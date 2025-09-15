from datetime import datetime, timedelta, timezone
from io import BytesIO

import pandas as pd
from flask import Blueprint, jsonify, request, send_file
from models import (
    Brand,
    ImportHistory,
    Product,
    ProductCalculation,
    TemporaryImport,
    db,
)
from sqlalchemy import func
from utils.auth import token_required
from utils.calculations import recalculate_product_calculations

bp = Blueprint("products", __name__)


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
    calculations = (
        ProductCalculation.query.join(Product)
        .join(Brand)
        .order_by(Brand.brand, Product.model)
        .all()
    )
    result = [
        {
            "id": c.id,
            "product_id": c.product_id,
            "model": c.product.model if c.product else None,
            "description": c.product.description if c.product else None,
            "brand": c.product.brand.brand if c.product and c.product.brand else None,
            "price": c.price,
            "memory": (
                c.product.memory.memory if c.product and c.product.memory else None
            ),
            "color": c.product.color.color if c.product and c.product.color else None,
            "type": c.product.type.type if c.product and c.product.type else None,
            "ram": c.product.RAM.ram if c.product and c.product.RAM else None,
            "norme": c.product.norme.norme if c.product and c.product.norme else None,
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


@bp.route("/product_price_summary", methods=["GET"])
@token_required()
def product_price_summary():
    """Return latest supplier prices and average per product."""

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
        .join(Brand)
        .all()
    )

    data = {}
    for calc in latest:
        pid = calc.product_id
        p = calc.product
        if pid not in data:
            data[pid] = {
                "id": pid,
                "model": p.model,
                "description": p.description,
                "brand": p.brand.brand if p.brand else None,
                "memory": p.memory.memory if p.memory else None,
                "color": p.color.color if p.color else None,
                "type": p.type.type if p.type else None,
                "ram": p.RAM.ram if p.RAM else None,
                "norme": p.norme.norme if p.norme else None,
                "supplier_prices": {},
                "recommended_price": p.recommended_price,
                "buy_price": {},
                "tcp": calc.tcp,
                "min_buy_price": None,
                "min_buy_price_value": None,
                "min_buy_margin": None,
                "marge_samples": [],
            }
        supplier = calc.supplier.name if calc.supplier else ""
        data[pid]["supplier_prices"][supplier] = calc.prixht_max
        data[pid]["buy_price"][supplier] = calc.price
        if calc.marge is not None:
            data[pid]["marge_samples"].append(calc.marge)
        if data[pid]["tcp"] is None and calc.tcp is not None:
            data[pid]["tcp"] = calc.tcp
        if calc.price is not None:
            current_min = data[pid]["min_buy_price_value"]
            if current_min is None or calc.price < current_min:
                data[pid]["min_buy_price_value"] = calc.price
                data[pid]["min_buy_margin"] = calc.marge

    result = []
    for item in data.values():
        prices = [p for p in item["supplier_prices"].values() if p is not None]
        avg = sum(prices) / len(prices) if prices else 0
        item["average_price"] = round(avg, 2)
        if item["recommended_price"] is None:
            item["recommended_price"] = item["average_price"]
            prod = Product.query.get(item["id"])
            if prod:
                prod.recommended_price = item["recommended_price"]
        buy_prices = [
            price for price in item["buy_price"].values() if price is not None
        ]
        min_buy_price_value = item.pop("min_buy_price_value", None)
        if min_buy_price_value is None:
            min_buy_price_value = min(buy_prices) if buy_prices else 0
        item["min_buy_price"] = round(min_buy_price_value, 2)

        margin_from_calc = item.pop("min_buy_margin", None)
        margin_samples = [m for m in item.pop("marge_samples", []) if m is not None]
        if margin_from_calc is None and margin_samples:
            margin_from_calc = margin_samples[0]

        tcp_value = item.get("tcp", 0) or 0
        if margin_from_calc is None:
            margin_from_calc = (
                (item["recommended_price"] or 0)
                - tcp_value
                - min_buy_price_value
            )
        item["marge"] = round(margin_from_calc, 2)
        item["tcp"] = round(tcp_value, 2)
        if request.user.role == "client":
            item.pop("supplier_prices", None)
            item.pop("tcp", None)
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
    products = Product.query.join(Brand).order_by(Brand.brand, Product.model).all()
    result = [
        {
            "id": p.id,
            "description": p.description,
            "model": p.model,
            "brand": p.brand.brand if p.brand else None,
            "brand_id": p.brand_id,
            "memory": p.memory.memory if p.memory else None,
            "memory_id": p.memory_id,
            "color": p.color.color if p.color else None,
            "color_id": p.color_id,
            "type": p.type.type if p.type else None,
            "type_id": p.type_id,
            "ram": p.RAM.ram if p.RAM else None,
            "ram_id": p.RAM_id,
            "norme": p.norme.norme if p.norme else None,
            "norme_id": p.norme_id,
            "ean": p.ean,
            "recommended_price": p.recommended_price,
        }
        for p in products
    ]
    return jsonify(result)


@bp.route("/product_calculations/count", methods=["GET"])
@token_required("admin")
def count_product_calculations():
    """Return the number of product calculations available.

    ---
    tags:
      - Products
    responses:
      200:
        description: Number of available calculations
        schema:
          type: object
          properties:
            count:
              type: integer
    """
    count = ProductCalculation.query.count()
    return jsonify({"count": count})


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
    recalculate_product_calculations()
    count = ProductCalculation.query.count()
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
    calcs = ProductCalculation.query.join(Product).all()
    rows = []
    for c in calcs:
        p = c.product
        rows.append(
            {
                "id": p.id if p else None,
                "name": p.model if p else None,
                "description": p.description if p else None,
                "brand": p.brand.brand if p.brand else None,
                "price": c.price if c else None,
                "memory": p.memory.memory if p.memory else None,
                "color": p.color.color if p.color else None,
                "type": p.type.type if p.type else None,
                "ram": p.RAM.ram if p.RAM else None,
                "norme": p.norme.norme if p.norme else None,
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


@bp.route("/refresh", methods=["POST"])
@token_required("admin")
def refresh():
    """Delete all product calculations.

    ---
    tags:
      - Products
    responses:
      200:
        description: Confirmation message
    """
    ProductCalculation.query.delete()
    TemporaryImport.query.delete()
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
    product = Product.query.get_or_404(product_id)
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

    if "marge" in data:
        try:
            new_margin = float(data["marge"])
        except (TypeError, ValueError):
            new_margin = None
        if new_margin is not None:
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
                product.recommended_price = round(
                    (latest_calc.tcp or 0) + base_price + new_margin,
                    2,
                )
                for c in calcs:
                    c.marge = round(new_margin, 2)
                    price_value = c.price or 0
                    tcp_value = c.tcp or 0
                    c.prixht_max = round(tcp_value + price_value + new_margin, 2)
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
        product = Product.query.get(pid)
        if not product:
            continue
        for field in fields:
            if field in item:
                setattr(product, field, item[field])
        updated_ids.append(pid)

    if updated_ids:
        db.session.commit()
    return jsonify({"status": "success", "updated": updated_ids})


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
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"status": "deleted"})
