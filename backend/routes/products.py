import logging
import math
import time
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Dict, Set

import pandas as pd
from flask import Blueprint, jsonify, request, send_file, current_app
from models import (
    ApiFetchJob,
    Brand,
    Color,
    ColorTranslation,
    ImportHistory,
    InternalProduct,
    Product,
    ProductCalculation,
    SupplierAPI,
    SupplierCatalog,
    db,
)
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from utils.activity import log_activity
from utils.auth import token_required
from utils.calculations import recalculate_product_calculations
from utils.etl import run_fetch_job, select_best_mapping


def _start_of_day_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _ensure_daily_supplier_cache() -> None:
    """Ensure supplier API data is refreshed once per day."""

    today = _start_of_day_utc()
    supplier_apis = (
        SupplierAPI.query.options(joinedload(SupplierAPI.endpoints))
        .filter(SupplierAPI.endpoints.any())
        .all()
    )

    for api in supplier_apis:
        supplier = api.supplier
        if not supplier:
            continue

        mapping = select_best_mapping(api.id)
        if not mapping:
            continue

        for endpoint in api.endpoints:
            latest_job = (
                ApiFetchJob.query.filter(
                    ApiFetchJob.endpoint_id == endpoint.id,
                    ApiFetchJob.status == "success",
                    ApiFetchJob.started_at >= today,
                )
                .order_by(ApiFetchJob.started_at.desc())
                .first()
            )
            has_temp_data = (
                SupplierCatalog.query.filter(
                    SupplierCatalog.supplier_id == supplier.id
                )
                .limit(1)
                .first()
                is not None
            )

            if latest_job and has_temp_data:
                continue

            job = ApiFetchJob(
                supplier_api_id=api.id,
                endpoint_id=endpoint.id,
                mapping_version_id=mapping.id,
                status="running",
            )
            db.session.add(job)
            db.session.commit()

            current_app.logger.info(
                "Daily supplier sync triggered",  # pragma: no cover - logging
                extra={
                    "supplier_id": supplier.id,
                    "supplier": supplier.name,
                    "endpoint_id": endpoint.id,
                },
            )

            run_fetch_job(
                job_id=job.id,
                supplier_id=supplier.id,
                endpoint_id=endpoint.id,
                mapping_id=mapping.id,
            )

logger = logging.getLogger(__name__)



def _serialize_product_attrs(product) -> dict:
    """Return the 6 standard attribute fields for a product."""
    return {
        "brand": product.brand.brand if product.brand else None,
        "memory": product.memory.memory if product.memory else None,
        "color": product.color.color if product.color else None,
        "type": product.type.type if product.type else None,
        "ram": product.RAM.ram if product.RAM else None,
        "norme": product.norme.norme if product.norme else None,
    }


def _safe_float(value: object, default: float = 0.0) -> float:
    """Return value as float, coercing NaN/Inf to default."""
    if value is None:
        return default
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(f) or math.isinf(f):
        return default
    return f


bp = Blueprint("products", __name__)


@bp.route("/search_catalog", methods=["GET"])
@token_required()
def list_search_catalog():
    """Return daily supplier catalog."""

    try:
        _ensure_daily_supplier_cache()
    except RuntimeError as exc:  # pragma: no cover - defensive
        current_app.logger.exception("Daily supplier sync failed: %s", exc)
        return jsonify({"error": str(exc)}), 502

    color_synonyms: Dict[int, Set[str]] = {}

    for color in Color.query.all():
        if color.color:
            color_synonyms.setdefault(color.id, set()).add(color.color)

    for translation in ColorTranslation.query.all():
        target_id = translation.color_target_id
        synonyms = color_synonyms.setdefault(target_id, set())
        if translation.color_target:
            synonyms.add(translation.color_target)
        if translation.color_source:
            synonyms.add(translation.color_source)

    entries = (
        SupplierCatalog.query.options(
            joinedload(SupplierCatalog.brand),
            joinedload(SupplierCatalog.supplier),
            joinedload(SupplierCatalog.color),
        )
        .filter(SupplierCatalog.supplier_id.isnot(None))
        .order_by(SupplierCatalog.model.asc(), SupplierCatalog.description.asc())
        .all()
    )

    results = []
    for entry in entries:
        name = (
            entry.model
            or entry.description
            or entry.part_number
            or entry.ean
            or f"Produit-{entry.id}"
        )
        price = entry.selling_price if entry.selling_price is not None else None

        color_values = []
        if entry.color_id is not None:
            color_values = sorted(
                {
                    value.strip()
                    for value in color_synonyms.get(entry.color_id, set())
                    if value and value.strip()
                }
            )

        results.append(
            {
                "id": entry.id,
                "name": name,
                "model": entry.model,
                "description": entry.description,
                "brand": entry.brand.brand if entry.brand else None,
                "price": price,
                "quantity": entry.quantity,
                "ean": entry.ean,
                "part_number": entry.part_number,
                "supplier": entry.supplier.name if entry.supplier else None,
                "color_synonyms": color_values,
            }
        )

    return jsonify(results)


