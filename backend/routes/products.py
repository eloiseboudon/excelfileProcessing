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

from utils.calculations import recalculate_product_calculations

bp = Blueprint("products", __name__)


@bp.route("/product_calculation", methods=["GET"])
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
            "tcp": c.tcp,
            "marge4_5": c.marge4_5,
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


@bp.route("/products", methods=["GET"])
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
            "ean": p.ean,
        }
        for p in products
    ]
    return jsonify(result)


@bp.route("/product_calculations/count", methods=["GET"])
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
                "supplier": c.supplier.name if c.supplier else None,
                "TCP": c.tcp,
                "Marge de 4,5%": c.marge4_5,
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
    return jsonify({"status": "success", "message": "Product calculations empty"})


@bp.route("/refresh_week", methods=["POST"])
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
        return jsonify({"error": "No date provided"}), 400

    try:
        date_objs = [datetime.fromisoformat(d) for d in data["dates"]]
    except Exception:
        return jsonify({"error": "Invalid date format"}), 400

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
            ImportHistory.date >= start,
            ImportHistory.date < end,
        ).delete(synchronize_session=False)

    db.session.commit()
    return jsonify(
        {
            "status": "success",
            "message": "Product calculations and import history empty for selected weeks",
        }
    )


@bp.route("/products", methods=["POST"])
def create_product():
    """Create a new product."""
    data = request.get_json(silent=True) or {}
    product = Product(
        ean=data.get("ean"),
        model=data.get("model", ""),
        description=data.get("description", ""),
        brand_id=data.get("brand_id"),
        memory_id=data.get("memory_id"),
        color_id=data.get("color_id"),
        type_id=data.get("type_id"),
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({"id": product.id}), 201


@bp.route("/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    """Update an existing product."""
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
    ]:
        if field in data:
            setattr(product, field, data[field])
    db.session.commit()
    return jsonify({"status": "updated"})


@bp.route("/products/bulk_update", methods=["PUT"])
def bulk_update_products():
    """Update multiple products in a single request."""
    items = request.get_json(silent=True) or []
    if not isinstance(items, list):
        return jsonify({"error": "Invalid payload"}), 400

    fields = [
        "ean",
        "model",
        "description",
        "brand_id",
        "memory_id",
        "color_id",
        "type_id",
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
def delete_product(product_id):
    """Delete a product."""
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"status": "deleted"})
