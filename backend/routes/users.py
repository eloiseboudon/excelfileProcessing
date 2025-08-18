from flask import Blueprint, jsonify, request
from models import User, db
from utils.auth import token_required

bp = Blueprint("users", __name__)


@bp.route("/users", methods=["GET"])
@token_required("admin")
def list_users():
    users = User.query.all()
    return jsonify([
        {"id": u.id, "username": u.username, "role": u.role} for u in users
    ])


@bp.route("/users", methods=["POST"])
@token_required("admin")
def create_user():
    data = request.json or {}
    username = data.get("username")
    role = data.get("role", "client")
    if not username:
        return jsonify({"error": "username requis"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Utilisateur existe"}), 400
    user = User(username=username, role=role)
    user.set_password("changeme")
    db.session.add(user)
    db.session.commit()
    return jsonify({"id": user.id, "username": user.username, "role": user.role})


@bp.route("/users/<int:user_id>", methods=["PUT"])
@token_required("admin")
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json or {}
    if "username" in data:
        user.username = data["username"]
    if "role" in data:
        user.role = data["role"]
    db.session.commit()
    return jsonify({"status": "success"})

