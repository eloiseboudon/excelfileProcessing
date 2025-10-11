import os
from datetime import datetime
from typing import Any

import pandas as pd
from flask import Blueprint, current_app, jsonify, request
from models import (
    ApiEndpoint,
    ApiFetchJob,
    FormatImport,
    ImportHistory,
    MappingVersion,
    Supplier,
    SupplierAPI,
    TemporaryImport,
    db,
)
from sqlalchemy import extract, func
from sqlalchemy.orm import joinedload
from utils.auth import token_required
from utils.calculations import recalculate_product_calculations
from utils.etl import run_fetch_job


def _normalize_column_key(name: str | None) -> str:
    """Return a normalized identifier for a mapped column name."""

    return "".join(ch for ch in (name or "").lower() if ch.isalnum())


def _select_endpoint(
    supplier_id: int,
    endpoint_id: int | None,
    endpoint_name: str | None,
) -> ApiEndpoint | None:
    base_query = (
        ApiEndpoint.query.join(SupplierAPI).filter(SupplierAPI.supplier_id == supplier_id)
    )

    if endpoint_id is not None:
        endpoint = base_query.filter(ApiEndpoint.id == endpoint_id).first()
        if endpoint:
            return endpoint

    if endpoint_name:
        endpoint = (
            base_query.filter(
                func.lower(ApiEndpoint.name) == endpoint_name.strip().lower()
            )
            .order_by(ApiEndpoint.id.asc())
            .first()
        )
        if endpoint:
            return endpoint

    endpoints = base_query.all()
    if len(endpoints) == 1:
        return endpoints[0]
    return None


def _select_mapping(endpoint: ApiEndpoint, mapping_version_id: int | None) -> MappingVersion | None:
    query = MappingVersion.query.filter_by(supplier_api_id=endpoint.supplier_api_id)
    if mapping_version_id is not None:
        mapping = query.filter_by(id=mapping_version_id).first()
        if mapping:
            return mapping

    return (
        query.filter_by(is_active=True)
        .order_by(MappingVersion.version.desc(), MappingVersion.id.desc())
        .first()
    )



def _clean_cell(value: Any) -> str | None:
    """Convert a raw dataframe cell to a clean string value."""

    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned or cleaned.lower() == "nan":
            return None
        return cleaned
    if pd.isna(value):
        return None
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value).strip()
    if isinstance(value, int):
        return str(value)
    return str(value).strip()

bp = Blueprint("imports", __name__)


@bp.route("/supplier_api/config", methods=["GET"])
@token_required("admin")
def list_supplier_api_config():
    """Return API configuration overview for each supplier."""

    suppliers = (
        Supplier.query.options(
            joinedload(Supplier.apis)
            .joinedload(SupplierAPI.endpoints),
            joinedload(Supplier.apis)
            .joinedload(SupplierAPI.mappings)
            .joinedload(MappingVersion.fields),
        )
        .order_by(Supplier.name.asc())
        .all()
    )

    result = []
    for supplier in suppliers:
        supplier_payload = {
            "id": supplier.id,
            "name": supplier.name,
            "apis": [],
        }

        for supplier_api in sorted(supplier.apis, key=lambda api: api.id or 0):
            endpoints = [
                {
                    "id": endpoint.id,
                    "name": endpoint.name,
                    "method": endpoint.method,
                    "path": endpoint.path,
                    "items_path": endpoint.items_path,
                }
                for endpoint in sorted(
                    supplier_api.endpoints,
                    key=lambda ep: (ep.name or "").lower(),
                )
            ]

            mappings_sorted = sorted(
                supplier_api.mappings,
                key=lambda mapping: (
                    0 if mapping.is_active else 1,
                    -(mapping.version or 0),
                    -mapping.id,
                ),
            )
            active_mapping = mappings_sorted[0] if mappings_sorted else None

            mapping_payload = None
            if active_mapping:
                mapping_payload = {
                    "id": active_mapping.id,
                    "version": active_mapping.version,
                    "is_active": active_mapping.is_active,
                    "fields": [
                        {
                            "id": field.id,
                            "target_field": field.target_field,
                            "source_path": field.source_path,
                            "transform": field.transform,
                        }
                        for field in sorted(
                            active_mapping.fields,
                            key=lambda f: (f.target_field or "").lower(),
                        )
                    ],
                }

            supplier_payload["apis"].append(
                {
                    "id": supplier_api.id,
                    "base_url": supplier_api.base_url,
                    "auth_type": supplier_api.auth_type.value
                    if supplier_api.auth_type
                    else None,
                    "rate_limit_per_min": supplier_api.rate_limit_per_min,
                    "endpoints": endpoints,
                    "mapping": mapping_payload,
                }
            )

        result.append(supplier_payload)

    return jsonify(result)


@bp.route("/import_history", methods=["GET"])
@token_required("admin")
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
@token_required("admin")
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


