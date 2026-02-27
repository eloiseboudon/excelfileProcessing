"""API endpoints for LLM-based product matching."""

import logging
import threading
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import case, cast, exists, func, String

from models import (
    DeviceType,
    LabelCache,
    MatchingRun,
    PendingMatch,
    Product,
    ProductCalculation,
    Supplier,
    SupplierProductRef,
    SupplierCatalog,
    db,
)
from utils.activity import log_activity
from utils.auth import token_required
from utils.llm_matching import (
    _log_ean_history,
    create_product_from_extraction,
    normalize_label,
    run_matching_job,
)
from utils.type_classifier import classify_device_type

logger = logging.getLogger(__name__)

bp = Blueprint("matching", __name__)


def _run_matching_background(app, supplier_id, limit) -> None:
    """Run matching job in a background thread with its own app context."""
    with app.app_context():
        try:
            # Ensure device types are assigned before scoring — device_type is a
            # hard disqualifier and products without a type miss all candidates.
            from utils.nightly_pipeline import _run_assign_types_step
            try:
                _run_assign_types_step()
            except Exception:
                logger.warning("assign_device_types failed before matching, continuing anyway", exc_info=True)

            result = run_matching_job(supplier_id=supplier_id, limit=limit)
            logger.info(
                "Matching termine: %d produits, %d auto, %d review, %d rejetes, %d non trouves, %d erreurs",
                result.get("total_products", 0),
                result.get("auto_matched", 0),
                result.get("pending_review", 0),
                result.get("auto_rejected", 0),
                result.get("not_found", 0),
                result.get("errors", 0),
            )
        except Exception:
            logger.exception("Erreur background rapprochement LLM")


@bp.route("/matching/run", methods=["POST"])
@token_required("admin")
def run_matching():
    """Launch LLM matching asynchronously — returns 202 immediately."""
    data = request.get_json(silent=True) or {}
    supplier_id = data.get("supplier_id")
    limit = data.get("limit")
    if limit is not None:
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = None

    if supplier_id is not None:
        supplier = db.session.get(Supplier, supplier_id)
        if not supplier:
            return jsonify({"error": "Fournisseur introuvable"}), 404

    app = current_app._get_current_object()
    thread = threading.Thread(
        target=_run_matching_background,
        args=(app, supplier_id, limit),
        daemon=True,
    )
    thread.start()

    log_activity("matching.run", details={
        "supplier_id": supplier_id,
        "limit": limit,
    })
    return jsonify({"status": "started"}), 202


