from flask import Blueprint, jsonify, request
from utils.auth import token_required
from models import (
    Brand,
    Color,
    ColorTranslation,
    DeviceType,
    Exclusion,
    FormatImport,
    MemoryOption,
    Product,
    Supplier,
    db,
)
from utils.calculations import update_product_calculations_for_memory_option

bp = Blueprint("references", __name__)


def _model_mapping():
    return {
        "suppliers": Supplier,
        "brands": Brand,
        "colors": Color,
        "memory_options": MemoryOption,
        "device_types": DeviceType,
        "exclusions": Exclusion,
        "color_translations": ColorTranslation,
        "format_imports": FormatImport,
    }


def _update_products_for_color_translation(sources, target_color_id):
    if not target_color_id:
        return
    if isinstance(sources, str):
        sources = [sources]
    for s in sources:
        if not s:
            continue
        term = f"%{s.lower()}%"
        products = Product.query.filter(Product.description.ilike(term)).all()
        for p in products:
            p.color_id = target_color_id
    if sources:
        db.session.commit()


@bp.route("/references/<table>", methods=["GET"])
@token_required("admin")
def get_reference_table(table):
    """Retrieve a full reference table.

    ---
    tags:
      - References
    parameters:
      - in: path
        name: table
        type: string
        required: true
    responses:
      200:
        description: Items from the requested table
    """
    model = _model_mapping().get(table)
    if not model:
        return jsonify({"error": "Table inconnue"}), 400
    items = model.query.all()

    def serialize(obj):
        if isinstance(obj, Supplier):
            return {
                "id": obj.id,
                "name": obj.name,
                "email": obj.email,
                "phone": obj.phone,
                "address": obj.address,
            }
        if isinstance(obj, Brand):
            return {"id": obj.id, "brand": obj.brand}
        if isinstance(obj, Color):
            return {"id": obj.id, "color": obj.color}
        if isinstance(obj, MemoryOption):
            return {"id": obj.id, "memory": obj.memory, "tcp_value": obj.tcp_value}
        if isinstance(obj, DeviceType):
            return {"id": obj.id, "type": obj.type}
        if isinstance(obj, Exclusion):
            return {"id": obj.id, "term": obj.term}
        if isinstance(obj, ColorTranslation):
            return {
                "id": obj.id,
                "color_source": obj.color_source,
                "color_target": obj.color_target,
            }
        if isinstance(obj, FormatImport):
            return {
                "id": obj.id,
                "supplier_id": obj.supplier_id,
                "column_name": obj.column_name,
                "column_order": obj.column_order,
            }
        return {}

    return jsonify([serialize(i) for i in items])


@bp.route("/references/<table>/<int:item_id>", methods=["PUT"])
@token_required("admin")
def update_reference_item(table, item_id):
    """Update an item in a reference table.

    ---
    tags:
      - References
    parameters:
      - in: path
        name: table
        required: true
        type: string
      - in: path
        name: item_id
        required: true
        type: integer
      - in: body
        name: body
        schema:
          type: object
    responses:
      200:
        description: Update status
    """
    model = _model_mapping().get(table)
    if not model:
        return jsonify({"error": "Table inconnue"}), 400
    item = model.query.get_or_404(item_id)
    data = request.json or {}
    old_source = None
    if isinstance(item, ColorTranslation):
        old_source = item.color_source
    for key, value in data.items():
        if hasattr(item, key):
            setattr(item, key, value)
    db.session.commit()
    if table == "color_translations":
        _update_products_for_color_translation(
            [old_source, item.color_source], item.color_target_id
        )
    if table == "memory_options" and "tcp_value" in data:
        update_product_calculations_for_memory_option(item.id)
    return jsonify({"status": "success"})


@bp.route("/references/<table>", methods=["POST"])
@token_required("admin")
def create_reference_item(table):
    """Create an item in a reference table.

    ---
    tags:
      - References
    parameters:
      - in: path
        name: table
        required: true
        type: string
      - in: body
        name: body
        schema:
          type: object
    responses:
      200:
        description: Identifier of created item
    """
    model = _model_mapping().get(table)
    if not model:
        return jsonify({"error": "Table inconnue"}), 400
    data = request.json or {}
    item = model(**data)
    db.session.add(item)
    db.session.commit()
    if table == "color_translations":
        _update_products_for_color_translation(item.color_source, item.color_target_id)
    return jsonify({"id": item.id})


@bp.route("/references/<table>/<int:item_id>", methods=["DELETE"])
@token_required("admin")
def delete_reference_item(table, item_id):
    """Delete an item from a reference table.

    ---
    tags:
      - References
    parameters:
      - in: path
        name: table
        required: true
        type: string
      - in: path
        name: item_id
        required: true
        type: integer
    responses:
      200:
        description: Deletion status
    """
    model = _model_mapping().get(table)
    if not model:
        return jsonify({"error": "Table inconnue"}), 400
    item = model.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"status": "deleted"})
