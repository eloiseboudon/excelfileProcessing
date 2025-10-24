from datetime import datetime
from typing import Any

from flask import Blueprint, jsonify, request
from models import (
    ApiEndpoint,
    ApiFetchJob,
    AuthType,
    FieldMap,
    ImportHistory,
    MappingVersion,
    Supplier,
    SupplierAPI,
    db,
)
from sqlalchemy import extract, func
from sqlalchemy.orm import joinedload
from utils.auth import token_required
from utils.etl import run_fetch_job


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

bp = Blueprint("imports", __name__)


def _serialize_field(field: FieldMap) -> dict[str, Any]:
    return {
        "id": field.id,
        "target_field": field.target_field,
        "source_path": field.source_path,
        "transform": field.transform,
    }


def _serialize_mapping(
    mapping: MappingVersion | None, *, include_fields: bool = True
) -> dict[str, Any] | None:
    if not mapping:
        return None

    fields = list(mapping.fields or [])

    data: dict[str, Any] = {
        "id": mapping.id,
        "version": mapping.version,
        "is_active": mapping.is_active,
        "field_count": len(fields),
    }

    if include_fields:
        data["fields"] = [
            _serialize_field(field)
            for field in sorted(
                fields,
                key=lambda f: (f.target_field or "").lower(),
            )
        ]

    return data


def _serialize_endpoint(endpoint: ApiEndpoint) -> dict[str, Any]:
    return {
        "id": endpoint.id,
        "name": endpoint.name,
        "method": endpoint.method,
        "path": endpoint.path,
        "items_path": endpoint.items_path,
    }


def _serialize_supplier_api(api: SupplierAPI) -> dict[str, Any]:
    return {
        "id": api.id,
        "base_url": api.base_url,
        "auth_type": api.auth_type.value if api.auth_type else None,
        "rate_limit_per_min": api.rate_limit_per_min,
        "endpoints": [
            _serialize_endpoint(endpoint)
            for endpoint in sorted(
                api.endpoints,
                key=lambda ep: (ep.name or "").lower(),
            )
        ],
        "mapping": _serialize_mapping(
            next(
                (
                    mapping
                    for mapping in sorted(
                        api.mappings,
                        key=lambda mapping: (
                            0 if mapping.is_active else 1,
                            -(mapping.version or 0),
                            -mapping.id,
                        ),
                    )
                ),
                None,
            )
        ),
    }


@bp.route("/supplier_api/config", methods=["GET"])
@token_required("admin")
def list_supplier_api_config():
    """List the API configuration for each supplier.

    ---
    tags:
      - Imports
    responses:
      200:
        description: Supplier API configuration grouped by supplier
    """

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
            "apis": [
                _serialize_supplier_api(api)
                for api in sorted(supplier.apis, key=lambda api: api.id or 0)
            ],
        }

        result.append(supplier_payload)

    return jsonify(result)


def _parse_auth_type(raw_value: str | None) -> AuthType:
    if not raw_value:
        return AuthType.NONE

    try:
        normalized = raw_value.strip().lower()
        return AuthType(normalized)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError("Type d'authentification invalide.") from exc


@bp.route("/supplier_api/<int:supplier_id>/apis", methods=["POST"])
@token_required("admin")
def create_supplier_api(supplier_id: int):
    """Create a new supplier API configuration.

    ---
    tags:
      - Imports
    parameters:
      - in: path
        name: supplier_id
        type: integer
        required: true
      - in: body
        name: payload
        schema:
          type: object
          required:
            - base_url
          properties:
            base_url:
              type: string
            auth_type:
              type: string
            rate_limit_per_min:
              type: integer
            auth_config:
              type: object
            default_headers:
              type: object
    responses:
      201:
        description: Newly created API configuration
      400:
        description: Validation error for the provided payload
    """
    supplier = Supplier.query.get_or_404(supplier_id)
    payload = request.get_json(silent=True) or {}

    base_url = (payload.get("base_url") or "").strip()
    if not base_url:
        return jsonify({"error": "La base URL est obligatoire."}), 400

    try:
        auth_type = _parse_auth_type(payload.get("auth_type"))
    except ValueError as err:
        return jsonify({"error": str(err)}), 400

    api = SupplierAPI(
        supplier=supplier,
        base_url=base_url,
        auth_type=auth_type,
        rate_limit_per_min=payload.get("rate_limit_per_min"),
        auth_config=payload.get("auth_config"),
        default_headers=payload.get("default_headers"),
    )
    db.session.add(api)
    db.session.commit()

    return jsonify(_serialize_supplier_api(api)), 201


