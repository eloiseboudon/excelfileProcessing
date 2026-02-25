"""Nightly pipeline orchestrator.

Chains: Odoo sync → supplier API fetches → LLM matching → email report.
"""

from __future__ import annotations

import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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

        # Step 2 — Supplier API fetches
        suppliers_synced = _run_suppliers_step()

        # Step 3 — LLM matching
        matching_submitted = _run_matching_step()

    except Exception as exc:
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


def _run_matching_step() -> int:
    """Run LLM matching Phase 1 and return number of labels submitted."""
    from utils.llm_matching import run_matching_job

    result = run_matching_job(supplier_id=None, limit=None)
    submitted = result.get("total_labels", 0)
    logger.info("Matching step: %d labels submitted", submitted)
    return submitted


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
    """Send the nightly recap email to all active recipients.

    Returns True if at least one email was sent successfully.
    """
    from models import NightlyEmailRecipient

    recipients = NightlyEmailRecipient.query.filter_by(active=True).all()
    if not recipients:
        return False

    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    smtp_from = os.environ.get("SMTP_FROM", smtp_user)
    smtp_from_name = os.environ.get("SMTP_FROM_NAME", "AJT Pro")

    if not smtp_host or not smtp_user:
        logger.warning("SMTP not configured, skipping email")
        return False

    html_body = _build_html_report(job)
    subject = _build_subject(job)

    success = False
    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_password)
            for recipient in recipients:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"{smtp_from_name} <{smtp_from}>"
                msg["To"] = recipient.email
                msg.attach(MIMEText(html_body, "html", "utf-8"))
                server.sendmail(smtp_from, recipient.email, msg.as_string())
                logger.info("Nightly email sent to %s", recipient.email)
        success = True
    except Exception:
        logger.exception("SMTP error while sending nightly email")

    return success


def _build_subject(job: Any) -> str:
    date_str = job.started_at.strftime("%d/%m/%Y") if job.started_at else "N/A"
    status_label = "✅ Succès" if job.status == "completed" else "❌ Échec"
    return f"[AJT Pro] Rapport nightly {date_str} — {status_label}"


def _build_html_report(job: Any) -> str:
    frontend_base = os.environ.get("FRONTEND_BASE_URL", "http://localhost:5173")
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
