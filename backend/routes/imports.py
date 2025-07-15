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
            extract('week', ImportHistory.import_date)
            == extract('week', datetime.utcnow())
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
    df_raw = df.copy()

    # Apply column mappings defined for the supplier if available
    mappings = (
        FormatImport.query.filter_by(supplier_id=supplier_id).all()
        if supplier_id
        else []
    )
    by_name = {
        (m.column_name or '').lower(): (m.column_type or '').lower()
        for m in mappings
        if m.column_name
    }
    by_order = {
        m.column_order: (m.column_type or '').lower()
        for m in mappings
        if m.column_order is not None
    }

    for idx, col in enumerate(list(df.columns)):
        if idx in by_order:
            df.rename(columns={col: by_order[idx]}, inplace=True)

    for src, target in by_name.items():
        if src in df.columns:
            df.rename(columns={src: target}, inplace=True)

    if "sellingprice" in df.columns and "selling_price" not in df.columns:
        df.rename(columns={"sellingprice": "selling_price"}, inplace=True)

    if "description" in df.columns:
        df["description"] = df["description"].astype(str).str.strip()

    expected_types = {
        (m.column_name or "").lower(): (m.column_type or "").lower()
        for m in mappings
    }

    count_new = 0
    invalid_rows = 0
    count_update = 0

    # The EAN column is unreliable and may be missing or empty.
    # Do not use it to filter or deduplicate rows.

    for idx, row in df.iterrows():
        raw_row = df_raw.iloc[idx]
        valid = True
        for col, typ in expected_types.items():
            if col not in raw_row:
                continue
            val = raw_row[col]
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
        ean_raw = row.get("ean")

        # When column mappings are misconfigured pandas may return a Series
        # instead of a scalar. In that case just grab the first value.
        if isinstance(ean_raw, pd.Series):
            ean_raw = ean_raw.iloc[0]

        ean_str = str(ean_raw).strip()

        # Consider empty strings and values like "unknown" as missing so we
        # generate a unique placeholder. This prevents UNIQUE constraint
        # violations when suppliers use repeated dummy values.
        if pd.isna(ean_raw) or ean_str == "" or ean_str.lower() == "unknown":
            # The database field is limited to 20 characters, so truncate the
            # generated UUID accordingly.
            ean_value = uuid.uuid4().hex[:20]
        else:
            # Truncate real EANs that exceed the column length to avoid errors.
            ean_value = ean_str[:20]

        temp = TemporaryImport(
            description=row.get("description"),
            model=row.get("model", row.get("description")),
            quantity=row.get("quantity"),
            selling_price=row.get("selling_price"),
            ean=ean_value,
            supplier_id=supplier_id,
        )
        db.session.add(temp)

    recalculate_product_calculations()

    history = ImportHistory(
        filename=file.filename, supplier_id=supplier_id, product_count=count_new
    )
    db.session.add(history)
    db.session.commit()

    return jsonify({"status": "success", "new": count_new, "updated": count_update, "invalid": invalid_rows})


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
