"""Routes for Odoo synchronization configuration and job management."""

import threading
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from models import OdooConfig, OdooSyncJob, db
from utils.auth import token_required
from utils.odoo_sync import OdooClient, run_odoo_sync

bp = Blueprint("odoo", __name__)


@bp.route("/odoo/config", methods=["GET"])
@token_required("admin")
def get_config():
    """Get Odoo configuration.

    ---
    tags:
      - Odoo
    responses:
      200:
        description: Odoo configuration (password masked)
    """
    config = OdooConfig.query.first()
    if not config:
        return jsonify({"configured": False})
    return jsonify(
        {
            "configured": True,
            "url": config.url,
            "database": config.database,
            "login": config.login,
            "password": "********" if config.password else "",
            "auto_sync_enabled": config.auto_sync_enabled,
            "auto_sync_interval_minutes": config.auto_sync_interval_minutes,
            "last_auto_sync_at": (
                config.last_auto_sync_at.isoformat() if config.last_auto_sync_at else None
            ),
        }
    )


@bp.route("/odoo/config", methods=["PUT"])
@token_required("admin")
def update_config():
    """Create or update Odoo configuration.

    ---
    tags:
      - Odoo
    responses:
      200:
        description: Configuration saved
      400:
        description: Missing required fields
    """
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    database = data.get("database", "").strip()
    login = data.get("login", "").strip()
    password = data.get("password", "").strip()

    if not url or not database or not login:
        return jsonify({"error": "URL, base de données et login requis"}), 400

    config = OdooConfig.query.first()
    if config:
        config.url = url
        config.database = database
        config.login = login
        if password and password != "********":
            config.password = password
        config.updated_at = datetime.now(timezone.utc)
    else:
        if not password:
            return jsonify({"error": "Mot de passe requis"}), 400
        config = OdooConfig(
            url=url,
            database=database,
            login=login,
            password=password,
        )
        db.session.add(config)
    db.session.commit()
    return jsonify({"message": "Configuration sauvegardée"})


@bp.route("/odoo/test", methods=["POST"])
@token_required("admin")
def test_connection():
    """Test the Odoo connection.

    ---
    tags:
      - Odoo
    responses:
      200:
        description: Connection successful
      400:
        description: No configuration found
      500:
        description: Connection failed
    """
    config = OdooConfig.query.first()
    if not config:
        return jsonify({"error": "Configuration Odoo manquante"}), 400

    try:
        client = OdooClient(config.url, config.database, config.login, config.password)
        result = client.test_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/odoo/sync", methods=["POST"])
@token_required("admin")
def trigger_sync():
    """Trigger a manual Odoo synchronization.

    ---
    tags:
      - Odoo
    responses:
      200:
        description: Synchronization started
      400:
        description: No configuration found
      409:
        description: A sync is already running
    """
    config = OdooConfig.query.first()
    if not config:
        return jsonify({"error": "Configuration Odoo manquante"}), 400

    running = OdooSyncJob.query.filter_by(status="running").first()
    if running:
        return jsonify({"error": "Une synchronisation est déjà en cours"}), 409

    job = OdooSyncJob(trigger="manual")
    db.session.add(job)
    db.session.commit()

    from flask import current_app

    app = current_app._get_current_object()

    def _run():
        with app.app_context():
            run_odoo_sync(job.id)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return jsonify({"job_id": job.id, "status": "running"})


@bp.route("/odoo/jobs", methods=["GET"])
@token_required("admin")
def list_jobs():
    """List Odoo sync jobs.

    ---
    tags:
      - Odoo
    responses:
      200:
        description: List of sync jobs
    """
    limit = request.args.get("limit", 20, type=int)
    jobs = (
        OdooSyncJob.query.order_by(OdooSyncJob.started_at.desc()).limit(limit).all()
    )
    return jsonify(
        [
            {
                "id": j.id,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "ended_at": j.ended_at.isoformat() if j.ended_at else None,
                "status": j.status,
                "trigger": j.trigger,
                "error_message": j.error_message,
                "total_odoo_products": j.total_odoo_products,
                "created_count": j.created_count,
                "updated_count": j.updated_count,
                "unchanged_count": j.unchanged_count,
                "error_count": j.error_count,
            }
            for j in jobs
        ]
    )


@bp.route("/odoo/jobs/<int:job_id>", methods=["GET"])
@token_required("admin")
def get_job(job_id):
    """Get details for a specific sync job.

    ---
    tags:
      - Odoo
    responses:
      200:
        description: Job details with reports
      404:
        description: Job not found
    """
    job = db.session.get(OdooSyncJob, job_id)
    if not job:
        return jsonify({"error": "Job introuvable"}), 404
    return jsonify(
        {
            "id": job.id,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            "status": job.status,
            "trigger": job.trigger,
            "error_message": job.error_message,
            "total_odoo_products": job.total_odoo_products,
            "created_count": job.created_count,
            "updated_count": job.updated_count,
            "unchanged_count": job.unchanged_count,
            "error_count": job.error_count,
            "report_created": job.report_created,
            "report_updated": job.report_updated,
            "report_unchanged": job.report_unchanged,
            "report_errors": job.report_errors,
        }
    )


@bp.route("/odoo/auto-sync", methods=["PUT"])
@token_required("admin")
def update_auto_sync():
    """Enable or disable automatic synchronization.

    ---
    tags:
      - Odoo
    responses:
      200:
        description: Auto sync settings updated
      400:
        description: No configuration found or invalid interval
    """
    config = OdooConfig.query.first()
    if not config:
        return jsonify({"error": "Configuration Odoo manquante"}), 400

    data = request.get_json(silent=True) or {}
    enabled = data.get("enabled")
    interval = data.get("interval_minutes")

    if enabled is not None:
        config.auto_sync_enabled = bool(enabled)
    if interval is not None:
        interval = int(interval)
        if interval < 15:
            return jsonify({"error": "Intervalle minimum : 15 minutes"}), 400
        config.auto_sync_interval_minutes = interval

    config.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(
        {
            "auto_sync_enabled": config.auto_sync_enabled,
            "auto_sync_interval_minutes": config.auto_sync_interval_minutes,
        }
    )
