"""API endpoints for activity logs and application log file."""

from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from models import ActivityLog, User, db
from utils.auth import token_required

bp = Blueprint("logs", __name__)


@bp.route("/logs/activity", methods=["GET"])
@token_required("admin")
def list_activity_logs():
    """Return paginated activity logs."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)
    category = request.args.get("category", type=str)
    action = request.args.get("action", type=str)

    query = ActivityLog.query
    if category:
        query = query.filter_by(category=category)
    if action:
        query = query.filter(ActivityLog.action.ilike(f"%{action}%"))

    query = query.order_by(ActivityLog.timestamp.desc())
    total = query.count()
    items = (
        query.outerjoin(User, ActivityLog.user_id == User.id)
        .add_columns(User.username)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    results = []
    for log_entry, username in items:
        results.append({
            "id": log_entry.id,
            "timestamp": log_entry.timestamp.isoformat() if log_entry.timestamp else None,
            "action": log_entry.action,
            "category": log_entry.category,
            "user_id": log_entry.user_id,
            "username": username,
            "details": log_entry.details,
            "ip_address": log_entry.ip_address,
        })

    return jsonify({
        "items": results,
        "total": total,
        "page": page,
        "per_page": per_page,
    })


def _tail_lines(path: Path, n: int) -> list:
    """Read the last *n* lines of a file without loading it entirely."""
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        if size == 0:
            return []
        chunk_size = 8192
        lines: list[bytes] = []
        position = size
        remainder = b""
        while position > 0 and len(lines) <= n:
            read_size = min(chunk_size, position)
            position -= read_size
            f.seek(position)
            chunk = f.read(read_size) + remainder
            remainder = b""
            parts = chunk.split(b"\n")
            if position > 0:
                remainder = parts[0]
                parts = parts[1:]
            lines = parts + lines
        # Filter empty entries (e.g. trailing newline) before slicing
        lines = [l for l in lines if l]
        return [l.decode("utf-8", errors="replace") for l in lines[-n:]]


def _count_lines(path: Path) -> int:
    """Count newlines in a file using buffered binary reads."""
    count = 0
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            count += chunk.count(b"\n")
    return count


@bp.route("/logs/app", methods=["GET"])
@token_required("admin")
def read_app_logs():
    """Return the last N lines of the application log file."""
    lines_count = min(request.args.get("lines", 200, type=int), 1000)

    log_path = Path(current_app.root_path) / "logs" / "app.log"
    if not log_path.exists():
        return jsonify({"lines": [], "total_lines": 0})

    tail = _tail_lines(log_path, lines_count)
    return jsonify({"lines": tail, "total_lines": _count_lines(log_path)})