@bp.route("/supplier_catalog/refresh", methods=["POST"])
@token_required("admin")
def refresh_supplier_catalog():
    """Force-refresh supplier catalogs by re-fetching all configured APIs."""
    start = time.time()

    supplier_apis = (
        SupplierAPI.query.options(joinedload(SupplierAPI.endpoints))
        .filter(SupplierAPI.endpoints.any())
        .all()
    )

    total_items = 0
    refreshed_suppliers = []

    for api in supplier_apis:
        supplier = api.supplier
        if not supplier:
            continue

        mapping = select_best_mapping(api.id)
        if not mapping:
            continue

        for endpoint in api.endpoints:
            job = ApiFetchJob(
                supplier_api_id=api.id,
                endpoint_id=endpoint.id,
                mapping_version_id=mapping.id,
                status="running",
            )
            db.session.add(job)
            db.session.commit()

            try:
                result = run_fetch_job(
                    job_id=job.id,
                    supplier_id=supplier.id,
                    endpoint_id=endpoint.id,
                    mapping_id=mapping.id,
                )
                total_items += result.get("catalog_count", 0)
                refreshed_suppliers.append(supplier.name)
            except RuntimeError as exc:
                current_app.logger.warning(
                    "Refresh failed for supplier %s: %s", supplier.name, exc
                )

    duration = round(time.time() - start, 2)

    return jsonify({
        "status": "success",
        "refreshed_suppliers": refreshed_suppliers,
        "total_items": total_items,
        "duration_seconds": duration,
    })


