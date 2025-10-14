from __future__ import annotations

import re
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin

import jmespath
import requests
from dateutil import parser as date_parser
from flask import current_app
from requests.auth import HTTPBasicAuth
from sqlalchemy.orm import joinedload

from models import (
    ApiEndpoint,
    ApiFetchJob,
    AuthType,
    MappingVersion,
    ParsedItem,
    Product,
    ProductCalculation,
    RawIngest,
    Supplier,
    SupplierProductRef,
    TemporaryImport,
    db,
)


_EXPRESSION_CACHE: Dict[str, jmespath.parser.ParsedResult] = {}
_MAX_REPORT_ITEMS = 200
_MAX_RAW_SAMPLE_ITEMS = 25

_FIELD_ALIAS_MAP = {
    "supplier_ski": "supplier_sku",
    "suppliersku": "supplier_sku",
    "sku": "supplier_sku",
}

_FIELD_PRIORITY = {
    "supplier_sku": 0,
    "ean": 1,
    "part_number": 2,
}


def _compile_expression(path: str) -> jmespath.parser.ParsedResult:
    expression = _EXPRESSION_CACHE.get(path)
    if expression is None:
        expression = jmespath.compile(path)
        _EXPRESSION_CACHE[path] = expression
    return expression


def _normalize_source_path(path: str) -> str:
    cleaned = (path or "").strip()
    if not cleaned or cleaned == "$":
        return "@"
    if cleaned.startswith("$."):
        cleaned = cleaned[2:]
    elif cleaned.startswith("$"):
        cleaned = cleaned[1:]
    return cleaned or "@"


def _normalize_target_field(name: Optional[str]) -> str:
    if not name:
        return ""
    normalized = re.sub(r"\s+", "_", name.strip().lower())
    return _FIELD_ALIAS_MAP.get(normalized, normalized)


def _search_path(obj: Any, path: str) -> Any:
    normalized = _normalize_source_path(path)
    if normalized == "@":
        return obj
    expression = _compile_expression(normalized)
    return expression.search(obj)


def _ensure_json_compatible(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return str(value)

    if isinstance(value, dict):
        result = {}
        for idx, (key, item) in enumerate(value.items()):
            if idx >= _MAX_RAW_SAMPLE_ITEMS:
                break
            result[str(key)] = _ensure_json_compatible(item, depth + 1)
        return result
    if isinstance(value, list):
        return [
            _ensure_json_compatible(item, depth + 1)
            for item in value[:_MAX_RAW_SAMPLE_ITEMS]
        ]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _prepare_api_raw_samples(items: Any) -> List[Any]:
    if isinstance(items, list):
        sample_source = items[:_MAX_RAW_SAMPLE_ITEMS]
    elif items is None:
        sample_source = []
    else:
        sample_source = [items]

    return [_ensure_json_compatible(entry) for entry in sample_source]


def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    try:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            value = value.replace(" ", "")
            if value.count(",") == 1 and value.count(".") == 0:
                value = value.replace(",", ".")
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(int(value))
    try:
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return None
            cleaned = cleaned.replace(" ", "")
            if cleaned.count(",") == 1 and cleaned.count(".") == 0:
                cleaned = cleaned.replace(",", ".")
            value = cleaned
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_first_int(*values: Any) -> Optional[int]:
    for value in values:
        result = _coerce_int(value)
        if result is not None:
            return result
    return None


def _coerce_first_float(*values: Any) -> Optional[float]:
    for value in values:
        result = _coerce_float(value)
        if result is not None:
            return result
    return None


def _stringify(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return str(value)


def _first_non_empty(*values: Any) -> Optional[str]:
    for value in values:
        text = _stringify(value)
        if text:
            return text
    return None


def _extract_supplier_sku(record: Dict[str, Any]) -> Optional[str]:
    return _first_non_empty(
        record.get("supplier_sku"),
        record.get("sku"),
        record.get("reference"),
        record.get("ref"),
        record.get("item_code"),
        record.get("product_code"),
        record.get("code"),
        record.get("vpn"),
        record.get("vpnr"),
    )


def _extract_ean(record: Dict[str, Any]) -> Optional[str]:
    return _first_non_empty(
        record.get("ean"),
        record.get("ean13"),
        record.get("ean_13"),
        record.get("barcode"),
        record.get("gtin"),
    )


def _extract_part_number(record: Dict[str, Any]) -> Optional[str]:
    return _first_non_empty(
        record.get("part_number"),
        record.get("partNumber"),
        record.get("pn"),
        record.get("mpn"),
        record.get("manufacturer_part_number"),
        record.get("product_number"),
        record.get("item_number"),
        record.get("vpn"),
        record.get("vpnr"),
    )


def _extract_description(record: Dict[str, Any]) -> Optional[str]:
    return _first_non_empty(
        record.get("description"),
        record.get("name"),
        record.get("title"),
        record.get("designation"),
        record.get("product_name"),
    )


def _extract_model(record: Dict[str, Any], description: Optional[str]) -> Optional[str]:
    return _first_non_empty(
        record.get("model"),
        record.get("model_name"),
        record.get("product_model"),
        record.get("reference"),
        description,
    )


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value))
        except (ValueError, OSError, OverflowError):
            return None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            return date_parser.parse(cleaned)
        except (ValueError, TypeError):
            return None
    return None


