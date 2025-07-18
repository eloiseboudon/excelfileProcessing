from flask import Blueprint, request, jsonify
from models import User
from utils.auth import generate_token

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "Nom d'utilisateur et mot de passe requis"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Identifiants invalides"}), 401

    token = generate_token(user)
    return jsonify({"token": token, "role": user.role})
