from flask import Blueprint, jsonify, request
from models import User, db
from utils.auth import token_required

bp = Blueprint("users", __name__)


@bp.route("/users", methods=["GET"])
@token_required("admin")
def list_users():
    users = User.query.all()
    return jsonify(
        [
            {
                "id": u.id,
                "username": u.username,
                "role": u.role,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "email": u.email,
            }
            for u in users
        ]
    )


@bp.route("/users", methods=["POST"])
@token_required("admin")
def create_user():
    data = request.json or {}
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    role = data.get("role", "client")
    if not email:
        return jsonify({"error": "email requis"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Utilisateur existe"}), 400
    user = User(email=email, role=role, first_name=first_name, last_name=last_name)
    user.set_password("changeme")
    db.session.add(user)
    db.session.commit()
    return jsonify(
        {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
    )


@bp.route("/users/<int:user_id>", methods=["PUT"])
@token_required("admin")
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json or {}
    if "email" in data:
        user.email = data["email"]
    if "role" in data:
        user.role = data["role"]
    if "first_name" in data:
        user.first_name = data["first_name"]
    if "last_name" in data:
        user.last_name = data["last_name"]
    if "email" in data:
        user.email = data["email"]
    db.session.commit()
    return jsonify({"status": "success"})
