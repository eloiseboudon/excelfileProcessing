from flask import Blueprint, request, jsonify
import jwt
from models import User
from utils.auth import (
    generate_access_token,
    generate_refresh_token,
    decode_refresh_token,
)

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and return access tokens.

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
        description: Tokens generated for the authenticated user
      400:
        description: Missing credentials in the request body
      401:
        description: Invalid email or password
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Identifiants invalides"}), 401

    access_token = generate_access_token(user)
    refresh_token = generate_refresh_token(user)
    return jsonify({"token": access_token, "refresh_token": refresh_token, "role": user.role})


@bp.route("/refresh", methods=["POST"])
def refresh():
    """Exchange a refresh token for a new access token.

    ---
    tags:
      - Auth
    consumes:
      - application/json
    parameters:
      - in: body
        name: payload
        schema:
          type: object
          required:
            - refresh_token
          properties:
            refresh_token:
              type: string
    responses:
      200:
        description: New access token generated from the provided refresh token
      400:
        description: Missing refresh token in the request body
      401:
        description: Expired or invalid refresh token
    """
    data = request.get_json(silent=True) or {}
    token = data.get("refresh_token")
    if not token:
        return jsonify({"error": "Refresh token requis"}), 400
    try:
        payload = decode_refresh_token(token)
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expir\u00e9"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Token invalide"}), 401

    user = User.query.get(payload.get("user_id"))
    if not user:
        return jsonify({"error": "Utilisateur introuvable"}), 401

    access_token = generate_access_token(user)
    refresh_token = generate_refresh_token(user)
    return jsonify({"token": access_token, "refresh_token": refresh_token, "role": user.role})
