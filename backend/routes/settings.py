from flask import Blueprint, jsonify, request
from models import GraphSetting, db

bp = Blueprint("settings", __name__)


@bp.route("/graph_settings", methods=["GET"])
def list_graph_settings():
    settings = GraphSetting.query.all()
    return jsonify([{"name": s.name, "visible": s.visible} for s in settings])


@bp.route("/graph_settings/<name>", methods=["PUT"])
def update_graph_setting(name):
    data = request.json or {}
    visible = bool(data.get("visible", False))
    setting = GraphSetting.query.filter_by(name=name).first()
    if setting:
        setting.visible = visible
    else:
        setting = GraphSetting(name=name, visible=visible)
        db.session.add(setting)
    db.session.commit()
    return jsonify({"status": "success"})
