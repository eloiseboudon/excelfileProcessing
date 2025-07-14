from flask import Blueprint, jsonify, request
from sqlalchemy import func, extract
from models import ProductCalculation, Product, Supplier, Brand

bp = Blueprint("stats", __name__)


@bp.route("/price_stats", methods=["GET"])
def price_stats():
    """Aggregate average price per week with optional filters."""

    supplier_id = request.args.get("supplier_id", type=int)
    brand_id = request.args.get("brand_id", type=int)
    product_id = request.args.get("product_id", type=int)

    query = (
        ProductCalculation.query.join(
            Supplier, ProductCalculation.supplier_id == Supplier.id
        )
        .join(Product, ProductCalculation.product_id == Product.id)
        .join(Brand, Product.brand_id == Brand.id)
    )

    if supplier_id:
        query = query.filter(ProductCalculation.supplier_id == supplier_id)
    if brand_id:
        query = query.filter(Product.brand_id == brand_id)
    if product_id:
        query = query.filter(Product.id == product_id)

    results = (
        query.with_entities(
            Supplier.name.label("supplier"),
            Product.id.label("product_id"),
            Product.model.label("product"),
            Brand.brand.label("brand"),
            extract("week", ProductCalculation.date).label("week"),
            extract("year", ProductCalculation.date).label("year"),
            func.avg(ProductCalculation.price).label("avg_price"),
        )
        .group_by(
            Supplier.name,
            Product.id,
            Product.model,
            Brand.brand,
            extract("year", ProductCalculation.date),
            extract("week", ProductCalculation.date),
        )
        .order_by(
            extract("year", ProductCalculation.date),
            extract("week", ProductCalculation.date),
        )
        .all()
    )

    data = [
        {
            "supplier": r.supplier,
            "product_id": r.product_id,
            "product": r.product,
            "brand": r.brand,
            "week": f"S{int(r.week):02d}-{int(r.year)}",
            "avg_price": float(r.avg_price),
        }
        for r in results
    ]
    return jsonify(data)
