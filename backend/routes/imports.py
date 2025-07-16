from datetime import datetime
import os

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

    # Prepare invalid rows log
    log_dir = os.path.join(os.path.dirname(__file__), "..", "log")
    os.makedirs(log_dir, exist_ok=True)
    log_filename = datetime.utcnow().strftime("import_%Y%m%d_%H%M%S.txt")
    log_path = os.path.join(log_dir, log_filename)
    log_entries = ["line\tdescription\treason"]

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

    # Map Excel columns to standardized names. Duplicate column_order values
    # are allowed and will copy data from the same source column.
    for m in mappings:
        if m.column_order is None or not m.column_name:
            continue
        idx = m.column_order - 1
        if 0 <= idx < len(df.columns):
            df[(m.column_name or "").lower()] = df.iloc[:, idx]

    required_columns = [
        (m.column_name or "").lower() for m in mappings if m.column_name
    ]
    missing_columns = [c for c in required_columns if c not in df.columns]
    if missing_columns:
        current_app.logger.error(
            f"Required columns missing after renaming: {missing_columns}"
        )
        return (
            jsonify(
                {
                    "error": "Missing columns after mapping: "
                    + ", ".join(missing_columns)
                }
            ),
            400,
        )

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

    for idx, row in df.iterrows():
        valid = True
        reason = ""
        for col, typ in expected_types.items():
            if col not in row:
                continue
            val = row[col]
            if typ == "number":
                if pd.isna(pd.to_numeric(val, errors="coerce")):
                    valid = False
                    reason = f"invalid type for {col}"
                    break
            elif typ == "string":
                if pd.isna(val):
                    valid = False
                    reason = f"missing value for {col}"
                    break
        if not valid:
            invalid_rows += 1
            log_entries.append(
                f"{idx + 2}\t{row.get('description', '')}\t{reason}"
            )
            continue

        quantity = pd.to_numeric(row.get("quantity"), errors="coerce")
        selling_price = pd.to_numeric(row.get("selling_price"), errors="coerce")
        if pd.isna(quantity) or pd.isna(selling_price):
            invalid_rows += 1
            log_entries.append(
                f"{idx + 2}\t{row.get('description', '')}\tinvalid quantity or selling_price"
            )
            continue

        count_new += 1
        temp = TemporaryImport(
            description=row.get("description"),
            model=row.get("model") or row.get("description"),
            quantity=row.get("quantity"),
            selling_price=row.get("selling_price"),
            supplier_id=supplier_id,
        )
        db.session.add(temp)

    # Write invalid rows report
    with open(log_path, "w", encoding="utf-8") as log_file:
        for entry in log_entries:
            log_file.write(entry + "\n")

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