@bp.route("/supplier_api/apis/<int:api_id>", methods=["PUT", "PATCH"])
@token_required("admin")
def update_supplier_api(api_id: int):
    """Update an existing supplier API configuration.

    ---
    tags:
      - Imports
    parameters:
      - in: path
        name: api_id
        type: integer
        required: true
      - in: body
        name: payload
        schema:
          type: object
          properties:
            base_url:
              type: string
            auth_type:
              type: string
            rate_limit_per_min:
              type: integer
            auth_config:
              type: object
            default_headers:
              type: object
    responses:
      200:
        description: Updated API configuration
      400:
        description: Invalid data provided for the update
    """
    api = SupplierAPI.query.get_or_404(api_id)
    payload = request.get_json(silent=True) or {}

    if "base_url" in payload:
        base_url = (payload.get("base_url") or "").strip()
        if not base_url:
            return jsonify({"error": "La base URL est obligatoire."}), 400
        api.base_url = base_url

    if "auth_type" in payload:
        try:
            api.auth_type = _parse_auth_type(payload.get("auth_type"))
        except ValueError as err:
            return jsonify({"error": str(err)}), 400

    if "rate_limit_per_min" in payload:
        rate_limit = payload.get("rate_limit_per_min")
        api.rate_limit_per_min = rate_limit if rate_limit is not None else None

    if "auth_config" in payload:
        api.auth_config = payload.get("auth_config")

    if "default_headers" in payload:
        api.default_headers = payload.get("default_headers")

    db.session.commit()
    db.session.refresh(api)

    return jsonify(_serialize_supplier_api(api))


@bp.route("/supplier_api/apis/<int:api_id>", methods=["DELETE"])
@token_required("admin")
def delete_supplier_api(api_id: int):
    """Delete a supplier API configuration.

    ---
    tags:
      - Imports
    parameters:
      - in: path
        name: api_id
        type: integer
        required: true
    responses:
      204:
        description: API configuration successfully deleted
      400:
        description: API cannot be deleted because of existing dependencies
    """
    api = SupplierAPI.query.get_or_404(api_id)

    if ApiFetchJob.query.filter_by(supplier_api_id=api_id).first():
        return (
            jsonify(
                {
                    "error": "Impossible de supprimer une API liée à des synchronisations existantes.",
                }
            ),
            400,
        )

    for endpoint in list(api.endpoints):
        db.session.delete(endpoint)

    for mapping in list(api.mappings):
        for field in list(mapping.fields):
            db.session.delete(field)
        db.session.delete(mapping)

    db.session.delete(api)
    db.session.commit()

    return ("", 204)


@bp.route("/supplier_api/apis/<int:api_id>/endpoints", methods=["POST"])
@token_required("admin")
def create_supplier_api_endpoint(api_id: int):
    """Create an API endpoint definition for a supplier.

    ---
    tags:
      - Imports
    parameters:
      - in: path
        name: api_id
        type: integer
        required: true
      - in: body
        name: payload
        schema:
          type: object
          required:
            - name
            - path
          properties:
            name:
              type: string
            path:
              type: string
            method:
              type: string
            items_path:
              type: string
    responses:
      201:
        description: Newly created endpoint
      400:
        description: Validation error for the endpoint payload
    """
    api = SupplierAPI.query.get_or_404(api_id)
    payload = request.get_json(silent=True) or {}

    name = (payload.get("name") or "").strip()
    path = (payload.get("path") or "").strip()
    method = (payload.get("method") or "GET").strip().upper() or "GET"

    if not name or not path:
        return jsonify({"error": "Le nom et le chemin sont obligatoires."}), 400

    endpoint = ApiEndpoint(
        supplier_api=api,
        name=name,
        path=path,
        method=method,
        items_path=(payload.get("items_path") or None),
    )
    db.session.add(endpoint)
    db.session.commit()

    return jsonify(_serialize_endpoint(endpoint)), 201


