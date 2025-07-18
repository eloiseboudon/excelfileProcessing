import os
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
        return jsonify({"status": "error", "message": "Import déjà existant"}), 200
    return jsonify({"status": "success", "message": "Import non existant"}), 200


@bp.route("/import_preview", methods=["POST"])
def preview_import():
    """Return a preview of the first five valid rows from an Excel file.

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
        description: Rows preview
    """

    if "file" not in request.files:
        return jsonify({"error": "Pas de fichier fourni"}), 400

    file = request.files["file"]
    supplier_id = request.form.get("supplier_id")
    if supplier_id is not None:
        try:
            supplier_id = int(supplier_id)
        except ValueError:
            supplier_id = None

    df = pd.read_excel(file)
    df.columns = [str(c).lower().strip() for c in df.columns]

    for col in ["quantity", "selling_price"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    mappings = []
    if supplier_id:
        mappings = FormatImport.query.filter_by(supplier_id=supplier_id).all()
        if not mappings:
            return (
                jsonify({"error": "Format d'import non trouvé pour ce fournisseur"}),
                400,
            )

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
        return (
            jsonify(
                {
                    "error": "Colonnes manquantes après le mapping: "
                    + ", ".join(missing_columns)
                }
            ),
            400,
        )

    if "description" in df.columns:
        df["description"] = df["description"].astype(str).str.strip()

    preview_rows = []
    for _, row in df.iterrows():
        quantity = row.get("quantity")
        selling_price = row.get("selling_price")
        if pd.isna(quantity) or pd.isna(selling_price):
            continue
        preview_rows.append(
            {
                "description": row.get("description"),
                "model": row.get("model") or row.get("description"),
                "quantity": int(quantity),
                "selling_price": float(selling_price),
            }
        )
        if len(preview_rows) >= 5:
            break

    return jsonify({"preview": preview_rows})


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
        return jsonify({"error": "Pas de fichier fourni"}), 400

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
    mappings = FormatImport.query.filter_by(supplier_id=supplier_id).all()
    if not mappings:
        current_app.logger.error("Aucun format d'import défini pour ce fournisseur")
        return (
            jsonify({"error": "Format d'import non trouvé pour ce fournisseur"}),
            400,
        )

    # Find mappings for quantity, selling_price, description and model
    quantity_mapping = next(
        (m for m in mappings if m.column_name and m.column_name.lower() == "quantity"),
        None,
    )
    selling_price_mapping = next(
        (
            m
            for m in mappings
            if m.column_name and m.column_name.lower() == "selling_price"
        ),
        None,
    )
    description_mapping = next(
        (
            m
            for m in mappings
            if m.column_name and m.column_name.lower() == "description"
        ),
        None,
    )
    model_mapping = next(
        (m for m in mappings if m.column_name and m.column_name.lower() == "model"),
        None,
    )

    if not quantity_mapping or not selling_price_mapping or not description_mapping:
        current_app.logger.error(
            "Les colonnes quantity, selling_price et description doivent être configurées dans le format d'import"
        )
        return (
            jsonify(
                {
                    "error": "Les colonnes quantity, selling_price et description doivent être configurées dans le format d'import"
                }
            ),
            400,
        )

    # Map Excel columns to standardized names
    for m in mappings:
        if m.column_order is None or not m.column_name:
            continue
        idx = m.column_order - 1
        if 0 <= idx < len(df.columns):
            df[(m.column_name or "").lower()] = df.iloc[:, idx]

    required_columns = [
        (m.column_name or "").lower() for m in mappings if m.column_name
    ]

    # Process description column
    if description_mapping:
        description_col = description_mapping.column_name.lower()
        if description_col in df.columns:
            df[description_col] = df[description_col].astype(str).str.strip()
    missing_columns = [c for c in required_columns if c not in df.columns]
    if missing_columns:
        current_app.logger.error(
            f"Required columns missing after renaming: {missing_columns}"
        )
        return (
            jsonify(
                {
                    "error": "Colonnes manquantes après le mapping: "
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

    count_new = 0
    invalid_rows = 0

    for idx, row in df.iterrows():
        # Get quantity and selling_price using their mappings
        quantity_col = quantity_mapping.column_name.lower()
        selling_price_col = selling_price_mapping.column_name.lower()
        description_col = description_mapping.column_name.lower()
        model_col = model_mapping.column_name.lower() if model_mapping else None
        quantity = row.get(quantity_col)
        selling_price = row.get(selling_price_col)

        if pd.isna(quantity) or pd.isna(selling_price):
            invalid_rows += 1
            log_entries.append(
                f"{idx + 2}\t{row.get(description_col, '')}\tinvalid quantity or selling_price-{row.get(quantity_col, '')}-{row.get(selling_price_col, '')}"
            )
            continue

        count_new += 1
        # Get description and model using their mappings
        description = row.get(description_col)
        model = row.get(model_col) if model_col else description

        temp = TemporaryImport(
            description=description,
            model=model,
            quantity=int(quantity),
            selling_price=float(selling_price),
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
