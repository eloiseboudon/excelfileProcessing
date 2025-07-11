from flask import Blueprint, jsonify, request
import pandas as pd

from models import ImportHistory, TemporaryImport, ProductReference, db

bp = Blueprint('imports', __name__)


@bp.route('/import_history', methods=['GET'])
def list_import_history():
    histories = ImportHistory.query.order_by(ImportHistory.import_date.desc()).all()
    result = [
        {
            'id': h.id,
            'filename': h.filename,
            'supplier_id': h.supplier_id,
            'product_count': h.product_count,
            'import_date': h.import_date.isoformat(),
        }
        for h in histories
    ]
    return jsonify(result)


@bp.route('/import', methods=['POST'])
def create_import():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    supplier_id = request.form.get('supplier_id')
    if supplier_id is not None:
        try:
            supplier_id = int(supplier_id)
        except ValueError:
            supplier_id = None

    TemporaryImport.query.delete()
    db.session.commit()

    df = pd.read_excel(file)
    df.columns = [c.lower().strip() for c in df.columns]
    if 'description' in df.columns:
        df['description'] = df['description'].astype(str).str.strip()
    df.drop_duplicates(subset=['ean'], inplace=True)
    df = df[df['ean'].notna()]
    count_new = 0
    count_update = 0
    for _, row in df.iterrows():
        ean_value = str(int(row['ean']))
        temp = TemporaryImport(
            description=row.get('description'),
            quantity=row.get('quantity', None),
            selling_price=row.get('sellingprice', None),
            ean=ean_value,
            supplier_id=supplier_id,
        )
        db.session.add(temp)

        ref = ProductReference.query.filter_by(ean=ean_value, supplier_id=supplier_id).first()
        if ref:
            ref.description = row.get('description')
            ref.quantity = row.get('quantity', None)
            ref.selling_price = row.get('sellingprice', None)
            ref.supplier_id = supplier_id
            count_update += 1
        else:
            ref = ProductReference(
                description=row.get('description'),
                quantity=row.get('quantity', None),
                selling_price=row.get('sellingprice', None),
                ean=ean_value,
                supplier_id=supplier_id,
            )
            count_new += 1
            db.session.add(ref)

    history = ImportHistory(filename=file.filename, supplier_id=supplier_id, product_count=len(df))
    db.session.add(history)

    db.session.commit()
    return jsonify({'status': 'success', 'new': count_new, 'updated': count_update})


@bp.route('/last_import/<int:supplier_id>', methods=['GET'])
def last_import(supplier_id):
    history = (
        ImportHistory.query.filter_by(supplier_id=supplier_id)
        .order_by(ImportHistory.import_date.desc())
        .first()
    )
    if not history:
        return jsonify({}), 200

    return jsonify(
        {
            'id': history.id,
            'filename': history.filename,
            'supplier_id': history.supplier_id,
            'product_count': history.product_count,
            'import_date': history.import_date.isoformat(),
        }
    )
