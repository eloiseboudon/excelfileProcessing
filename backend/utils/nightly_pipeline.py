"""Nightly pipeline orchestrator.

Chains: Odoo sync → supplier API fetches → LLM matching → email report.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def run_nightly_pipeline() -> Dict[str, Any]:
    """Run the full nightly pipeline and return a summary dict."""
    from models import (
        ApiFetchJob,
        NightlyEmailRecipient,
        NightlyJob,
        OdooSyncJob,
        SupplierAPI,
        db,
    )

    # Prevent duplicate runs (e.g. multiple Gunicorn workers triggering simultaneously).
    # pg_try_advisory_lock is atomic — only one connection can acquire it.
    # Falls back to a simple running-job check on non-PostgreSQL engines (tests use SQLite).
    from sqlalchemy import text

    use_pg_lock = "postgresql" in str(db.engine.url)
    if use_pg_lock:
        lock_acquired = db.session.execute(text("SELECT pg_try_advisory_lock(73901)")).scalar()
        if not lock_acquired:
            logger.info("Nightly pipeline lock already held by another worker, skipping.")
            return {"skipped": True, "reason": "already_running"}
    else:
        already_running = NightlyJob.query.filter_by(status="running").first()
        if already_running:
            logger.info("Nightly pipeline already running (job #%d), skipping.", already_running.id)
            return {"skipped": True, "reason": "already_running"}

    try:
        return _run_pipeline_locked(db, NightlyJob, NightlyEmailRecipient,
                                    ApiFetchJob, OdooSyncJob, SupplierAPI)
    finally:
        if use_pg_lock:
            db.session.execute(text("SELECT pg_advisory_unlock(73901)"))
            db.session.commit()


def _run_pipeline_locked(db, NightlyJob, NightlyEmailRecipient,
                         ApiFetchJob, OdooSyncJob, SupplierAPI) -> Dict[str, Any]:
    """Core pipeline logic, called while holding the advisory lock."""
    job = NightlyJob(status="running")
    db.session.add(job)
    db.session.commit()
    job_id = job.id
    logger.info("Nightly pipeline started (job #%d)", job_id)

    odoo_synced = None
    suppliers_synced = 0
    matching_submitted = None
    error_message = None

    try:
        # Step 1 — Odoo sync
        odoo_synced = _run_odoo_step()

        # Step 1.5 — Assign device types (non-fatal: type assignment enriches matching but
        # should not abort the pipeline if it fails)
        try:
            _run_assign_types_step()
        except Exception:
            db.session.rollback()
            logger.exception("Assign types step failed, continuing pipeline")

        # Step 2 — Supplier API fetches
        suppliers_synced = _run_suppliers_step()

        # Step 3 — LLM matching
        matching_result = _run_matching_step()
        matching_submitted = matching_result.get("total_products", 0)

        # Link MatchingRun to this NightlyJob
        run_id = matching_result.get("run_id")
        if run_id:
            from models import MatchingRun
            matching_run = db.session.get(MatchingRun, run_id)
            if matching_run:
                matching_run.nightly_job_id = job_id
                db.session.commit()

    except Exception as exc:
        db.session.rollback()
        logger.exception("Nightly pipeline failed at job #%d", job_id)
        error_message = str(exc)

    # Persist job outcome
    job = db.session.get(NightlyJob, job_id)
    job.status = "failed" if error_message else "completed"
    job.finished_at = datetime.now(timezone.utc)
    job.odoo_synced = odoo_synced
    job.suppliers_synced = suppliers_synced
    job.matching_submitted = matching_submitted
    job.error_message = error_message
    db.session.commit()

    # Step 4 — Email report
    email_sent = False
    try:
        recipients = NightlyEmailRecipient.query.filter_by(active=True).all()
        if recipients:
            email_sent = send_nightly_email(job)
            job.email_sent = email_sent
            db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Failed to send nightly email for job #%d", job_id)

    summary = {
        "job_id": job_id,
        "status": job.status,
        "odoo_synced": odoo_synced,
        "suppliers_synced": suppliers_synced,
        "matching_submitted": matching_submitted,
        "email_sent": email_sent,
        "error_message": error_message,
    }
    logger.info("Nightly pipeline finished: %s", summary)
    return summary


# ---------------------------------------------------------------------------
# Step implementations
# ---------------------------------------------------------------------------


def _run_odoo_step() -> int:
    """Trigger an Odoo sync and return the number of synced products."""
    from models import OdooConfig, OdooSyncJob, db
    from utils.odoo_sync import run_odoo_sync

    config = OdooConfig.query.first()
    if not config:
        logger.warning("No Odoo config found, skipping Odoo sync step")
        return 0

    sync_job = OdooSyncJob(trigger="nightly")
    db.session.add(sync_job)
    db.session.commit()

    run_odoo_sync(sync_job.id)

    # Reload to get updated counts
    db.session.refresh(sync_job)
    synced = (sync_job.created_count or 0) + (sync_job.updated_count or 0)
    logger.info("Odoo sync step: %d products synced", synced)
    return synced


def _run_assign_types_step() -> Dict[str, int]:
    """Assign device types to products with a missing or non-informative type.

    Runs after the Odoo sync so newly imported products receive their type
    before the supplier fetches and LLM matching steps.
    Returns a summary dict with classified/unclassified counts.
    """
    from sqlalchemy import func

    from models import DeviceType, Product, db
    from utils.type_classifier import classify_device_type

    _SKIP = {"all", "a définir", "a definir"}

    products_no_type = Product.query.filter(Product.type_id.is_(None)).all()
    products_skip_type = (
        Product.query
        .join(DeviceType, Product.type_id == DeviceType.id)
        .filter(func.lower(DeviceType.type).in_(list(_SKIP)))
        .all()
    )
    products = products_no_type + products_skip_type

    if not products:
        logger.info("Assign types step: no products to classify")
        return {"classified": 0, "unclassified": 0, "total": 0}

    type_cache: Dict[str, int] = {dt.type.lower(): dt.id for dt in DeviceType.query.all()}
    fallback_id = type_cache.get("a définir") or type_cache.get("a definir")

    classified = 0
    unclassified = 0

    for product in products:
        brand = product.brand.brand if product.brand else None
        new_type_name = classify_device_type(product.model, brand)
        if new_type_name:
            type_id = type_cache.get(new_type_name.lower())
            if type_id:
                product.type_id = type_id
            classified += 1
        else:
            if fallback_id:
                product.type_id = fallback_id
            unclassified += 1

    db.session.commit()
    logger.info(
        "Assign types step: %d classified, %d unclassified (total: %d)",
        classified, unclassified, len(products),
    )
    return {"classified": classified, "unclassified": unclassified, "total": len(products)}


def _run_suppliers_step() -> int:
    """Re-fetch all active supplier APIs and return count of suppliers processed."""
    from models import ApiFetchJob, MappingVersion, SupplierAPI, db
    from utils.etl import run_fetch_job

    apis = _get_active_supplier_apis()
    count = 0
    for api in apis:
        try:
            # Find the active mapping
            mapping = MappingVersion.query.filter_by(
                supplier_api_id=api.id, is_active=True
            ).first()
            if not mapping:
                logger.warning(
                    "No active mapping for SupplierAPI #%d, skipping", api.id
                )
                continue

            # Use first endpoint (typical setup: one endpoint per API)
            if not api.endpoints:
                logger.warning(
                    "No endpoint for SupplierAPI #%d, skipping", api.id
                )
                continue

            endpoint = api.endpoints[0]
            new_job = ApiFetchJob(
                supplier_api_id=api.id,
                endpoint_id=endpoint.id,
                mapping_version_id=mapping.id,
                status="running",
            )
            db.session.add(new_job)
            db.session.commit()

            run_fetch_job(
                job_id=new_job.id,
                supplier_id=api.supplier_id,
                endpoint_id=endpoint.id,
                mapping_id=mapping.id,
            )
            count += 1
        except Exception:
            logger.exception("Failed to fetch supplier API #%d", api.id)

    logger.info("Suppliers step: %d APIs fetched", count)
    return count


def _run_matching_step() -> Dict[str, Any]:
    """Nightly matching: incremental evaluation — only new/changed labels are scored.

    Strategy:
    - Existing matches (auto-matched, pending, rejected) are preserved.
    - Phase 1 marks every label still present in the supplier catalog (last_seen_run_id).
    - Labels no longer in the catalog are cleaned up (product_id reset, PendingMatch deleted).
    - Phase 2 only scores products not yet matched/pending against the candidate pool.
    - Result: only genuinely new supplier labels trigger scoring work.

    Weekly full rescore (Sunday): all auto-matched and pending/rejected results are
    reset so Phase 2 re-evaluates the entire product catalog from scratch. Manual
    validations (status='validated'/'created') are preserved.
    """
    from models import LabelCache, PendingMatch, db
    from utils import llm_matching

    is_sunday = datetime.now(timezone.utc).weekday() == 6  # 0=Monday, 6=Sunday

    if is_sunday:
        # Reset auto-matched LabelCache entries (preserve manual validations via SupplierProductRef)
        reset_count = LabelCache.query.filter(
            LabelCache.product_id.isnot(None),
            LabelCache.match_source.in_(["auto", "attr_share"]),
        ).update(
            {"product_id": None, "match_score": None, "match_reasoning": None,
             "match_source": "extracted"},
            synchronize_session="fetch",
        )

        # Delete pending/rejected PendingMatches (manual validations are preserved)
        deleted_pm = PendingMatch.query.filter(
            PendingMatch.status.in_(["pending", "rejected"])
        ).delete(synchronize_session="fetch")

        db.session.flush()
        logger.info(
            "Sunday full rescore: %d LabelCache matches reset, %d PendingMatches deleted",
            reset_count, deleted_pm,
        )

    result = llm_matching.run_matching_job(supplier_id=None, limit=None)
    logger.info(
        "Nightly matching (%s): %d products processed (llm_calls=%d, auto=%d, pending=%d)",
        "full rescore" if is_sunday else "incremental",
        result.get("total_products", 0),
        result.get("llm_calls", 0),
        result.get("auto_matched", 0),
        result.get("pending_review", 0),
    )

    return result


def _apply_validation_history(validation_history: Dict[tuple, int]) -> int:
    """Auto-validate new PendingMatch entries that reproduce a known good match.

    A match is considered "known good" when tonight's top candidate points to
    the same Odoo product that was validated (manually or via auto-match) last night.
    """
    from datetime import datetime, timezone

    from models import LabelCache, PendingMatch, db

    count = 0
    for pm in PendingMatch.query.filter_by(status="pending").all():
        validated_product_id = validation_history.get((pm.source_label, pm.supplier_id))
        if not validated_product_id:
            continue

        candidates = pm.candidates or []
        if not candidates:
            continue

        top_product_id = candidates[0].get("product_id")
        if top_product_id != validated_product_id:
            # Match changed → leave as pending for morning review
            continue

        pm.status = "validated"
        pm.resolved_product_id = validated_product_id
        pm.resolved_at = datetime.now(timezone.utc)

        # Restore LabelCache product link so the ETL can sync prices on next run
        LabelCache.query.filter_by(
            normalized_label=pm.source_label,
            supplier_id=pm.supplier_id,
        ).update({"product_id": validated_product_id}, synchronize_session=False)
        count += 1

    db.session.commit()
    return count


def _get_active_supplier_apis() -> List[Any]:
    """Return SupplierAPI rows that have at least one fetch job."""
    from models import ApiFetchJob, SupplierAPI, db
    from sqlalchemy import exists

    return (
        SupplierAPI.query.filter(
            exists().where(ApiFetchJob.supplier_api_id == SupplierAPI.id)
        )
        .all()
    )


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------


def send_nightly_email(job: Any) -> bool:
    """Trigger the n8n webhook so the existing workflow sends the recap email.

    Returns True if the webhook responded with HTTP 2xx.
    """
    from models import NightlyEmailRecipient

    webhook_url = os.environ.get("NIGHTLY_WEBHOOK_URL", "").strip()
    if not webhook_url:
        logger.warning("NIGHTLY_WEBHOOK_URL not set, skipping email notification")
        return False

    recipients = NightlyEmailRecipient.query.filter_by(active=True).all()
    if not recipients:
        logger.info("No active recipients, skipping webhook call")
        return False

    frontend_base = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    duration = ""
    if job.started_at and job.finished_at:
        secs = int((job.finished_at - job.started_at).total_seconds())
        m, s = divmod(secs, 60)
        duration = f"{m}m {s}s" if m else f"{s}s"

    payload = {
        "status": job.status,
        "date": job.started_at.strftime("%d/%m/%Y %H:%M UTC") if job.started_at else None,
        "odoo_synced": job.odoo_synced or 0,
        "suppliers_synced": job.suppliers_synced or 0,
        "matching_submitted": job.matching_submitted or 0,
        "duration": duration,
        "error_message": job.error_message,
        "validation_url": f"{frontend_base}/matching",
        "subject": _build_subject(job),
        "html_body": _build_html_report(job),
        "recipients": [r.email for r in recipients],
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            success = 200 <= resp.status < 300
            logger.info("n8n webhook called: HTTP %d", resp.status)
            return success
    except Exception:
        logger.exception("Failed to call n8n webhook")
        return False


def _build_subject(job: Any) -> str:
    date_str = job.started_at.strftime("%d/%m/%Y") if job.started_at else "N/A"
    status_label = "✅ Succès" if job.status == "completed" else "❌ Échec"
    return f"[AJT Pro] Rapport nightly {date_str} — {status_label}"


def _build_html_report(job: Any) -> str:
    from models import MatchingRun

    frontend_base = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    validation_url = f"{frontend_base}/matching"

    date_str = job.started_at.strftime("%d/%m/%Y %H:%M UTC") if job.started_at else "N/A"
    duration = ""
    if job.started_at and job.finished_at:
        delta = job.finished_at - job.started_at
        total_seconds = int(delta.total_seconds())
        minutes, seconds = divmod(total_seconds, 60)
        duration = f"{minutes}m {seconds}s"

    status_color = "#22c55e" if job.status == "completed" else "#ef4444"
    status_label = "Succès" if job.status == "completed" else "Échec"

    rows = [
        ("Synchronisation Odoo", f"{job.odoo_synced or 0} produits"),
        ("Fournisseurs traités", f"{job.suppliers_synced or 0} API"),
        ("Labels soumis au matching", f"{job.matching_submitted or 0}"),
        ("Email envoyé", "Oui" if job.email_sent else "Non"),
    ]
    if duration:
        rows.append(("Durée", duration))
    if job.error_message:
        rows.append(("Erreur", job.error_message))

    rows_html = "".join(
        f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:14px;">{label}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-weight:600;font-size:14px;">{value}</td>
        </tr>"""
        for label, value in rows
    )

    # Matching detail section
    mr = MatchingRun.query.filter_by(nightly_job_id=job.id).first()
    matching_section = ""
    if mr and mr.total_products is not None:
        matching_rows = [
            ("Produits traités", str(mr.total_products)),
            ("Depuis le cache", f"{mr.from_cache or 0} (0 appel LLM)"),
            ("Appels LLM (batches)", str(mr.llm_calls or 0)),
            ("Auto-matchés (≥90 pts)", str(mr.auto_matched or 0)),
            ("À valider (50-89 pts)", str(mr.pending_review or 0)),
            ("Rejetés auto", str(mr.auto_rejected or 0)),
            ("Non trouvés", str(mr.not_found or 0)),
            ("Coût estimé", f"~{mr.cost_estimate or 0:.4f} €"),
            ("Durée matching", f"{mr.duration_seconds or 0:.1f}s"),
        ]
        matching_rows_html = "".join(
            f"""
            <tr>
              <td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280;font-size:13px;">{label}</td>
              <td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;font-weight:600;font-size:13px;">{value}</td>
            </tr>"""
            for label, value in matching_rows
        )
        matching_section = f"""
      <h2 style="font-size:15px;color:#374151;margin:24px 0 8px;">Détail matching LLM</h2>
      <table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:6px;overflow:hidden;">
        {matching_rows_html}
      </table>"""

    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><title>Rapport nightly AJT Pro</title></head>
