import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flasgger import Swagger
from flask import Flask
from flask_cors import CORS
from models import db
from routes import register_routes
from utils.logging_config import configure_logging


def _cleanup_orphaned_jobs():
    """Reset any NightlyJob stuck in 'running' status at startup (e.g. after a server crash or hot-reload)."""
    try:
        from models import NightlyJob
        count = NightlyJob.query.filter_by(status="running").update(
            {
                "status": "failed",
                "finished_at": datetime.now(timezone.utc),
                "error_message": "Interrupted by server restart",
            }
        )
        if count:
            db.session.commit()
            logging.getLogger(__name__).warning(
                "Cleaned up %d orphaned nightly job(s) stuck in 'running' status.", count
            )
    except Exception:
        db.session.rollback()


def create_app():
    # Load environment variables from a local .env file if present
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(env_path)

    app = Flask(__name__)
    swagger_template = os.path.join(os.path.dirname(__file__), "swagger_template.yml")
    Swagger(app, template_file=swagger_template)

    frontend_origin = os.getenv("FRONTEND_URL", "*")
    origins = (
        [o.strip() for o in frontend_origin.split(",")] if frontend_origin else "*"
    )
    CORS(
        app,
        resources={r"/*": {"origins": origins}},
        expose_headers=["Content-Disposition"],
    )

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if database_url.startswith("sqlite"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "connect_args": {"cached_statements": 512},
        }
    db.init_app(app)
    configure_logging(app)

    with app.app_context():
        db.create_all()
        _cleanup_orphaned_jobs()

    register_routes(app)

    # Start Odoo auto-sync scheduler if opted-in
    if os.getenv("ENABLE_ODOO_SCHEDULER", "").lower() == "true":
        from utils.odoo_scheduler import OdooScheduler

        scheduler = OdooScheduler(app)
        scheduler.start()

    # Start nightly pipeline scheduler if opted-in
    if os.getenv("ENABLE_NIGHTLY_SCHEDULER", "false").lower() == "true":
        from utils.nightly_scheduler import NightlyScheduler

        nightly_scheduler = NightlyScheduler(app)
        nightly_scheduler.start()

    return app


app = create_app()

if __name__ == "__main__":

    app.logger.setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5001"))
    app.run(host=host, port=port)
