from flask import Blueprint

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
