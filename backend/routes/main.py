from datetime import datetime, timezone

from flask import Blueprint, jsonify
from sqlalchemy import text

from models import db

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """Simple health check endpoint.

    ---
    tags:
      - Main
    responses:
      200:
        description: API is reachable
    """
    return {"message": "Hello World"}


@bp.route('/health')
def health():
    """Deep health check — verifies DB connectivity.

    ---
    tags:
      - Main
    responses:
      200:
        description: API and database are healthy
      503:
        description: Database unreachable
    """
    try:
        db.session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        return jsonify({"status": "unhealthy", "db": "unreachable", "timestamp": datetime.now(timezone.utc).isoformat()}), 503

    return jsonify({"status": "healthy", "db": db_status, "timestamp": datetime.now(timezone.utc).isoformat()})
