from flask import Blueprint, jsonify, request

from models import (
    Brand,
    Color,
    DeviceType,
    Exclusion,
    MemoryOption,
    Supplier,
    db,
)

bp = Blueprint('references', __name__)


@bp.route('/suppliers', methods=['GET'])
def list_suppliers():
    suppliers = Supplier.query.all()
    result = [
        {
            'id': s.id,
            'name': s.name,
            'email': s.email,
            'phone': s.phone,
            'address': s.address,
        }
        for s in suppliers
    ]
    return jsonify(result)


@bp.route('/brands', methods=['GET'])
def list_brands():
    brands = Brand.query.all()
    result = [{'id': b.id, 'brand': b.brand} for b in brands]
    return jsonify(result)


@bp.route('/colors', methods=['GET'])
def list_colors():
    colors = Color.query.all()
    result = [{'id': c.id, 'color': c.color} for c in colors]
    return jsonify(result)


@bp.route('/memory_options', methods=['GET'])
def list_memory_options():
    memories = MemoryOption.query.all()
    result = [{'id': m.id, 'memory': m.memory} for m in memories]
    return jsonify(result)


@bp.route('/device_types', methods=['GET'])
def list_device_types():
    types = DeviceType.query.all()
    result = [{'id': t.id, 'type': t.type} for t in types]
    return jsonify(result)


@bp.route('/exclusions', methods=['GET'])
def list_exclusions():
    exclusions = Exclusion.query.all()
    result = [{'id': e.id, 'term': e.term} for e in exclusions]
    return jsonify(result)


def _model_mapping():
    return {
        'suppliers': Supplier,
        'brands': Brand,
        'colors': Color,
        'memory_options': MemoryOption,
        'device_types': DeviceType,
        'exclusions': Exclusion,
    }


@bp.route('/references/<table>', methods=['GET'])
def get_reference_table(table):
    model = _model_mapping().get(table)
    if not model:
        return jsonify({'error': 'Unknown table'}), 400
    items = model.query.all()

    def serialize(obj):
        if isinstance(obj, Supplier):
            return {
                'id': obj.id,
                'name': obj.name,
                'email': obj.email,
                'phone': obj.phone,
                'address': obj.address,
            }
        if isinstance(obj, Brand):
            return {'id': obj.id, 'brand': obj.brand}
        if isinstance(obj, Color):
            return {'id': obj.id, 'color': obj.color}
        if isinstance(obj, MemoryOption):
            return {'id': obj.id, 'memory': obj.memory}
        if isinstance(obj, DeviceType):
            return {'id': obj.id, 'type': obj.type}
        if isinstance(obj, Exclusion):
            return {'id': obj.id, 'term': obj.term}
        return {}

    return jsonify([serialize(i) for i in items])


@bp.route('/references/<table>/<int:item_id>', methods=['PUT'])
def update_reference_item(table, item_id):
    model = _model_mapping().get(table)
    if not model:
        return jsonify({'error': 'Unknown table'}), 400
    item = model.query.get_or_404(item_id)
    data = request.json or {}
    for key, value in data.items():
        if hasattr(item, key):
            setattr(item, key, value)
    db.session.commit()
    return jsonify({'status': 'success'})


@bp.route('/references/<table>', methods=['POST'])
def create_reference_item(table):
    model = _model_mapping().get(table)
    if not model:
        return jsonify({'error': 'Unknown table'}), 400
    data = request.json or {}
    item = model(**data)
    db.session.add(item)
    db.session.commit()
    return jsonify({'id': item.id})


@bp.route('/references/<table>/<int:item_id>', methods=['DELETE'])
def delete_reference_item(table, item_id):
    model = _model_mapping().get(table)
    if not model:
        return jsonify({'error': 'Unknown table'}), 400
    item = model.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'status': 'deleted'})