@bp.route("/supplier_api/<int:supplier_id>", methods=["POST"])
@token_required("admin")
def fetch_supplier_api(supplier_id: int):
    """Fetch live supplier data and store it into the temporary table."""

    supplier = Supplier.query.get(supplier_id)
    if not supplier:
        return jsonify({"error": "Fournisseur introuvable"}), 404

    body = request.get_json(silent=True) or {}

    endpoint_id = body.get("endpoint_id")
    if isinstance(endpoint_id, str):
        endpoint_id = int(endpoint_id) if endpoint_id.isdigit() else None
    elif not isinstance(endpoint_id, int):
        endpoint_id = None

    endpoint_name = body.get("endpoint_name")
    if not isinstance(endpoint_name, str):
        endpoint_name = None

    mapping_version_id = body.get("mapping_version_id")
    if isinstance(mapping_version_id, str):
        mapping_version_id = (
            int(mapping_version_id) if mapping_version_id.isdigit() else None
        )
    elif not isinstance(mapping_version_id, int):
        mapping_version_id = None

    endpoint = _select_endpoint(
        supplier_id,
        endpoint_id,
        endpoint_name,
    )
    if not endpoint:
        return (
            jsonify(
                {
                    "error": "Endpoint API introuvable. Précisez endpoint_id ou endpoint_name."
                }
            ),
            400,
        )

    mapping = _select_mapping(endpoint, mapping_version_id)
    if not mapping:
        return (
            jsonify({"error": "Aucun mapping actif trouvé pour cet endpoint"}),
            400,
        )

    job = ApiFetchJob(
        supplier_api_id=endpoint.supplier_api_id,
        endpoint_id=endpoint.id,
        status="running",
    )
    db.session.add(job)
    db.session.commit()

    query_overrides = (
        body.get("query_params") if isinstance(body.get("query_params"), dict) else None
    )
    body_overrides = body.get("body") if isinstance(body.get("body"), dict) else None

    try:
        result = run_fetch_job(
            job_id=job.id,
            supplier_id=supplier_id,
            endpoint_id=endpoint.id,
            mapping_id=mapping.id,
            query_overrides=query_overrides,
            body_overrides=body_overrides,
        )
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify(result), 200


@bp.route("/import_preview", methods=["POST"])
@token_required("admin")
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
            normalized_name = (m.column_name or "").lower()
            df[normalized_name] = df.iloc[:, idx]
            if normalized_name in {"quantity", "selling_price"}:
                df[normalized_name] = pd.to_numeric(
                    df[normalized_name], errors="coerce"
                )

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
        try:
            quantity_value = int(float(quantity))
            selling_price_value = float(selling_price)
        except (TypeError, ValueError):
            continue
        preview_rows.append(
            {
                "description": row.get("description"),
                "model": row.get("model") or row.get("description"),
                "quantity": quantity_value,
                "selling_price": selling_price_value,
            }
        )
        if len(preview_rows) >= 5:
            break

    return jsonify({"preview": preview_rows})


@bp.route("/import", methods=["POST"])
@token_required("admin")
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
    def find_mapping(target: str):
        return next(
            (
                m
                for m in mappings
                if m.column_name
                and _normalize_column_key(m.column_name) == target
            ),
            None,
        )

    quantity_mapping = find_mapping("quantity")
    selling_price_mapping = find_mapping("sellingprice")
    description_mapping = find_mapping("description")
    model_mapping = find_mapping("model")
    ean_mapping = find_mapping("ean")
    part_number_mapping = find_mapping("partnumber")

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
            normalized_name = (m.column_name or "").lower()
            df[normalized_name] = df.iloc[:, idx]
            if normalized_name in {"quantity", "selling_price"}:
                df[normalized_name] = pd.to_numeric(
                    df[normalized_name], errors="coerce"
                )

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
    existing_eans: set[tuple[str, int]] = set()

    for idx, row in df.iterrows():
        # Get quantity and selling_price using their mappings
        quantity_col = quantity_mapping.column_name.lower()
        selling_price_col = selling_price_mapping.column_name.lower()
        description_col = description_mapping.column_name.lower()
        model_col = model_mapping.column_name.lower() if model_mapping else None
        ean_col = ean_mapping.column_name.lower() if ean_mapping else None
        part_number_col = (
            part_number_mapping.column_name.lower()
            if part_number_mapping
            else None
        )
        quantity = row.get(quantity_col)
        selling_price = row.get(selling_price_col)

        if pd.isna(quantity) or pd.isna(selling_price):
            invalid_rows += 1
            log_entries.append(
                f"{idx + 2}\t{row.get(description_col, '')}\tinvalid quantity or selling_price-{row.get(quantity_col, '')}-{row.get(selling_price_col, '')}"
            )
            continue

        try:
            quantity_int = int(float(quantity))
            selling_price_float = float(selling_price)
        except (TypeError, ValueError):
            invalid_rows += 1
            log_entries.append(
                f"{idx + 2}\t{row.get(description_col, '')}\tunable to convert quantity/selling_price-{row.get(quantity_col, '')}-{row.get(selling_price_col, '')}"
            )
            continue

        # Get description and model using their mappings
        description = row.get(description_col)
        model = row.get(model_col) if model_col else description
        ean_value = _clean_cell(row.get(ean_col)) if ean_col else None
        part_number_value = (
            _clean_cell(row.get(part_number_col)) if part_number_col else None
        )

        if ean_value and supplier_id:
            key = (ean_value, supplier_id)
            if key in existing_eans:
                invalid_rows += 1
                log_entries.append(
                    f"{idx + 2}\t{row.get(description_col, '')}\tduplicate ean {ean_value}"
                )
                continue
            existing_eans.add(key)

        count_new += 1

        temp = TemporaryImport(
            description=description,
            model=model,
            quantity=quantity_int,
            selling_price=selling_price_float,
            supplier_id=supplier_id,
            ean=ean_value,
            part_number=part_number_value,
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
@token_required("admin")
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