def _apply_transforms(value: Any, transform: Optional[Dict[str, Any]]) -> Any:
    if not transform or not isinstance(transform, dict):
        return value

    if transform.get("strip") and isinstance(value, str):
        value = value.strip()
    if transform.get("lower") and isinstance(value, str):
        value = value.lower()
    if transform.get("upper") and isinstance(value, str):
        value = value.upper()

    regex_replace = transform.get("regex_replace")
    if regex_replace and isinstance(value, str):
        for pattern, repl in regex_replace:
            value = re.sub(pattern, repl, value)

    if transform.get("decimal_normalize") and isinstance(value, str):
        value = value.replace(" ", "").replace(",", ".")

    cast_type = transform.get("cast")
    if cast_type == "int":
        value = _coerce_int(value)
    elif cast_type == "float":
        value = _coerce_float(value)
    elif cast_type == "str":
        value = _stringify(value)

    if transform.get("parse_dt"):
        parsed = _parse_datetime(value)
        if parsed is not None:
            value = parsed

    currency = transform.get("currency")
    if currency and not value:
        value = currency

    return value


def _extract_items(payload: Any, items_path: Optional[str]) -> List[dict[str, Any]]:
    data: Any = payload
    if items_path:
        result = _search_path(payload, items_path)
        if result is not None:
            data = result

    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _prepare_field_maps(mapping: MappingVersion) -> List[FieldMap]:
    fields = list(mapping.fields or [])
    fields.sort(
        key=lambda field: (
            _FIELD_PRIORITY.get(_normalize_target_field(field.target_field), 10),
            field.id or 0,
        )
    )
    return fields


def _perform_request(
    supplier_api, endpoint: ApiEndpoint, query: Dict[str, Any], body: Dict[str, Any]
) -> requests.Response:
    base_url = supplier_api.base_url.rstrip("/") + "/"
    url = urljoin(base_url, endpoint.path.lstrip("/"))

    headers = dict(supplier_api.default_headers or {})
    auth = None

    if supplier_api.auth_type == AuthType.API_KEY:
        config = supplier_api.auth_config or {}
        header_name = config.get("header")
        header_value = config.get("value")
        if header_name and header_value:
            headers[header_name] = header_value
    elif supplier_api.auth_type == AuthType.BASIC:
        config = supplier_api.auth_config or {}
        username = config.get("username")
        password = config.get("password")
        if username and password:
            auth = HTTPBasicAuth(username, password)
    elif supplier_api.auth_type == AuthType.OAUTH2:
        raise RuntimeError("L'authentification OAuth2 n'est pas encore prise en charge")

    method = (endpoint.method or "GET").upper()
    timeout = 30

    request_kwargs: Dict[str, Any] = {
        "headers": headers,
        "params": query,
        "timeout": timeout,
        "auth": auth,
    }

    if method in {"POST", "PUT", "PATCH"}:
        if (endpoint.content_type or "").lower() == "application/json":
            request_kwargs["json"] = body or None
        else:
            request_kwargs["data"] = body or None

    response = requests.request(method, url, **request_kwargs)
    response.raise_for_status()
    return response


