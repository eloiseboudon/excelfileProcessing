from flask import Blueprint, jsonify
from sqlalchemy import func, extract
from models import ProductCalculation, Product, Supplier, Brand

bp = Blueprint("stats", __name__)


@bp.route("/price_stats", methods=["GET"])
def price_stats():
    """Aggregate average price per week, supplier and brand."""
    results = (
        ProductCalculation.query.join(
            Supplier, ProductCalculation.supplier_id == Supplier.id
        )
        .join(Product, ProductCalculation.product_id == Product.id)
        .join(Brand, Product.brand_id == Brand.id)
        .with_entities(
            Supplier.name.label("supplier"),
            Brand.brand.label("brand"),
            extract("week", ProductCalculation.date).label("week"),
            extract("year", ProductCalculation.date).label("year"),
            func.avg(ProductCalculation.price).label("avg_price"),
        )
        .group_by(
            Supplier.name,
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
            "brand": r.brand,
            "week": f"S{int(r.week):02d}-{int(r.year)}",
            "avg_price": float(r.avg_price),
        }
        for r in results
    ]
    return jsonify(data)