@bp.route("/supplier_api/endpoints/<int:endpoint_id>", methods=["PUT", "PATCH"])
@token_required("admin")
def update_supplier_api_endpoint(endpoint_id: int):
    """Update a supplier API endpoint definition.

    ---
    tags:
      - Imports
    parameters:
      - in: path
        name: endpoint_id
        type: integer
        required: true
      - in: body
        name: payload
        schema:
          type: object
          properties:
            name:
              type: string
            path:
              type: string
            method:
              type: string
            items_path:
              type: string
    responses:
      200:
        description: Updated endpoint definition
      400:
        description: Validation error for the endpoint payload
    """
    endpoint = ApiEndpoint.query.get_or_404(endpoint_id)
    payload = request.get_json(silent=True) or {}

    if "name" in payload:
        name = (payload.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Le nom est obligatoire."}), 400
        endpoint.name = name

    if "path" in payload:
        path = (payload.get("path") or "").strip()
        if not path:
            return jsonify({"error": "Le chemin est obligatoire."}), 400
        endpoint.path = path

    if "method" in payload:
        method = (payload.get("method") or "GET").strip().upper()
        endpoint.method = method or "GET"

    if "items_path" in payload:
        items_path = payload.get("items_path")
        endpoint.items_path = items_path or None

    db.session.commit()
    db.session.refresh(endpoint)

    return jsonify(_serialize_endpoint(endpoint))


@bp.route("/supplier_api/endpoints/<int:endpoint_id>", methods=["DELETE"])
@token_required("admin")
def delete_supplier_api_endpoint(endpoint_id: int):
    """Delete an API endpoint definition.

    ---
    tags:
      - Imports
    parameters:
      - in: path
        name: endpoint_id
        type: integer
        required: true
    responses:
      204:
        description: Endpoint successfully deleted
      400:
        description: Endpoint cannot be deleted due to existing dependencies
    """
    endpoint = ApiEndpoint.query.get_or_404(endpoint_id)

    if ApiFetchJob.query.filter_by(endpoint_id=endpoint_id).first():
        return (
            jsonify(
                {
                    "error": "Impossible de supprimer un endpoint associé à des synchronisations existantes.",
                }
            ),
            400,
        )

    db.session.delete(endpoint)
    db.session.commit()

    return ("", 204)


@bp.route("/supplier_api/apis/<int:api_id>/mapping", methods=["POST"])
@token_required("admin")
def create_supplier_api_mapping(api_id: int):
    """Create a mapping version for a supplier API.

    ---
    tags:
      - Imports
    parameters:
      - in: path
        name: api_id
        type: integer
        required: true
      - in: body
        name: payload
        schema:
          type: object
          properties:
            version:
              type: integer
            is_active:
              type: boolean
            fields:
              type: array
              items:
                type: object
                properties:
                  target_field:
                    type: string
                  source_path:
                    type: string
                  transform:
                    type: string
    responses:
      201:
        description: Mapping definition created
      400:
        description: Invalid mapping payload
    """
    SupplierAPI.query.get_or_404(api_id)
    payload = request.get_json(silent=True) or {}

    is_active = payload.get("is_active", True)
    version = payload.get("version")
    if version is None:
        current_max = (
            db.session.query(func.max(MappingVersion.version))
            .filter(MappingVersion.supplier_api_id == api_id)
            .scalar()
        )
        version = (current_max or 0) + 1

    if is_active:
        MappingVersion.query.filter_by(
            supplier_api_id=api_id, is_active=True
        ).update({"is_active": False}, synchronize_session=False)

    mapping = MappingVersion(
        supplier_api_id=api_id,
        version=version,
        is_active=is_active,
    )
    db.session.add(mapping)
    db.session.flush()

    fields_payload = payload.get("fields") or []
    for field_payload in fields_payload:
        target_field = (field_payload.get("target_field") or "").strip()
        source_path = (field_payload.get("source_path") or "").strip()
        if not target_field or not source_path:
            continue
        field = FieldMap(
            mapping_version=mapping,
            target_field=target_field,
            source_path=source_path,
            transform=field_payload.get("transform"),
        )
        db.session.add(field)

    db.session.commit()

    db.session.refresh(mapping)
    return jsonify(_serialize_mapping(mapping)), 201


@bp.route(
    "/supplier_api/mappings/<int:mapping_id>/fields",
    methods=["POST"],
)
@token_required("admin")
def create_supplier_api_field(mapping_id: int):
    """Add a mapped field to a mapping version.

    ---
    tags:
      - Imports
    parameters:
      - in: path
        name: mapping_id
        type: integer
        required: true
      - in: body
        name: payload
        schema:
          type: object
          required:
            - target_field
            - source_path
          properties:
            target_field:
              type: string
            source_path:
              type: string
            transform:
              type: string
    responses:
      201:
        description: Newly created mapping field
      400:
        description: Missing field details
    """
    mapping = MappingVersion.query.get_or_404(mapping_id)
    payload = request.get_json(silent=True) or {}

    target_field = (payload.get("target_field") or "").strip()
    source_path = (payload.get("source_path") or "").strip()

    if not target_field or not source_path:
        return (
            jsonify({"error": "Les champs cible et source sont obligatoires."}),
            400,
        )

    field = FieldMap(
        mapping_version=mapping,
        target_field=target_field,
        source_path=source_path,
        transform=payload.get("transform"),
    )
    db.session.add(field)
    db.session.commit()
    db.session.refresh(field)

    return jsonify(_serialize_field(field)), 201


@bp.route("/supplier_api/fields/<int:field_id>", methods=["PUT", "PATCH"])
@token_required("admin")
def update_supplier_api_field(field_id: int):
    """Update a mapped field definition.

    ---
    tags:
      - Imports
    parameters:
      - in: path
        name: field_id
        type: integer
        required: true
      - in: body
        name: payload
        schema:
          type: object
          properties:
            target_field:
              type: string
            source_path:
              type: string
            transform:
              type: string
    responses:
      200:
        description: Updated mapping field
      400:
        description: Invalid field update payload
    """
    field = FieldMap.query.get_or_404(field_id)
    payload = request.get_json(silent=True) or {}

    if "target_field" in payload:
        target_field = (payload.get("target_field") or "").strip()
        if not target_field:
            return jsonify({"error": "Le champ cible est obligatoire."}), 400
        field.target_field = target_field

    if "source_path" in payload:
        source_path = (payload.get("source_path") or "").strip()
        if not source_path:
            return jsonify({"error": "Le champ source est obligatoire."}), 400
        field.source_path = source_path

    if "transform" in payload:
        field.transform = payload.get("transform")

    db.session.commit()
    db.session.refresh(field)

    return jsonify(_serialize_field(field))


@bp.route("/supplier_api/fields/<int:field_id>", methods=["DELETE"])
@token_required("admin")
def delete_supplier_api_field(field_id: int):
    """Delete a mapped field definition.

    ---
    tags:
      - Imports
    parameters:
      - in: path
        name: field_id
        type: integer
        required: true
    responses:
      204:
        description: Field successfully deleted
    """
    field = FieldMap.query.get_or_404(field_id)
    db.session.delete(field)
    db.session.commit()
    return ("", 204)


@bp.route("/supplier_api/reports", methods=["GET"])
@token_required("admin")
def list_supplier_api_reports():
    """List recent supplier API synchronization reports.

    ---
    tags:
      - Imports
    parameters:
      - in: query
        name: limit
        type: integer
        required: false
        description: Maximum number of reports to return
    responses:
      200:
        description: Synchronization reports with metadata and mapping details
    """

    try:
        limit = int(request.args.get("limit", 20))
    except (TypeError, ValueError):
        limit = 20

    limit = max(1, min(limit, 100))

    jobs = (
        ApiFetchJob.query.options(
            joinedload(ApiFetchJob.supplier_api).joinedload(SupplierAPI.supplier),
            joinedload(ApiFetchJob.mapping_version).joinedload(MappingVersion.fields),
        )
        .filter(ApiFetchJob.status == "success")
        .order_by(ApiFetchJob.started_at.desc())
        .limit(limit)
        .all()
    )

    reports = []
    for job in jobs:
        supplier = job.supplier_api.supplier if job.supplier_api else None
        reports.append(
            {
                "job_id": job.id,
                "supplier_id": supplier.id if supplier else None,
                "supplier": supplier.name if supplier else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
                "updated_products": job.report_updated_products or [],
                "database_missing_products": job.report_database_missing_products
                or [],
                "api_missing_products": job.report_api_missing_products or [],
                "api_raw_items": job.report_api_raw_items or [],
                "mapping": _serialize_mapping(
                    job.mapping_version, include_fields=False
                ),
            }
        )

    return jsonify(reports)


@bp.route("/verify_import/<int:supplier_id>", methods=["GET"])
@token_required("admin")
def verify_import(supplier_id):
    """Check whether the current week already has an import for a supplier.

    ---
    tags:
      - Imports
    parameters:
      - in: path
        name: supplier_id
        type: integer
        required: true
    responses:
      200:
        description: Status indicating whether an import already exists this week
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
    """Trigger a supplier API fetch and store the result.

    ---
    tags:
      - Imports
    parameters:
      - in: path
        name: supplier_id
        type: integer
        required: true
      - in: body
        name: payload
        schema:
          type: object
          properties:
            endpoint_id:
              type: integer
            endpoint_name:
              type: string
            mapping_version_id:
              type: integer
            query_params:
              type: object
            body:
              type: object
    responses:
      200:
        description: Result of the fetch operation
      400:
        description: Endpoint or mapping selection error
      502:
        description: Upstream supplier API error
    """

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
        mapping_version_id=mapping.id,
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