_PRICE_THRESHOLDS = [15, 29, 49, 79, 99, 129, 149, 179, 209, 299, 499, 799, 999]
_PRICE_MULTIPLIERS = [
    1.25,
    1.22,
    1.20,
    1.18,
    1.15,
    1.11,
    1.10,
    1.09,
    1.09,
    1.08,
    1.08,
    1.07,
    1.07,
    1.06,
]


def _compute_margin_prices(price: float, tcp: float) -> tuple[float, float, float, float, float]:
    margin45 = price * 0.045
    price_with_tcp = price + tcp + margin45

    price_with_margin = price
    for threshold, multiplier in zip(_PRICE_THRESHOLDS, _PRICE_MULTIPLIERS):
        if price <= threshold:
            price_with_margin = price * multiplier
            break
    else:
        price_with_margin = price * _PRICE_MULTIPLIERS[-1]

    if price > _PRICE_THRESHOLDS[-1]:
        price_with_margin = price * _PRICE_MULTIPLIERS[-1]

    max_price = math.ceil(max(price_with_tcp, price_with_margin))
    marge = max_price - tcp - price
    return (
        round(margin45, 2),
        round(price_with_tcp, 2),
        round(price_with_margin, 2),
        max_price,
        round(marge, 2),
    )


def _prepare_temp_row(record: Dict[str, Any]) -> Dict[str, Any]:
    quantity = _coerce_first_int(
        record.get("quantity"),
        record.get("qty"),
        record.get("stock"),
        record.get("stock_quantity"),
        record.get("available"),
        record.get("availability"),
        record.get("quantity_available"),
    ) or 0

    purchase_price = _coerce_first_float(
        record.get("purchase_price"),
        record.get("buy_price"),
        record.get("net_price"),
        record.get("cost"),
        record.get("purchaseprice"),
    )
    base_price = _coerce_first_float(
        record.get("price"),
        record.get("selling_price"),
        record.get("sale_price"),
        record.get("unit_price"),
        record.get("gross_price"),
        record.get("final_price"),
    )
    recommended = _coerce_first_float(
        record.get("recommended_price"),
        record.get("msrp"),
        record.get("rrp"),
    )

    price = base_price
    if price is None:
        price = purchase_price
    if price is None:
        price = recommended
    if price is None:
        price = 0.0

    description = _extract_description(record)
    model = _extract_model(record, description)

    return {
        "description": description,
        "model": model,
        "quantity": quantity,
        "selling_price": price,
        "ean": _extract_ean(record),
        "part_number": _extract_part_number(record),
        "supplier_sku": _extract_supplier_sku(record),
    }


