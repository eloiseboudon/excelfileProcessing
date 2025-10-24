from flask import Blueprint, jsonify, request
from models import User, db
from utils.auth import token_required

bp = Blueprint("users", __name__)


@bp.route("/users", methods=["GET"])
@token_required("admin")
def list_users():
    """List all registered users.

    ---
    tags:
      - Users
    responses:
      200:
        description: Array of users with their roles and contact information
    """
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
    """Create a new user with a temporary password.

    ---
    tags:
      - Users
    consumes:
      - application/json
    parameters:
      - in: body
        name: payload
        schema:
          type: object
          required:
            - email
          properties:
            email:
              type: string
              format: email
            username:
              type: string
            role:
              type: string
            first_name:
              type: string
            last_name:
              type: string
    responses:
      200:
        description: Created user details
      400:
        description: Invalid payload or duplicate user
    """
    data = request.json or {}
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    email = data.get("email")
    role = data.get("role", "client")
    username = data.get("username")
    if not email:
        return jsonify({"error": "email requis"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Utilisateur existe"}), 400
    user = User(
        email=email,
        username=username,
        role=role,
        first_name=first_name,
        last_name=last_name,
    )
    user.set_password("changeme")
    db.session.add(user)
    db.session.commit()
    return jsonify(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
    )


@bp.route("/users/<int:user_id>", methods=["PUT"])
@token_required("admin")
def update_user(user_id):
    """Update user attributes.

    ---
    tags:
      - Users
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
      - in: body
        name: payload
        schema:
          type: object
          properties:
            username:
              type: string
            email:
              type: string
              format: email
            role:
              type: string
            first_name:
              type: string
            last_name:
              type: string
    responses:
      200:
        description: Confirmation that the user has been updated
    """
    user = User.query.get_or_404(user_id)
    data = request.json or {}
    if "username" in data:
        user.username = data["username"]
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


@bp.route("/users/<int:user_id>", methods=["DELETE"])
@token_required("admin")
def delete_user(user_id):
    """Delete a user.

    ---
    tags:
      - Users
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      200:
        description: Confirmation that the user has been deleted
    """
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"status": "success"})
