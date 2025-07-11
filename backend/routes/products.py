from datetime import datetime, timedelta, timezone
from io import BytesIO

import pandas as pd
from flask import Blueprint, jsonify, request, send_file
from utils.calculations import recalculate_product_calculations
from models import Product, ProductCalculation, db

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
    calculations = ProductCalculation.query.join(Product).all()
    result = [
        {
            "id": c.id,
            "product_id": c.product_id,
            "name": c.product.name if c.product else None,
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
    products = Product.query.all()
    result = [
        {
            "id": p.id,
            "description": p.description,
            "name": p.name,
            "brand": p.brand.brand if p.brand else None,
            "price": (
                p.reference.selling_price
                if p.reference and p.reference.selling_price
                else None
            ),
            "memory": p.memory.memory if p.memory else None,
            "color": p.color.color if p.color else None,
            "type": p.type.type if p.type else None,
            "reference": (
                {
                    "id": p.reference.id if p.reference else None,
                    "description": p.reference.description if p.reference else None,
                }
                if p.reference
                else None
            ),
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
                "reference_id": p.reference_id if p else None,
                "name": p.name if p else None,
                "description": p.description if p else None,
                "brand": p.brand.brand if p.brand else None,
                "price": c.price if c else None,
                "memory": p.memory.memory if p.memory else None,
                "color": p.color.color if p.color else None,
                "type": p.type.type if p.type else None,
                "supplier": p.supplier.name if p.supplier else None,
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
    return jsonify({"status": "success", "message": "Product calculations empty"})


@bp.route("/refresh_week", methods=["POST"])
def refresh_week():
    """Delete product calculations for specified weeks.

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

    db.session.commit()
    return jsonify(
        {
            "status": "success",
            "message": "Product calculations empty for selected weeks",
        }
    )