<body style="font-family:Arial,sans-serif;background:#f9fafb;padding:24px;margin:0;">
  <div style="max-width:560px;margin:0 auto;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1);">
    <div style="background:#B8860B;padding:20px 24px;">
      <h1 style="color:#ffffff;margin:0;font-size:20px;">AJT Pro — Rapport nightly</h1>
      <p style="color:#fde68a;margin:4px 0 0;font-size:14px;">{date_str}</p>
    </div>
    <div style="padding:24px;">
      <p style="margin:0 0 16px;">
        Statut :
        <strong style="color:{status_color};">{status_label}</strong>
      </p>
      <table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:6px;overflow:hidden;">
        {rows_html}
      </table>
      {matching_section}
      <div style="margin-top:24px;text-align:center;">
        <a href="{validation_url}"
           style="background:#B8860B;color:#fff;padding:10px 24px;border-radius:6px;text-decoration:none;font-weight:600;font-size:14px;">
          Valider les rapprochements
        </a>
      </div>
    </div>
    <div style="padding:12px 24px;background:#f3f4f6;text-align:center;">
      <p style="margin:0;font-size:12px;color:#9ca3af;">
        Ce message a été envoyé automatiquement par AJT Pro. Ne pas répondre à cet email.
      </p>
    </div>
  </div>
</body>
</html>"""
