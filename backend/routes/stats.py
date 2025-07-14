from flask import Blueprint, jsonify, request
from sqlalchemy import func, extract
from models import ProductCalculation, Product, Supplier, Brand

bp = Blueprint("stats", __name__)


def _parse_week(w):
    if not w:
        return None
    w = w.strip()
    if w.startswith("S"):
        week_part, year_part = w[1:].split("-")
    elif "-W" in w:
        year_part, week_part = w.split("-W")
    else:
        year_part, week_part = w.split("-")
    return int(year_part), int(week_part)


@bp.route("/price_stats", methods=["GET"])
def price_stats():
    """Return average prices per week. If a product_id is supplied, results are
    grouped by supplier, otherwise aggregated globally."""

    supplier_id = request.args.get("supplier_id", type=int)
    brand_id = request.args.get("brand_id", type=int)
    product_id = request.args.get("product_id", type=int)
    start_week = request.args.get("start_week")
    end_week = request.args.get("end_week")

    query = (
        ProductCalculation.query.join(Supplier)
        .join(Product)
        .join(Brand)
    )

    if supplier_id:
        query = query.filter(ProductCalculation.supplier_id == supplier_id)
    if brand_id:
        query = query.filter(Product.brand_id == brand_id)
    if product_id:
        query = query.filter(Product.id == product_id)

    if start_week:
        sy, sw = _parse_week(start_week)
        query = query.filter(
            extract("year", ProductCalculation.date) * 100
            + extract("week", ProductCalculation.date)
            >= sy * 100 + sw
        )
    if end_week:
        ey, ew = _parse_week(end_week)
        query = query.filter(
            extract("year", ProductCalculation.date) * 100
            + extract("week", ProductCalculation.date)
            <= ey * 100 + ew
        )

    week_field = extract("week", ProductCalculation.date).label("week")
    year_field = extract("year", ProductCalculation.date).label("year")

    if product_id:
        fields = [
            Supplier.name.label("supplier"),
            week_field,
            year_field,
            func.avg(ProductCalculation.price).label("avg_price"),
        ]
        group_by = [Supplier.name, week_field, year_field]
    else:
        fields = [week_field, year_field, func.avg(ProductCalculation.price).label("avg_price")]
        group_by = [week_field, year_field]

    results = (
        query.with_entities(*fields)
        .group_by(*group_by)
        .order_by(year_field, week_field)
        .all()
    )

    data = []
    for r in results:
        entry = {
            "week": f"S{int(r.week):02d}-{int(r.year)}",
            "avg_price": float(r.avg_price),
        }
        if product_id:
            entry["supplier"] = r.supplier
        data.append(entry)

    return jsonify(data)
