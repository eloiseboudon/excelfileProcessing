import logging
import os

from dotenv import load_dotenv
from flasgger import Swagger
from flask import Flask
from flask_cors import CORS
from models import db
from routes import register_routes


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

    with app.app_context():
        db.create_all()

    register_routes(app)

    # Start Odoo auto-sync scheduler if opted-in
    if os.getenv("ENABLE_ODOO_SCHEDULER", "").lower() == "true":
        from utils.odoo_scheduler import OdooScheduler

        scheduler = OdooScheduler(app)
        scheduler.start()

    return app


app = create_app()

if __name__ == "__main__":

    app.logger.setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5001"))
    app.run(host=host, port=port)
