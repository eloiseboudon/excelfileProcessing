"""Nightly pipeline REST endpoints."""

from __future__ import annotations

import threading
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from models import NightlyConfig, NightlyEmailRecipient, NightlyJob, db
from utils.auth import token_required

nightly_bp = Blueprint("nightly", __name__, url_prefix="/api/nightly")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@nightly_bp.get("/config")
@token_required("admin")
def get_config():
    config = _get_or_create_config()
    return jsonify(_config_to_dict(config))


@nightly_bp.put("/config")
@token_required("admin")
def update_config():
    body = request.get_json(force=True) or {}
    config = _get_or_create_config()

    if "enabled" in body:
        config.enabled = bool(body["enabled"])
    if "run_hour" in body:
        hour = int(body["run_hour"])
        if not 0 <= hour <= 23:
            return jsonify({"error": "run_hour must be between 0 and 23"}), 400
        config.run_hour = hour
    if "run_minute" in body:
        minute = int(body["run_minute"])
        if not 0 <= minute <= 59:
            return jsonify({"error": "run_minute must be between 0 and 59"}), 400
        config.run_minute = minute

    config.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(_config_to_dict(config))


# ---------------------------------------------------------------------------
# Trigger
# ---------------------------------------------------------------------------


@nightly_bp.post("/trigger")
@token_required("admin")
def trigger_pipeline():
    """Launch the nightly pipeline immediately in a background thread."""
    from flask import current_app

    app = current_app._get_current_object()  # noqa: SLF001

    def _run():
        with app.app_context():
            from utils.nightly_pipeline import run_nightly_pipeline
            run_nightly_pipeline()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return jsonify({"status": "triggered"}), 202


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


@nightly_bp.get("/jobs")
@token_required("admin")
def list_jobs():
    jobs = (
        NightlyJob.query.order_by(NightlyJob.started_at.desc()).limit(20).all()
    )
    return jsonify([_job_to_dict(j) for j in jobs])


@nightly_bp.get("/jobs/<int:job_id>")
@token_required("admin")
def get_job(job_id: int):
    job = db.get_or_404(NightlyJob, job_id)
    return jsonify(_job_to_dict(job))


# ---------------------------------------------------------------------------
# Recipients
# ---------------------------------------------------------------------------


@nightly_bp.get("/recipients")
@token_required("admin")
def list_recipients():
    recipients = NightlyEmailRecipient.query.order_by(
        NightlyEmailRecipient.id
    ).all()
    return jsonify([_recipient_to_dict(r) for r in recipients])


@nightly_bp.post("/recipients")
@token_required("admin")
def add_recipient():
    body = request.get_json(force=True) or {}
    email = (body.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "email is required"}), 400

    existing = NightlyEmailRecipient.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "Recipient already exists"}), 409

    recipient = NightlyEmailRecipient(
        email=email,
        name=(body.get("name") or "").strip() or None,
        active=bool(body.get("active", True)),
    )
    db.session.add(recipient)
    db.session.commit()
    return jsonify(_recipient_to_dict(recipient)), 201


@nightly_bp.delete("/recipients/<int:recipient_id>")
@token_required("admin")
def delete_recipient(recipient_id: int):
    recipient = db.get_or_404(NightlyEmailRecipient, recipient_id)
    db.session.delete(recipient)
    db.session.commit()
    return "", 204


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_or_create_config() -> NightlyConfig:
    config = NightlyConfig.query.first()
    if not config:
        config = NightlyConfig(enabled=False, run_hour=2, run_minute=0)
        db.session.add(config)
        db.session.commit()
    return config


def _config_to_dict(config: NightlyConfig) -> dict:
    return {
        "id": config.id,
        "enabled": config.enabled,
        "run_hour": config.run_hour,
        "run_minute": config.run_minute,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


def _job_to_dict(job: NightlyJob) -> dict:
    return {
        "id": job.id,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "status": job.status,
        "odoo_synced": job.odoo_synced,
        "suppliers_synced": job.suppliers_synced,
        "matching_submitted": job.matching_submitted,
        "email_sent": job.email_sent,
        "error_message": job.error_message,
    }


def _recipient_to_dict(r: NightlyEmailRecipient) -> dict:
    return {
        "id": r.id,
        "email": r.email,
        "name": r.name,
        "active": r.active,
    }
