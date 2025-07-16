import uuid
from datetime import datetime

import pandas as pd
from flask import Blueprint, jsonify, request
from models import FormatImport, ImportHistory, TemporaryImport, db
from sqlalchemy import extract
from utils.calculations import recalculate_product_calculations

bp = Blueprint("imports", __name__)


@bp.route("/import_history", methods=["GET"])
def list_import_history():
    """List previous import operations.

    ---
    tags:
      - Imports
    responses:
      200:
        description: Import history records
    """
    histories = ImportHistory.query.order_by(ImportHistory.import_date.desc()).all()
    result = [
        {
            "id": h.id,
            "filename": h.filename,
            "supplier_id": h.supplier_id,
            "product_count": h.product_count,
            "import_date": h.import_date.isoformat(),
        }
        for h in histories
    ]
    return jsonify(result)


@bp.route("/verify_import/<int:supplier_id>", methods=["GET"])
def verify_import(supplier_id):
    """Verify if an import already exists for the current week for a supplier.

    ---
    tags:
      - Imports
    responses:
      200:
        description: Return if an import already exists for the current week for a supplier
    """

    verification = (
        ImportHistory.query.filter_by(supplier_id=supplier_id)
        .filter(
            extract("week", ImportHistory.import_date)
            == extract("week", datetime.utcnow())
        )
        .first()
    )
    if verification:
        return jsonify({"status": "error", "message": "Import already exists"}), 200
    return jsonify({"status": "success", "message": "Import does not exist"}), 200


@bp.route("/import", methods=["POST"])
def create_import():
    """Import a new Excel file.

    ---
    tags:
      - Imports
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: file
        type: file
        required: true
      - in: formData
        name: supplier_id
        type: integer
        required: false
    responses:
      200:
        description: Import result
    """

    from flask import current_app

    current_app.logger.debug(f"Headers: {request.headers}")
    current_app.logger.debug(f"Content-Type: {request.content_type}")

    if request.content_type == "application/json":
        data = request.get_json()
        current_app.logger.debug(f"JSON reçu: {data}")
    elif request.content_type.startswith("multipart/form-data"):
        current_app.logger.debug(f"Fichiers: {request.files}")
        current_app.logger.debug(f"Formulaire: {request.form}")
    else:
        raw_data = request.data
        current_app.logger.debug(f"Raw data: {raw_data}")

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    supplier_id = request.form.get("supplier_id")
    if supplier_id is not None:
        try:
            supplier_id = int(supplier_id)
        except ValueError:
            supplier_id = None

    TemporaryImport.query.delete()
    db.session.commit()

    df = pd.read_excel(file)
    df.columns = [str(c).lower().strip() for c in df.columns]

    # Apply column mappings defined for the supplier if available
    mappings = []
    if supplier_id:
        mappings = FormatImport.query.filter_by(supplier_id=supplier_id).all()
        if not mappings:
            current_app.logger.error("Aucun format d'import défini pour ce fournisseur")
            return (
                jsonify({"error": "Format d'import non trouvé pour ce fournisseur"}),
                400,
            )
    by_order = {
        m.column_order: (m.column_name or "").lower()
        for m in mappings
        if m.column_order is not None
    }

    for idx, col in enumerate(list(df.columns)):
        if idx in by_order:
            df.rename(columns={col: by_order[idx]}, inplace=True)

    if "description" in df.columns:
        df["description"] = df["description"].astype(str).str.strip()

    current_app.logger.debug(f"Colonnes du DataFrame final : {df.columns.tolist()}")
    current_app.logger.debug(
        f"Premières lignes du DataFrame :\n{df.head().to_string()}"
    )

    expected_types = {
        (m.column_name or "").lower(): (m.column_type or "").lower() for m in mappings
    }

    count_new = 0
    invalid_rows = 0
    count_update = 0

    for idx, row in df.iterrows():
        valid = True
        for col, typ in expected_types.items():
            if col not in row:
                continue
            val = row[col]
            if typ == "number":
                if pd.isna(pd.to_numeric(val, errors="coerce")):
                    valid = False
                    break
            elif typ == "string":
                if pd.isna(val):
                    valid = False
                    break
        if not valid:
            invalid_rows += 1
            continue

        count_new += 1
        temp = TemporaryImport(
            description=row.get("description"),
            model=row.get("model") or row.get("description"),
            quantity=row.get("quantity"),
            selling_price=row.get("selling_price"),
            ean=uuid.uuid4().hex[:20],
            supplier_id=supplier_id,
        )
        db.session.add(temp)

    history = ImportHistory(
        filename=file.filename, supplier_id=supplier_id, product_count=count_new
    )
    db.session.add(history)
    db.session.commit()

    with db.session.no_autoflush:
        recalculate_product_calculations()

    return jsonify(
        {
            "status": "success",
            "new": count_new,
            "updated": count_update,
            "invalid": invalid_rows,
        }
    )


@bp.route("/last_import/<int:supplier_id>", methods=["GET"])
def last_import(supplier_id):
    """Retrieve the last import for a supplier.

    ---
    tags:
      - Imports
    parameters:
      - in: path
        name: supplier_id
        required: true
        type: integer
    responses:
      200:
        description: Last import information or empty object
    """
    history = (
        ImportHistory.query.filter_by(supplier_id=supplier_id)
        .order_by(ImportHistory.import_date.desc())
        .first()
    )
    if not history:
        return jsonify({}), 200

    return jsonify(
        {
            "id": history.id,
            "filename": history.filename,
            "supplier_id": history.supplier_id,
            "product_count": history.product_count,
            "import_date": history.import_date.isoformat(),
        }
    )
