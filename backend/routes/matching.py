"""API endpoints for LLM-based product matching."""

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy import cast, func, String

from models import (
    LabelCache,
    PendingMatch,
    Product,
    Supplier,
    SupplierProductRef,
    SupplierCatalog,
    db,
)
from utils.auth import token_required
from utils.llm_matching import (
    create_product_from_extraction,
    normalize_label,
    run_matching_job,
)

logger = logging.getLogger(__name__)

bp = Blueprint("matching", __name__)


@bp.route("/matching/run", methods=["POST"])
@token_required("admin")
def run_matching():
    """Launch LLM matching on unmatched supplier catalog entries."""
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

    try:
        report = run_matching_job(supplier_id=supplier_id, limit=limit)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Erreur lors du rapprochement LLM")
        return jsonify({"error": "Erreur interne lors du rapprochement"}), 500

    return jsonify(report), 200


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

    results = []
    for pm in items:
        results.append({
            "id": pm.id,
            "supplier_id": pm.supplier_id,
            "supplier_name": pm.supplier.name if pm.supplier else None,
            "source_label": pm.source_label,
            "extracted_attributes": pm.extracted_attributes,
            "candidates": pm.candidates,
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

    if pm.status != "pending":
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

    # Update label cache
    normalized = normalize_label(pm.source_label)
    cache = LabelCache.query.filter_by(
        supplier_id=pm.supplier_id, normalized_label=normalized
    ).first()
    if cache:
        cache.product_id = product_id
        cache.match_source = "manual"
        cache.last_used_at = datetime.now(timezone.utc)
    else:
        cache = LabelCache(
            supplier_id=pm.supplier_id,
            normalized_label=normalized,
            product_id=product_id,
            match_score=100,
            match_source="manual",
            extracted_attributes=pm.extracted_attributes,
        )
        db.session.add(cache)

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

    db.session.commit()
    return jsonify({"status": pm.status}), 200


@bp.route("/matching/stats", methods=["GET"])
@token_required("admin")
def matching_stats():
    """Aggregated matching statistics."""
    total_cached = LabelCache.query.count()
    total_pending = PendingMatch.query.filter_by(status="pending").count()
    total_auto_matched = LabelCache.query.filter_by(match_source="auto").count()
    total_manual = LabelCache.query.filter_by(match_source="manual").count()

    # By supplier
    by_supplier = []
    suppliers = Supplier.query.all()
    for s in suppliers:
        cached = LabelCache.query.filter_by(supplier_id=s.id).count()
        pending = PendingMatch.query.filter_by(supplier_id=s.id, status="pending").count()
        matched = LabelCache.query.filter_by(supplier_id=s.id, match_source="auto").count()
        manual = LabelCache.query.filter_by(supplier_id=s.id, match_source="manual").count()
        if cached or pending:
            by_supplier.append({
                "supplier_id": s.id,
                "name": s.name,
                "cached": cached,
                "pending": pending,
                "matched": matched,
                "manual": manual,
            })

    cache_hit_rate = 0.0
    total_entries = total_cached + total_pending
    if total_entries > 0:
        cache_hit_rate = round(total_cached / total_entries * 100, 1)

    return jsonify({
        "total_cached": total_cached,
        "total_pending": total_pending,
        "total_auto_matched": total_auto_matched,
        "total_manual": total_manual,
        "cache_hit_rate": cache_hit_rate,
        "by_supplier": by_supplier,
    }), 200


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
