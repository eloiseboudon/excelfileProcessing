import os
import datetime
import jwt
from flask import request, jsonify
from functools import wraps
from models import User

SECRET_KEY = os.getenv("JWT_SECRET", "secret-key")
TOKEN_EXPIRATION = int(os.getenv("JWT_EXPIRE", "3600"))
REFRESH_TOKEN_EXPIRATION = int(os.getenv("JWT_REFRESH_EXPIRE", "604800"))


def generate_access_token(user: User) -> str:
    payload = {
        "user_id": user.id,
        "role": user.role,
        "type": "access",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=TOKEN_EXPIRATION),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def generate_refresh_token(user: User) -> str:
    payload = {
        "user_id": user.id,
        "type": "refresh",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=REFRESH_TOKEN_EXPIRATION),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token: str):
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def decode_refresh_token(token: str):
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    if payload.get("type") != "refresh":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


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
                return jsonify({"error": "Token expir\u00e9"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Token invalide"}), 401
            user = User.query.get(data.get("user_id"))
            if not user:
                return jsonify({"error": "Utilisateur introuvable"}), 401
            if role and user.role != role:
                return jsonify({"error": "Acc\u00e8s refus\u00e9"}), 403
            request.user = user
            return f(*args, **kwargs)

        return wrapper

    return decorator