@bp.route("/matching/pending", methods=["GET"])
@token_required("admin")
def list_pending():
    """List pending matches awaiting validation."""
    VALID_STATUSES = {"pending", "validated", "rejected", "created"}

    supplier_id = request.args.get("supplier_id", type=int)
    status = request.args.get("status", "pending")
    model = request.args.get("model", type=str)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 100)

    if status not in VALID_STATUSES:
        return jsonify({"error": f"Statut invalide: {status}"}), 400

    query = PendingMatch.query.filter_by(status=status)
    if supplier_id:
        query = query.filter_by(supplier_id=supplier_id)
    if model:
        query = query.filter(
            cast(PendingMatch.extracted_attributes["model_family"], String).ilike(
                f"%{model}%"
            )
        )

    query = query.order_by(PendingMatch.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    # Enrich candidate product_name with memory + color in a single batch query
    all_product_ids = {
        c["product_id"]
        for pm in items
        for c in (pm.candidates or [])
        if c.get("product_id")
    }
    product_labels: dict[int, str] = {}
    if all_product_ids:
        for p in Product.query.filter(Product.id.in_(all_product_ids)).all():
            parts = [p.model or p.description or f"#{p.id}"]
            if p.memory:
                parts.append(p.memory.memory)
            if p.color:
                parts.append(p.color.color)
            product_labels[p.id] = " — ".join(parts)

    results = []
    for pm in items:
        enriched = [
            {**c, "product_name": product_labels.get(c.get("product_id"), c.get("product_name", ""))}
            for c in (pm.candidates or [])
        ]
        results.append({
            "id": pm.id,
            "supplier_id": pm.supplier_id,
            "supplier_name": pm.supplier.name if pm.supplier else None,
            "source_label": pm.source_label,
            "extracted_attributes": pm.extracted_attributes,
            "candidates": enriched,
            "status": pm.status,
            "created_at": pm.created_at.isoformat() if pm.created_at else None,
        })

    return jsonify({
        "items": results,
        "total": total,
        "page": page,
        "per_page": per_page,
    }), 200


@bp.route("/matching/validate", methods=["POST"])
@token_required("admin")
def validate_match():
    """Validate a proposed match."""
    data = request.get_json(silent=True) or {}
    pending_match_id = data.get("pending_match_id")
    product_id = data.get("product_id")

    if not pending_match_id or not product_id:
        return jsonify({"error": "pending_match_id et product_id requis"}), 400

    pm = db.session.get(PendingMatch, pending_match_id)
    if not pm:
        return jsonify({"error": "Match en attente introuvable"}), 404

    if pm.status not in ("pending", "rejected"):
        return jsonify({"error": f"Match deja traite (statut: {pm.status})"}), 400

    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({"error": "Produit introuvable"}), 404

    pm.status = "validated"
    pm.resolved_product_id = product_id
    pm.resolved_at = datetime.now(timezone.utc)

    # Create SupplierProductRef
    existing_ref = SupplierProductRef.query.filter_by(
        supplier_id=pm.supplier_id,
    ).filter(
        (SupplierProductRef.ean == pm.source_label)
        | (SupplierProductRef.supplier_sku == pm.source_label)
    ).first()

    if not existing_ref:
        catalog_entry = (
            db.session.get(SupplierCatalog, pm.temporary_import_id)
            if pm.temporary_import_id
            else None
        )
        ref = SupplierProductRef(
            supplier_id=pm.supplier_id,
            product_id=product_id,
            ean=catalog_entry.ean if catalog_entry else None,
            part_number=catalog_entry.part_number if catalog_entry else None,
            last_seen_at=datetime.now(timezone.utc),
        )
        db.session.add(ref)
        _log_ean_history(
            product_id,
            catalog_entry.ean if catalog_entry else None,
            pm.supplier_id,
            run_id=None,
            source="manual_validation",
        )

    # Retrieve the score breakdown for the validated product from PendingMatch candidates
    candidate_reasoning = None
    for candidate in (pm.candidates or []):
        if candidate.get("product_id") == product_id:
            candidate_reasoning = candidate.get("details")
            break

    # Update label cache — store reasoning so future n-shot selection can use it
    normalized = normalize_label(pm.source_label)
    cache = LabelCache.query.filter_by(
        supplier_id=pm.supplier_id, normalized_label=normalized
    ).first()
    if cache:
        cache.product_id = product_id
        cache.match_source = "manual"
        cache.match_reasoning = candidate_reasoning
        cache.last_used_at = datetime.now(timezone.utc)
    else:
        cache = LabelCache(
            supplier_id=pm.supplier_id,
            normalized_label=normalized,
            product_id=product_id,
            match_score=100,
            match_source="manual",
            match_reasoning=candidate_reasoning,
            extracted_attributes=pm.extracted_attributes,
        )
        db.session.add(cache)

    log_activity("matching.validate", details={
        "pending_match_id": pending_match_id,
        "product_id": product_id,
    })
    db.session.commit()
    return jsonify({"status": "validated", "product_id": product_id}), 200


@bp.route("/matching/reject", methods=["POST"])
@token_required("admin")
def reject_match():
    """Reject a match and optionally create a new product."""
    data = request.get_json(silent=True) or {}
    pending_match_id = data.get("pending_match_id")
    create_product = data.get("create_product", False)

    if not pending_match_id:
        return jsonify({"error": "pending_match_id requis"}), 400

    pm = db.session.get(PendingMatch, pending_match_id)
    if not pm:
        return jsonify({"error": "Match en attente introuvable"}), 404

    if pm.status != "pending":
        return jsonify({"error": f"Match deja traite (statut: {pm.status})"}), 400

    if create_product:
        product = create_product_from_extraction(
            pm.extracted_attributes, pm.source_label
        )
        pm.status = "created"
        pm.resolved_product_id = product.id
        pm.resolved_at = datetime.now(timezone.utc)

        catalog_entry = (
            db.session.get(SupplierCatalog, pm.temporary_import_id)
            if pm.temporary_import_id
            else None
        )
        ref = SupplierProductRef(
            supplier_id=pm.supplier_id,
            product_id=product.id,
            ean=catalog_entry.ean if catalog_entry else None,
            part_number=catalog_entry.part_number if catalog_entry else None,
            last_seen_at=datetime.now(timezone.utc),
        )
        db.session.add(ref)
        _log_ean_history(
            product.id,
            catalog_entry.ean if catalog_entry else None,
            pm.supplier_id,
            run_id=None,
            source="manual_reject_create",
        )

        normalized = normalize_label(pm.source_label)
        cache = LabelCache(
            supplier_id=pm.supplier_id,
            normalized_label=normalized,
            product_id=product.id,
            match_score=0,
            match_source="manual",
            extracted_attributes=pm.extracted_attributes,
        )
        db.session.add(cache)
    else:
        pm.status = "rejected"
        pm.resolved_at = datetime.now(timezone.utc)

    log_activity("matching.reject", details={
        "pending_match_id": pending_match_id,
        "create_product": create_product,
    })
    db.session.commit()
    return jsonify({"status": pm.status}), 200


@bp.route("/matching/stats", methods=["GET"])
@token_required("admin")
def matching_stats():
    """Aggregated matching statistics."""
    total_cached = LabelCache.query.count()
    total_pending = PendingMatch.query.filter_by(status="pending").count()
    total_validated = PendingMatch.query.filter_by(status="validated").count()
    total_rejected = PendingMatch.query.filter_by(status="rejected").count()
    total_created = PendingMatch.query.filter_by(status="created").count()
    total_auto_matched = LabelCache.query.filter_by(match_source="auto").count()
    total_manual = LabelCache.query.filter_by(match_source="manual").count()

    total_processed = total_validated + total_rejected + total_created
    total_all = total_pending + total_processed
    progress_pct = round(total_processed / total_all * 100, 1) if total_all > 0 else 0.0

    # Produits du catalogue fournisseur sans SupplierProductRef.
    # _create_supplier_ref identifie un ref par (supplier_id, ean, part_number) avec NULL-safe
    # comparison. On reproduit la même logique ici pour détecter tous les refs existants,
    # y compris ceux créés pour des items sans EAN (ean=None, matchés par part_number).
    has_product_ref = (
        db.session.query(SupplierProductRef.id)
        .filter(
            SupplierProductRef.supplier_id == SupplierCatalog.supplier_id,
            SupplierProductRef.product_id.isnot(None),
            # Comparaison NULL-safe sur EAN : (NULL=NULL) OU (val=val)
            db.or_(
                db.and_(
                    SupplierCatalog.ean.is_(None),
                    SupplierProductRef.ean.is_(None),
                ),
                db.and_(
                    SupplierCatalog.ean.isnot(None),
                    SupplierProductRef.ean == SupplierCatalog.ean,
                ),
            ),
            # Comparaison NULL-safe sur part_number
            db.or_(
                db.and_(
                    SupplierCatalog.part_number.is_(None),
                    SupplierProductRef.part_number.is_(None),
                ),
                db.and_(
                    SupplierCatalog.part_number.isnot(None),
                    SupplierProductRef.part_number == SupplierCatalog.part_number,
                ),
            ),
        )
        .exists()
    )
    # Filtre aligné avec le job Python :
    # - if ti.description or ti.model  → truthy, exclut les chaînes vides
    # - if not sid: continue           → exclut les items sans fournisseur
    processable_filter = [
        ~has_product_ref,
        db.or_(
            db.and_(
                SupplierCatalog.description.isnot(None),
                SupplierCatalog.description != "",
            ),
            db.and_(
                SupplierCatalog.model.isnot(None),
                SupplierCatalog.model != "",
            ),
        ),
        SupplierCatalog.supplier_id.isnot(None),
    ]

    # Total sans SupplierProductRef (inclut ceux en attente de validation)
    total_catalog_unprocessed = SupplierCatalog.query.filter(*processable_filter).count()

    # Parmi ceux-là, ceux qui ont déjà un PendingMatch "pending" (en attente de validation user)
    already_in_pending = db.session.query(PendingMatch.temporary_import_id).filter(
        PendingMatch.temporary_import_id.isnot(None),
        PendingMatch.status == "pending",
    )
    total_catalog_pending_review = SupplierCatalog.query.filter(
        *processable_filter,
        SupplierCatalog.id.in_(already_in_pending),
    ).count()

    # Ceux jamais envoyés dans un lot LLM
    total_catalog_never_processed = total_catalog_unprocessed - total_catalog_pending_review

    # Labels uniques parmi les jamais traités — on charge les labels en Python et on applique
    # normalize_label() exactement comme run_matching_job (compatible SQLite + PostgreSQL)
    never_processed_labels = (
        db.session.query(
            func.coalesce(SupplierCatalog.description, SupplierCatalog.model)
        )
        .filter(
            *processable_filter,
            ~SupplierCatalog.id.in_(already_in_pending),
        )
        .all()
    )
    total_catalog_never_processed_labels = len({
        normalize_label(row[0])
        for row in never_processed_labels
        if row[0] and normalize_label(row[0])
    })

    # By supplier — aggregated queries instead of N+1 loop
    cache_stats = (
        db.session.query(
            LabelCache.supplier_id,
            func.count(LabelCache.id).label("cached"),
            func.count(case((LabelCache.match_source == "auto", 1))).label("matched"),
            func.count(case((LabelCache.match_source == "manual", 1))).label("manual"),
        )
        .group_by(LabelCache.supplier_id)
        .all()
    )
    cache_map = {r.supplier_id: r for r in cache_stats}

    pending_stats = (
        db.session.query(
            PendingMatch.supplier_id,
            func.count(PendingMatch.id).label("pending"),
        )
        .filter(PendingMatch.status == "pending")
        .group_by(PendingMatch.supplier_id)
        .all()
    )
    pending_map = {r.supplier_id: r.pending for r in pending_stats}

    suppliers = Supplier.query.all()
    by_supplier = []
    for s in suppliers:
        cs = cache_map.get(s.id)
        cached = cs.cached if cs else 0
        pending = pending_map.get(s.id, 0)
        if cached or pending:
            by_supplier.append({
                "supplier_id": s.id,
                "name": s.name,
                "cached": cached,
                "pending": pending,
                "matched": cs.matched if cs else 0,
                "manual": cs.manual if cs else 0,
            })

    cache_hit_rate = 0.0
    total_entries = total_cached + total_pending
    if total_entries > 0:
        cache_hit_rate = round(total_cached / total_entries * 100, 1)

    total_odoo_products = Product.query.count()
    # Products matched = union of ETL-linked (ProductCalculation) and LLM-linked
    # (SupplierProductRef). Consistent with the definition used in run_matching_job.
    pc_ids = (
        db.session.query(ProductCalculation.product_id)
        .filter(ProductCalculation.product_id.isnot(None))
        .distinct()
    )
    spr_ids = (
        db.session.query(SupplierProductRef.product_id)
        .filter(SupplierProductRef.product_id.isnot(None))
        .distinct()
    )
    total_odoo_matched = (
        db.session.query(func.count())
        .select_from(pc_ids.union(spr_ids).subquery())
        .scalar()
    ) or 0
    total_odoo_unmatched = total_odoo_products - total_odoo_matched
    coverage_pct = round(total_odoo_matched / total_odoo_products * 100, 1) if total_odoo_products > 0 else 0.0

    # Produits uniques dans les candidats des pending/rejected matches
    # (déjà soumis au LLM mais en attente de validation)
    pending_product_ids: set[int] = set()
    for pm in PendingMatch.query.filter(
        PendingMatch.status.in_(["pending", "rejected"])
    ).with_entities(PendingMatch.candidates).all():
        for c in (pm.candidates or []):
            pid = c.get("product_id")
            if pid:
                pending_product_ids.add(pid)

    # Cache entries disponibles pour le matching Phase 2
    cache_unmatched_count = LabelCache.query.filter(
        LabelCache.match_source == "extracted",
        LabelCache.product_id.is_(None),
    ).count()

    # "Jamais soumis" = produits qu'un run LLM pourrait traiter maintenant.
    # Si pas de nouveaux labels à extraire (Phase 1) ET pas de cache dispo (Phase 2),
    # le LLM ne peut rien faire de plus → 0.
    if cache_unmatched_count == 0 and total_catalog_never_processed_labels == 0:
        total_odoo_never_submitted = 0
    else:
        total_odoo_never_submitted = max(0, total_odoo_unmatched - len(pending_product_ids))

    last_run_row = MatchingRun.query.order_by(MatchingRun.id.desc()).first()
    last_run_data = None
    if last_run_row:
        last_run_data = {
            "status": last_run_row.status,
            "ran_at": last_run_row.ran_at.isoformat() if last_run_row.ran_at else None,
            "total_products": last_run_row.total_products,
            "from_cache": last_run_row.from_cache,
            "llm_calls": last_run_row.llm_calls,
            "auto_matched": last_run_row.auto_matched,
            "pending_review": last_run_row.pending_review,
            "auto_rejected": last_run_row.auto_rejected,
            "not_found": last_run_row.not_found,
            "errors": last_run_row.errors,
            "cost_estimate": last_run_row.cost_estimate,
            "duration_seconds": last_run_row.duration_seconds,
            "error_message": last_run_row.error_message,
        }

    return jsonify({
        "total_odoo_products": total_odoo_products,
        "total_odoo_matched": total_odoo_matched,
        "total_odoo_unmatched": total_odoo_unmatched,
        "total_odoo_never_submitted": total_odoo_never_submitted,
        "coverage_pct": coverage_pct,
        "total_cached": total_cached,
        "total_pending": total_pending,
        "total_validated": total_validated,
        "total_rejected": total_rejected,
        "total_created": total_created,
        "total_processed": total_processed,
        "total_all": total_all,
        "progress_pct": progress_pct,
        "total_auto_matched": total_auto_matched,
        "total_manual": total_manual,
        "cache_hit_rate": cache_hit_rate,
        "total_catalog_unprocessed": total_catalog_unprocessed,
        "total_catalog_never_processed": total_catalog_never_processed,
        "total_catalog_never_processed_labels": total_catalog_never_processed_labels,
        "total_catalog_pending_review": total_catalog_pending_review,
        "by_supplier": by_supplier,
        "last_run": last_run_data,
    }), 200


@bp.route("/matching/runs", methods=["GET"])
@token_required("admin")
def list_runs():
    """Return the most recent matching runs for the Rapport tab."""
    limit = request.args.get("limit", 30, type=int)
    limit = min(limit, 100)

    runs = (
        MatchingRun.query
        .order_by(MatchingRun.id.desc())
        .limit(limit)
        .all()
    )

    return jsonify([
        {
            "id": r.id,
            "ran_at": r.ran_at.isoformat() if r.ran_at else None,
            "status": r.status,
            "total_products": r.total_products,
            "from_cache": r.from_cache,
            "llm_calls": r.llm_calls,
            "auto_matched": r.auto_matched,
            "pending_review": r.pending_review,
            "auto_rejected": r.auto_rejected,
            "not_found": r.not_found,
            "errors": r.errors,
            "cost_estimate": r.cost_estimate,
            "duration_seconds": r.duration_seconds,
            "cross_supplier_hits": r.cross_supplier_hits,
            "fuzzy_hits": r.fuzzy_hits,
            "attr_share_hits": r.attr_share_hits,
            "total_odoo_products": r.total_odoo_products,
            "matched_products": r.matched_products,
            "nightly_job_id": r.nightly_job_id,
        }
        for r in runs
    ]), 200


@bp.route("/matching/cache", methods=["GET"])
@token_required("admin")
def list_cache():
    """List label cache entries."""
    supplier_id = request.args.get("supplier_id", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    per_page = min(per_page, 100)

    query = LabelCache.query
    if supplier_id:
        query = query.filter_by(supplier_id=supplier_id)

    query = query.order_by(LabelCache.last_used_at.desc())
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    results = []
    for c in items:
        results.append({
            "id": c.id,
            "supplier_id": c.supplier_id,
            "normalized_label": c.normalized_label,
            "product_id": c.product_id,
            "match_score": c.match_score,
            "match_source": c.match_source,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
        })

    return jsonify({
        "items": results,
        "total": total,
        "page": page,
        "per_page": per_page,
    }), 200


@bp.route("/matching/assign-types", methods=["POST"])
@token_required("admin")
def assign_device_types():
    """Assign device types to products with null or non-informative type using keyword rules."""
    data = request.get_json(silent=True) or {}
    dry_run = bool(data.get("dry_run", False))

    _SKIP = {"all", "a définir", "a definir"}

    products_no_type = Product.query.filter(Product.type_id.is_(None)).all()
    products_skip_type = (
        Product.query
        .join(DeviceType, Product.type_id == DeviceType.id)
        .filter(func.lower(DeviceType.type).in_(list(_SKIP)))
        .all()
    )
    products = products_no_type + products_skip_type

    type_cache: dict[str, int] = {
        dt.type.lower(): dt.id for dt in DeviceType.query.all()
    }
    # "A définir" is the fallback type for products that can't be classified
    fallback_id = type_cache.get("a définir") or type_cache.get("a definir")

    classified_count = 0
    unclassified_count = 0

    for product in products:
        brand = product.brand.brand if product.brand else None
        new_type_name = classify_device_type(product.model, brand)
        if new_type_name:
            type_id = type_cache.get(new_type_name.lower())
            if type_id and not dry_run:
                product.type_id = type_id
            classified_count += 1
        else:
            if fallback_id and not dry_run:
                product.type_id = fallback_id
            unclassified_count += 1

    if not dry_run:
        db.session.commit()
        log_activity("matching.assign_types", details={
            "classified": classified_count,
            "unclassified": unclassified_count,
            "total": len(products),
        })

    return jsonify({
        "classified": classified_count,
        "unclassified": unclassified_count,
        "total": len(products),
        "dry_run": dry_run,
    }), 200


@bp.route("/matching/cache/<int:cache_id>", methods=["DELETE"])
@token_required("admin")
def delete_cache_entry(cache_id):
    """Delete a cache entry to force re-matching."""
    cache = db.session.get(LabelCache, cache_id)
    if not cache:
        return jsonify({"error": "Entree cache introuvable"}), 404

    db.session.delete(cache)
    db.session.commit()
    return "", 204