@bp.route("/product_calculation", methods=["GET"])
@token_required("admin")
def list_product_calculations():
    """List calculated product prices.

    ---
    tags:
      - Products
    responses:
      200:
        description: Calculated prices for all products
    """
    now = datetime.now(timezone.utc)
    start_of_week = now - timedelta(days=now.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = start_of_week + timedelta(days=7)

    calculations = (
        ProductCalculation.query.join(Product)
        .outerjoin(Brand)
        .filter(
            ProductCalculation.date >= start_of_week,
            ProductCalculation.date < end_of_week,
        )
        .order_by(Brand.brand, Product.model)
        .all()
    )
    result = [
        {
            "id": c.id,
            "product_id": c.product_id,
            "model": c.product.model if c.product else None,
            "description": c.product.description if c.product else None,
            **(_serialize_product_attrs(c.product) if c.product else {k: None for k in ("brand", "memory", "color", "type", "ram", "norme")}),
            "price": c.price,
            "tcp": c.tcp,
            "marge4_5": c.marge4_5,
            "marge": c.marge,
            "prixht_tcp_marge4_5": c.prixht_tcp_marge4_5,
            "prixht_marge4_5": c.prixht_marge4_5,
            "prixht_max": c.prixht_max,
            "date": c.date.strftime("%d/%m/%Y") if c.date else None,
            "week": (
                f"S{c.date.isocalendar().week:02d}-{c.date.isocalendar().year}"
                if c.date
                else None
            ),
            "supplier": c.supplier.name if c.supplier else None,
        }
        for c in calculations
    ]
    return jsonify(result)


@bp.route("/internal_products", methods=["GET"])
def internal_products():
    """Return internal products with related product details."""

    internal_products = InternalProduct.query.options(
        joinedload(InternalProduct.product)
        .joinedload(Product.brand),
        joinedload(InternalProduct.product).joinedload(Product.memory),
        joinedload(InternalProduct.product).joinedload(Product.color),
        joinedload(InternalProduct.product).joinedload(Product.type),
        joinedload(InternalProduct.product).joinedload(Product.RAM),
        joinedload(InternalProduct.product).joinedload(Product.norme),
    ).all()

    result = []
    for internal in internal_products:
        product = internal.product
        product_payload = None

        if product is not None:
            product_payload = {
                "id": product.id,
                "ean": product.ean,
                "part_number": product.part_number,
                "model": product.model,
                "description": product.description,
                **_serialize_product_attrs(product),
                "recommended_price": product.recommended_price,
            }

        result.append(
            {
                "id": internal.id,
                "product_id": internal.product_id,
                "odoo_id": internal.odoo_id,
                "product": product_payload,
            }
        )

    return jsonify(result)


@bp.route("/product_price_summary", methods=["GET"])
@token_required()
def product_price_summary():
    """Return latest supplier prices and average per product."""
    try:
        return _product_price_summary_inner()
    except Exception as exc:
        logger.exception("Erreur dans product_price_summary")
        db.session.rollback()
        return jsonify({
            "error": "Erreur interne lors du calcul des prix",
            "detail": f"{type(exc).__name__}: {exc}",
        }), 500


def _product_price_summary_inner():
    subq = (
        db.session.query(
            ProductCalculation.product_id,
            ProductCalculation.supplier_id,
            func.max(ProductCalculation.date).label("latest"),
        )
        .group_by(ProductCalculation.product_id, ProductCalculation.supplier_id)
        .subquery()
    )

    latest = (
        ProductCalculation.query.join(
            subq,
            (ProductCalculation.product_id == subq.c.product_id)
            & (ProductCalculation.supplier_id == subq.c.supplier_id)
            & (ProductCalculation.date == subq.c.latest),
        )
        .join(Product)
        .outerjoin(Brand)
        .all()
    )

    data = {}
    for calc in latest:
        pid = calc.product_id
        p = calc.product
        if p is None:
            continue
        if pid not in data:
            data[pid] = {
                "id": pid,
                "model": p.model,
                "description": p.description,
                **_serialize_product_attrs(p),
                "supplier_prices": {},
                "recommended_price": _safe_float(p.recommended_price, default=None),
                "buy_price": {},
                "stock_levels": {},
                "latest_calculations": {},
                "tcp": None,
                "min_buy_price": None,
                "min_buy_price_value": None,
                "min_buy_margin": None,
                "latest_margin": None,
                "latest_date": None,
            }
        supplier = calc.supplier.name if calc.supplier else ""
        # Generate unique key if this supplier already has a ref for this product
        supplier_key = supplier
        idx = 2
        while supplier_key in data[pid]["supplier_prices"]:
            supplier_key = f"{supplier} ({idx})"
            idx += 1
        data[pid]["supplier_prices"][supplier_key] = _safe_float(calc.prixht_max)
        data[pid]["buy_price"][supplier_key] = _safe_float(calc.price)
        data[pid]["stock_levels"][supplier_key] = calc.stock
        data[pid]["latest_calculations"][supplier_key] = {
            "price": _safe_float(calc.price),
            "tcp": _safe_float(calc.tcp),
            "marge4_5": _safe_float(calc.marge4_5),
            "marge": _safe_float(calc.marge),
            "marge_percent": _safe_float(calc.marge_percent),
            "prixht_tcp_marge4_5": _safe_float(calc.prixht_tcp_marge4_5),
            "prixht_marge4_5": _safe_float(calc.prixht_marge4_5),
            "prixht_max": _safe_float(calc.prixht_max),
            "stock": calc.stock,
            "date": calc.date.isoformat() if calc.date else None,
        }
        if calc.price is not None:
            current_min = data[pid]["min_buy_price_value"]
            price_val = _safe_float(calc.price)
            if current_min is None or price_val < current_min:
                data[pid]["min_buy_price_value"] = price_val
                data[pid]["min_buy_margin"] = _safe_float(calc.marge)

        if calc.date is not None:
            latest_date = data[pid]["latest_date"]
            if latest_date is None or calc.date > latest_date:
                data[pid]["latest_date"] = calc.date
                preferred_price = (
                    _safe_float(calc.prixht_max, default=0)
                    or _safe_float(calc.prixht_marge4_5, default=0)
                    or _safe_float(calc.prixht_tcp_marge4_5, default=0)
                    or _safe_float(data[pid]["recommended_price"], default=None)
                )
                data[pid]["recommended_price"] = preferred_price
                data[pid]["tcp"] = _safe_float(calc.tcp)
                data[pid]["latest_margin"] = _safe_float(calc.marge, default=None)
                data[pid]["latest_margin_percent"] = _safe_float(
                    calc.marge_percent, default=None
                )

    result = []
    for item in data.values():
        prices = [p for p in item["supplier_prices"].values() if p is not None]
        avg = sum(prices) / len(prices) if prices else 0
        item["average_price"] = round(avg, 2)
        if item["recommended_price"] is None:
            item["recommended_price"] = item["average_price"]
            prod = db.session.get(Product, item["id"])
            if prod:
                prod.recommended_price = item["recommended_price"]
        buy_prices = [
            price for price in item["buy_price"].values() if price is not None
        ]
        min_buy_price_value = item.pop("min_buy_price_value", None)
        if min_buy_price_value is None:
            min_buy_price_value = min(buy_prices) if buy_prices else 0
        item["min_buy_price"] = round(min_buy_price_value, 2)

        latest_margin = item.pop("latest_margin", None)
        margin_from_calc = item.pop("min_buy_margin", None)
        if latest_margin is not None:
            margin_from_calc = latest_margin

        tcp_value = item.get("tcp", 0) or 0
        if margin_from_calc is None:
            margin_from_calc = (
                (item["recommended_price"] or 0) - tcp_value - min_buy_price_value
            )
        item["marge"] = round(margin_from_calc, 2)
        base_cost = (item["min_buy_price"] or 0) + tcp_value
        margin_percent = None
        if item.get("latest_margin_percent") is not None:
            margin_percent = item["latest_margin_percent"]
        elif base_cost:
            margin_percent = round((margin_from_calc / base_cost) * 100, 4)

        item["marge_percent"] = margin_percent
        item["tcp"] = round(tcp_value, 2)
        item.pop("latest_date", None)
        item.pop("latest_margin_percent", None)
        if request.user.role == "client":
            item.pop("supplier_prices", None)
            item.pop("tcp", None)
            item.pop("stock_levels", None)
            item.pop("latest_calculations", None)
        result.append(item)

    db.session.commit()
    return jsonify(result)


@bp.route("/products", methods=["GET"])
@token_required("admin")
def list_products():
    """List all products.

    ---
    tags:
      - Products
    responses:
      200:
        description: A list of products
    """
    products = Product.query.outerjoin(Brand).order_by(Brand.brand, Product.model).all()
    result = [
        {
            "id": p.id,
            "description": p.description,
            "model": p.model,
            **_serialize_product_attrs(p),
            "brand_id": p.brand_id,
            "memory_id": p.memory_id,
            "color_id": p.color_id,
            "type_id": p.type_id,
            "ram_id": p.RAM_id,
            "norme_id": p.norme_id,
            "ean": p.ean,
            "recommended_price": p.recommended_price,
        }
        for p in products
    ]
    return jsonify(result)


@bp.route("/calculate_products", methods=["POST"])
@token_required("admin")
def calculate_products():
    """Calculate pricing for all products in database.

    ---
    tags:
      - Products
    responses:
      200:
        description: Calculation summary
    """
    try:
        recalculate_product_calculations()
    except Exception as exc:
        logger.exception("Erreur lors du calcul des produits")
        return jsonify({"error": f"Erreur lors du calcul : {exc}"}), 500
    count = ProductCalculation.query.count()
    log_activity("calculation.run", details={"product_count": count})
    return jsonify({"status": "success", "created": count})


@bp.route("/export_calculates", methods=["GET"])
@token_required("admin")
def export_calculates():
    """Export product calculations to an Excel file.

    ---
    tags:
      - Products
    produces:
      - application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
    responses:
      200:
        description: XLSX file containing product calculations
    """
    MAX_EXPORT_ROWS = 10_000
    calcs = ProductCalculation.query.join(Product).limit(MAX_EXPORT_ROWS).all()
    rows = []
    for c in calcs:
        p = c.product
        attrs = _serialize_product_attrs(p) if p else {k: None for k in ("brand", "memory", "color", "type", "ram", "norme")}
        rows.append(
            {
                "id": p.id if p else None,
                "name": p.model if p else None,
                "description": p.description if p else None,
                **attrs,
                "price": c.price if c else None,
                "supplier": c.supplier.name if c.supplier else None,
                "TCP": c.tcp,
                "Marge de 4,5%": c.marge4_5,
                "Marge": c.marge,
                "Prix HT avec TCP et marge": c.prixht_tcp_marge4_5,
                "Prix HT avec Marge": c.prixht_marge4_5,
                "Prix HT Maximum": c.prixht_max,
                "Date": c.date.isoformat() if c.date else None,
                "Semaine": c.date.strftime("%Y-%W") if c.date else None,
            }
        )

    df = pd.DataFrame(rows)
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    filename = f"product_calculates_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.route("/reset_calculations", methods=["POST"])
@token_required("admin")
def reset_calculations():
    """Delete all product calculations.

    ---
    tags:
      - Products
    responses:
      200:
        description: Confirmation message
    """
    ProductCalculation.query.delete()
    SupplierCatalog.query.delete()
    return jsonify({"status": "success", "message": "Calculations produits vides"})


@bp.route("/refresh_week", methods=["POST"])
@token_required("admin")
def refresh_week():
    """Delete product calculations and import history for specified weeks.

    ---
    tags:
      - Products
    parameters:
      - in: body
        name: dates
        schema:
          type: object
          properties:
            dates:
              type: array
              items:
                type: string
        required: true
    responses:
      200:
        description: Confirmation message
    """
    data = request.get_json(silent=True)
    if not data or "dates" not in data:
        return jsonify({"error": "Aucune date fournie"}), 400

    try:
        date_objs = [datetime.fromisoformat(d) for d in data["dates"]]
    except Exception:
        return jsonify({"error": "Format de date invalide"}), 400

    week_ranges = {}
    for d in date_objs:
        start = d - timedelta(days=d.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        week_ranges[start] = end

    for start, end in week_ranges.items():
        ProductCalculation.query.filter(
            ProductCalculation.date >= start,
            ProductCalculation.date < end,
        ).delete(synchronize_session=False)
        ImportHistory.query.filter(
            ImportHistory.import_date >= start,
            ImportHistory.import_date < end,
        ).delete(synchronize_session=False)

    db.session.commit()
    return jsonify(
        {
            "status": "success",
            "message": "Calculations produits et historique importations vides pour les semaines sélectionnées",
        }
    )


@bp.route("/products", methods=["POST"])
@token_required("admin")
def create_product():
    """Create a new product.

    ---
    tags:
      - Products
    parameters:
      - in: body
        name: body
        schema:
          type: object
    responses:
      201:
        description: Identifier of created product
    """
    data = request.get_json(silent=True) or {}
    product = Product(
        ean=data.get("ean"),
        model=data.get("model", ""),
        description=data.get("description", ""),
        brand_id=data.get("brand_id"),
        memory_id=data.get("memory_id"),
        color_id=data.get("color_id"),
        type_id=data.get("type_id"),
        recommended_price=data.get("recommended_price"),
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({"id": product.id}), 201


@bp.route("/products/<int:product_id>", methods=["PUT"])
@token_required("admin")
def update_product(product_id):
    """Update an existing product.

    ---
    tags:
      - Products
    parameters:
      - in: path
        name: product_id
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
    product = db.get_or_404(Product, product_id)
    data = request.get_json(silent=True) or {}
    for field in [
        "ean",
        "model",
        "description",
        "brand_id",
        "memory_id",
        "color_id",
        "type_id",
        "recommended_price",
    ]:
        if field in data:
            setattr(product, field, data[field])

    has_margin_update = "marge" in data or "marge_percent" in data
    new_margin = None
    new_margin_percent = None

    if "marge" in data:
        try:
            new_margin = float(data["marge"])
        except (TypeError, ValueError):
            new_margin = None

    if "marge_percent" in data:
        try:
            new_margin_percent = float(data["marge_percent"])
        except (TypeError, ValueError):
            new_margin_percent = None

    if has_margin_update:
        latest_calc = (
            ProductCalculation.query.filter_by(product_id=product_id)
            .order_by(ProductCalculation.date.desc())
            .first()
        )
        if latest_calc:
            latest_date = latest_calc.date
            calcs = ProductCalculation.query.filter(
                ProductCalculation.product_id == product_id,
                ProductCalculation.date == latest_date,
            ).all()
            min_price_calc = None
            if calcs:
                min_price_calc = min(
                    (c for c in calcs if c.price is not None),
                    key=lambda c: c.price,
                    default=None,
                )
            base_price = 0.0
            if min_price_calc and min_price_calc.price is not None:
                base_price = min_price_calc.price
            elif latest_calc.price is not None:
                base_price = latest_calc.price
            tcp_value = latest_calc.tcp or 0
            base_cost = base_price + tcp_value

            margin_value = None
            if new_margin is not None:
                margin_value = round(new_margin, 2)
            elif new_margin_percent is not None and base_cost:
                margin_value = round(base_cost * (new_margin_percent / 100), 2)

            if margin_value is not None:
                if base_cost:
                    product_margin_percent = round((margin_value / base_cost) * 100, 4)
                elif new_margin_percent is not None:
                    product_margin_percent = round(new_margin_percent, 4)
                else:
                    product_margin_percent = None

                product.recommended_price = round(base_cost + margin_value, 2)

                for c in calcs:
                    price_value = c.price or 0
                    calc_base_cost = price_value + (c.tcp or 0)
                    if calc_base_cost:
                        calc_margin_percent = round(
                            (margin_value / calc_base_cost) * 100,
                            4,
                        )
                    else:
                        calc_margin_percent = product_margin_percent

                    c.marge = margin_value
                    c.marge_percent = calc_margin_percent
                    c.prixht_max = round(
                        (c.tcp or 0) + price_value + margin_value,
                        2,
                    )

                latest_calc.marge_percent = product_margin_percent
    db.session.commit()
    return jsonify({"status": "updated"})


@bp.route("/products/bulk_update", methods=["PUT"])
@token_required("admin")
def bulk_update_products():
    """Update multiple products in a single request.

    ---
    tags:
      - Products
    parameters:
      - in: body
        name: body
        schema:
          type: array
          items:
            type: object
    responses:
      200:
        description: Update results
    """
    items = request.get_json(silent=True) or []
    if not isinstance(items, list):
        return jsonify({"error": "Payload invalide"}), 400

    fields = [
        "ean",
        "model",
        "description",
        "brand_id",
        "memory_id",
        "color_id",
        "type_id",
        "recommended_price",
    ]
    updated_ids = []
    for item in items:
        pid = item.get("id")
        if not pid:
            continue
        product = db.session.get(Product, pid)
        if not product:
            continue
        for field in fields:
            if field in item:
                setattr(product, field, item[field])
        updated_ids.append(pid)

    if updated_ids:
        db.session.commit()
    return jsonify({"status": "success", "updated": updated_ids})


@bp.route("/products/bulk_delete", methods=["POST"])
@token_required("admin")
def bulk_delete_products():
    """Delete multiple products in a single request."""

    payload = request.get_json(silent=True) or {}
    ids = payload.get("ids")
    if not isinstance(ids, list):
        return jsonify({"error": "Payload invalide"}), 400

    valid_ids = []
    for value in ids:
        try:
            num = int(value)
        except (TypeError, ValueError):
            continue
        if num <= 0:
            continue
        valid_ids.append(num)

    if not valid_ids:
        return jsonify({"status": "success", "deleted": []})

    products = Product.query.filter(Product.id.in_(valid_ids)).all()
    deleted_ids = []
    for product in products:
        deleted_ids.append(product.id)
        ProductCalculation.query.filter_by(product_id=product.id).delete(
            synchronize_session=False
        )
        db.session.delete(product)

    if deleted_ids:
        log_activity("product.bulk_delete", details={"count": len(deleted_ids)})
        db.session.commit()

    return jsonify({"status": "success", "deleted": deleted_ids})


@bp.route("/products/<int:product_id>", methods=["DELETE"])
@token_required("admin")
def delete_product(product_id):
    """Delete a product.

    ---
    tags:
      - Products
    parameters:
      - in: path
        name: product_id
        required: true
        type: integer
    responses:
      200:
        description: Deletion status
    """
    product = db.get_or_404(Product, product_id)

    # Supprimer explicitement les calculs associés afin d'éviter
    # que SQLAlchemy ne tente de remettre leur clé étrangère à NULL,
    # ce qui viole la contrainte NOT NULL de product_id.
    ProductCalculation.query.filter_by(product_id=product_id).delete(
        synchronize_session=False
    )

    db.session.delete(product)
    db.session.commit()
    return jsonify({"status": "deleted"})