def _update_product_prices_from_records(
    supplier_id: int, records: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    if not records:
        return {
            "updated_products": [],
            "database_missing_products": [],
            "api_missing_products": [],
        }

    references = SupplierProductRef.query.filter_by(supplier_id=supplier_id).all()
    by_sku = {
        (ref.supplier_sku or "").strip(): ref
        for ref in references
        if ref.supplier_sku
    }
    by_ean = {(ref.ean or "").strip(): ref for ref in references if ref.ean}
    by_part = {
        (ref.part_number or "").strip(): ref
        for ref in references
        if ref.part_number
    }

    price_updates: dict[int, float] = {}
    matched_reference_ids: Set[int] = set()
    updated_products_map: Dict[int, Dict[str, Any]] = {}
    database_missing_entries: List[Dict[str, Any]] = []
    api_missing_entries: List[Dict[str, Any]] = []
    unmatched_keys: Set[tuple] = set()
    product_ids_to_fetch: Set[int] = set()
    now = datetime.utcnow()

    for record in records:
        product_id = _coerce_int(record.get("product_id"))
        ean = _extract_ean(record)
        part_number = _extract_part_number(record)
        supplier_sku = _extract_supplier_sku(record)

        matched_ref = None

        if not product_id:
            if supplier_sku and supplier_sku in by_sku:
                matched_ref = by_sku[supplier_sku]
            elif ean and ean in by_ean:
                matched_ref = by_ean[ean]
            elif part_number and part_number in by_part:
                matched_ref = by_part[part_number]

            if matched_ref and matched_ref.product_id:
                product_id = matched_ref.product_id
        elif supplier_sku and supplier_sku in by_sku:
            matched_ref = by_sku[supplier_sku]

        if matched_ref:
            matched_reference_ids.add(matched_ref.id)
            matched_ref.last_seen_at = now
            db.session.add(matched_ref)

        price = _coerce_first_float(
            record.get("price"),
            record.get("selling_price"),
            record.get("purchase_price"),
            record.get("recommended_price"),
            record.get("sale_price"),
            record.get("net_price"),
            record.get("cost"),
        )

        if product_id and price is not None and price >= 0:
            price_updates[product_id] = price
            product_ids_to_fetch.add(product_id)
            updated_products_map[product_id] = {
                "product_id": product_id,
                "ean": ean or (matched_ref.ean if matched_ref else None),
                "part_number": part_number
                or (matched_ref.part_number if matched_ref else None),
                "supplier_sku": supplier_sku
                or (matched_ref.supplier_sku if matched_ref else None),
                "price": round(price, 2),
            }
        else:
            key = (
                (supplier_sku or "").strip().lower(),
                (ean or "").strip().lower(),
                (part_number or "").strip().lower(),
            )
            if key not in unmatched_keys and len(api_missing_entries) < _MAX_REPORT_ITEMS:
                unmatched_keys.add(key)
                api_missing_entries.append(
                    {
                        "description": _extract_description(record)
                        or _extract_model(record, None),
                        "ean": ean,
                        "part_number": part_number,
                        "supplier_sku": supplier_sku,
                    }
                )

    for ref in references:
        if ref.product_id and ref.id not in matched_reference_ids:
            product_ids_to_fetch.add(ref.product_id)
            identifiers: List[str] = []
            if ref.supplier_sku:
                identifiers.append(f"SKU fournisseur {ref.supplier_sku}")
            if ref.ean:
                identifiers.append(f"EAN {ref.ean}")
            if ref.part_number:
                identifiers.append(f"Référence {ref.part_number}")
            if identifiers:
                reason = (
                    "Aucune donnée API ne correspond aux identifiants suivants : "
                    + ", ".join(identifiers)
                )
            else:
                reason = (
                    "Aucune donnée API ne correspond à ce produit, et aucun identifiant "
                    "n'est défini pour permettre l'appariement."
                )
            entry = {
                "product_id": ref.product_id,
                "ean": ref.ean,
                "part_number": ref.part_number,
                "supplier_sku": ref.supplier_sku,
                "reason": reason,
            }
            database_missing_entries.append(entry)
            if len(database_missing_entries) >= _MAX_REPORT_ITEMS:
                break

    if product_ids_to_fetch:
        products = (
            Product.query.filter(Product.id.in_(product_ids_to_fetch)).all()
        )
        product_map = {product.id: product for product in products}
    else:
        product_map = {}

    for data in updated_products_map.values():
        product = product_map.get(data["product_id"])
        if product:
            data["product_name"] = (
                product.model
                or product.description
                or product.part_number
                or product.ean
            )

    for entry in database_missing_entries:
        product = product_map.get(entry["product_id"])
        if product:
            entry["product_name"] = (
                product.model
                or product.description
                or product.part_number
                or product.ean
            )

    for product_id, price in price_updates.items():
        product = product_map.get(product_id)
        if not product:
            continue

        tcp = float(product.memory.tcp_value) if product.memory else 0.0
        (
            margin45,
            price_with_tcp,
            price_with_margin,
            max_price,
            marge,
        ) = _compute_margin_prices(price, tcp)

        calc = (
            ProductCalculation.query.filter_by(
                product_id=product_id, supplier_id=supplier_id
            )
            .order_by(ProductCalculation.date.desc())
            .first()
        )

        timestamp = datetime.now(timezone.utc)

        if calc:
            calc.price = round(price, 2)
            calc.tcp = round(tcp, 2)
            calc.marge4_5 = margin45
            calc.prixht_tcp_marge4_5 = price_with_tcp
            calc.prixht_marge4_5 = price_with_margin
            calc.prixht_max = max_price
            calc.marge = marge
            calc.date = timestamp
            db.session.add(calc)
        else:
            calc = ProductCalculation(
                product_id=product_id,
                supplier_id=supplier_id,
                price=round(price, 2),
                tcp=round(tcp, 2),
                marge4_5=margin45,
                prixht_tcp_marge4_5=price_with_tcp,
                prixht_marge4_5=price_with_margin,
                prixht_max=max_price,
                marge=marge,
                date=timestamp,
            )
            db.session.add(calc)

    updated_products = list(updated_products_map.values())

    return {
        "updated_products": updated_products[:_MAX_REPORT_ITEMS],
        "database_missing_products": database_missing_entries,
        "api_missing_products": api_missing_entries,
    }


def run_fetch_job(
    job_id: int,
    supplier_id: int,
    endpoint_id: int,
    mapping_id: int,
    *,
    query_overrides: Optional[Dict[str, Any]] = None,
    body_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    job = ApiFetchJob.query.get(job_id)
    if not job:
        raise RuntimeError("Tâche introuvable")

    endpoint = (
        ApiEndpoint.query.options(joinedload(ApiEndpoint.supplier_api))
        .filter_by(id=endpoint_id)
        .first()
    )
    if not endpoint:
        raise RuntimeError("Endpoint introuvable")

    mapping = (
        MappingVersion.query.options(joinedload(MappingVersion.fields))
        .filter_by(id=mapping_id)
        .first()
    )
    if not mapping:
        raise RuntimeError("Aucun mapping disponible pour cet endpoint")

    if job.mapping_version_id != mapping.id:
        job.mapping_version_id = mapping.id

    supplier = Supplier.query.get(supplier_id)
    if not supplier:
        raise RuntimeError("Fournisseur introuvable")

    final_query = dict(endpoint.query_params or {})
    if query_overrides:
        final_query.update(query_overrides)

    final_body = dict(endpoint.body_template or {})
    if body_overrides:
        final_body.update(body_overrides)

    job.params_used = {"query": final_query, "body": final_body, "path": endpoint.path}
    db.session.add(job)
    db.session.commit()

    try:
        response = _perform_request(endpoint.supplier_api, endpoint, final_query, final_body)
        job.params_used = {
            **(job.params_used or {}),
            "resolved_url": response.url,
            "status_code": response.status_code,
        }
        db.session.add(job)
        content_type = response.headers.get("Content-Type", endpoint.content_type)
        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError("Réponse JSON invalide reçue depuis l'API fournisseur") from exc

        raw_entry = RawIngest(
            job_id=job.id,
            http_status=response.status_code,
            payload=response.content,
            content_type=content_type or "application/json",
            page_index=0,
        )
        db.session.add(raw_entry)

        items = _extract_items(payload, endpoint.items_path)
        raw_samples = _prepare_api_raw_samples(items)
        job.report_api_raw_items = raw_samples
        db.session.add(job)
        if not items:
            raise RuntimeError("Aucune donnée exploitable retournée par l'API fournisseur")

        field_maps = _prepare_field_maps(mapping)
        if not field_maps:
            raise RuntimeError("Aucun mapping de champs n'est défini pour cet endpoint")

        parsed_records: List[Dict[str, Any]] = []
        for item in items:
            record: Dict[str, Any] = {}
            for field in field_maps:
                target_field = _normalize_target_field(field.target_field)
                if not target_field:
                    continue
                value = _search_path(item, field.source_path)
                value = _apply_transforms(value, field.transform)
                record[target_field] = value
            parsed_records.append(record)

        TemporaryImport.query.filter_by(supplier_id=supplier_id).delete(synchronize_session=False)

        seen_keys: Set[Tuple[str, str, str]] = set()
        temp_rows: List[Dict[str, Any]] = []

        for record in parsed_records:
            temp_row = _prepare_temp_row(record)
            supplier_sku = temp_row.get("supplier_sku")
            key = (
                (temp_row.get("ean") or "").strip().lower(),
                (temp_row.get("part_number") or "").strip().lower(),
                (supplier_sku or "").strip().lower(),
            )
            if not any(key):
                fallback = _first_non_empty(
                    temp_row.get("description"),
                    temp_row.get("model"),
                    record.get("name"),
                    record.get("title"),
                    record.get("designation"),
                    supplier_sku,
                ) or f"row-{len(temp_rows)}"
                key = ("", "", fallback.lower())
            if key in seen_keys:
                continue
            seen_keys.add(key)

            temp_rows.append(temp_row)

            parsed_item = ParsedItem(
                job_id=job.id,
                supplier_id=supplier_id,
                ean=temp_row["ean"],
                part_number=temp_row["part_number"],
                supplier_sku=supplier_sku,
                model=temp_row["model"],
                description=temp_row["description"],
                brand=_stringify(record.get("brand")),
                color=_stringify(record.get("color")),
                memory=_stringify(record.get("memory")),
                ram=_stringify(record.get("ram")),
                norme=_stringify(record.get("norme")),
                device_type=_stringify(record.get("device_type")),
                quantity=temp_row["quantity"],
                purchase_price=_coerce_first_float(
                    record.get("purchase_price"),
                    record.get("buy_price"),
                    record.get("net_price"),
                    record.get("cost"),
                    record.get("price"),
                    record.get("selling_price"),
                ),
                currency=_stringify(record.get("currency")),
                recommended_price=_coerce_first_float(
                    record.get("recommended_price"),
                    record.get("msrp"),
                    record.get("rrp"),
                ),
                updated_at=_parse_datetime(record.get("updated_at")),
            )
            db.session.add(parsed_item)

            temp_import = TemporaryImport(
                supplier_id=supplier_id,
                description=temp_row["description"],
                model=temp_row["model"],
                quantity=temp_row["quantity"],
                selling_price=temp_row["selling_price"],
                ean=temp_row["ean"],
                part_number=temp_row["part_number"],
            )
            db.session.add(temp_import)

        report_data = _update_product_prices_from_records(supplier_id, parsed_records)

        job.report_updated_products = report_data.get("updated_products")
        job.report_database_missing_products = report_data.get(
            "database_missing_products"
        )
        job.report_api_missing_products = report_data.get("api_missing_products")
        job.report_api_raw_items = raw_samples

        job.status = "success"
        job.error_message = None
        job.ended_at = datetime.utcnow()
        db.session.add(job)
        db.session.commit()

        preview_rows = temp_rows[:50]

        mapping_summary = {
            "id": mapping.id,
            "version": mapping.version,
            "is_active": mapping.is_active,
            "field_count": len(mapping.fields or []),
        }

        return {
            "job_id": job.id,
            "supplier_id": supplier_id,
            "supplier": supplier.name,
            "status": job.status,
            "parsed_count": len(parsed_records),
            "temporary_import_count": len(temp_rows),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            "items": preview_rows,
            "rows": preview_rows,
            "report": report_data,
            "api_raw_items": raw_samples,
            "mapping": mapping_summary,
        }
    except Exception as exc:  # pragma: no cover - defensive logging
        db.session.rollback()
        message = str(exc)
        current_app.logger.exception("Échec de la synchronisation API fournisseur: %s", exc)
        job = ApiFetchJob.query.get(job_id)
        if job:
            job.status = "failed"
            job.error_message = message
            job.ended_at = datetime.utcnow()
            db.session.add(job)
            db.session.commit()
        raise RuntimeError(message) from exc
