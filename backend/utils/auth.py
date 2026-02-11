from __future__ import annotations

import os
import datetime
import jwt
from flask import request, jsonify
from functools import wraps
from models import User

SECRET_KEY = os.getenv("JWT_SECRET", "secret-key")
TOKEN_EXPIRATION = int(os.getenv("JWT_EXPIRE", "3600"))
REFRESH_TOKEN_EXPIRATION = int(os.getenv("JWT_REFRESH_EXPIRE", "604800"))

_TOKEN_EXPIRATIONS = {
    "access": TOKEN_EXPIRATION,
    "refresh": REFRESH_TOKEN_EXPIRATION,
}


def _generate_token(user: User, token_type: str) -> str:
    expire = _TOKEN_EXPIRATIONS[token_type]
    payload = {
        "user_id": user.id,
        "type": token_type,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=expire),
    }
    if token_type == "access":
        payload["role"] = user.role
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def _decode_token(token: str, expected_type: str):
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def generate_access_token(user: User) -> str:
    return _generate_token(user, "access")


def generate_refresh_token(user: User) -> str:
    return _generate_token(user, "refresh")


def decode_token(token: str):
    return _decode_token(token, "access")


def decode_refresh_token(token: str):
    return _decode_token(token, "refresh")


def token_required(role: str | None = None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "Token manquant"}), 401
            token = auth_header.split(" ", 1)[1]
            try:
                data = decode_token(token)
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token expiré"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Token invalide"}), 401
            user = User.query.get(data.get("user_id"))
            if not user:
                return jsonify({"error": "Utilisateur introuvable"}), 401
            if role and user.role != role:
                return jsonify({"error": "Accès refusé"}), 403
            request.user = user
            return f(*args, **kwargs)

        return wrapper

    return decorator
