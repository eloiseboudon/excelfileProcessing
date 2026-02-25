import os

import jwt
from flask import Blueprint, make_response, request, jsonify
from models import User, db
from utils.activity import log_activity
from utils.auth import (
    generate_access_token,
    generate_refresh_token,
    decode_refresh_token,
    REFRESH_TOKEN_EXPIRATION,
)

bp = Blueprint("auth", __name__)

COOKIE_SECURE = os.getenv("FLASK_ENV", "production") != "development"
COOKIE_SAMESITE = "Lax"
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN") or None


def _check_origin():
    """Reject cross-origin POST requests (defense-in-depth CSRF protection)."""
    origin = request.headers.get("Origin")
    if not origin:
        # Requests without Origin (same-origin navigations, curl) are allowed
        return None
    allowed = os.getenv("FRONTEND_URL", "").split(",")
    allowed = [o.strip().rstrip("/") for o in allowed if o.strip()]
    if origin.rstrip("/") not in allowed:
        return jsonify({"error": "Origin not allowed"}), 403
    return None


def _set_refresh_cookie(response, token):
    response.set_cookie(
        "refresh_token",
        token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        domain=COOKIE_DOMAIN,
        max_age=REFRESH_TOKEN_EXPIRATION,
        path="/",
    )


@bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and return an access token.

    The refresh token is set as an HTTPOnly cookie.

    ---
    tags:
      - Auth
    consumes:
      - application/json
    parameters:
      - in: body
        name: credentials
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              format: email
            password:
              type: string
    responses:
      200:
        description: Access token generated for the authenticated user
      400:
        description: Missing credentials in the request body
      401:
        description: Invalid email or password
    """
    origin_error = _check_origin()
    if origin_error:
        return origin_error

    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Identifiants invalides"}), 401

    log_activity("user.login", details={"email": email}, user_id=user.id, commit=True)

    access_token = generate_access_token(user)
    refresh_token = generate_refresh_token(user)

    response = make_response(jsonify({"token": access_token, "role": user.role}))
    _set_refresh_cookie(response, refresh_token)
    return response


@bp.route("/refresh", methods=["POST"])
def refresh():
    """Exchange a refresh token (from HTTPOnly cookie) for a new access token.

    ---
    tags:
      - Auth
    responses:
      200:
        description: New access token generated from the refresh cookie
      401:
        description: Missing, expired or invalid refresh token
    """
    origin_error = _check_origin()
    if origin_error:
        return origin_error

    token = request.cookies.get("refresh_token")
    if not token:
        return jsonify({"error": "Refresh token manquant"}), 401
    try:
        payload = decode_refresh_token(token)
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expiré"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Token invalide"}), 401

    user = db.session.get(User, payload.get("user_id"))
    if not user:
        return jsonify({"error": "Utilisateur introuvable"}), 401

    access_token = generate_access_token(user)
    new_refresh_token = generate_refresh_token(user)

    response = make_response(jsonify({"token": access_token, "role": user.role}))
    _set_refresh_cookie(response, new_refresh_token)
    return response


@bp.route("/logout", methods=["POST"])
def logout():
    """Clear the refresh token cookie.

    ---
    tags:
      - Auth
    responses:
      200:
        description: Cookie cleared
    """
    origin_error = _check_origin()
    if origin_error:
        return origin_error

    response = make_response(jsonify({"status": "ok"}))
    response.delete_cookie("refresh_token", path="/", domain=COOKIE_DOMAIN)
    return response
