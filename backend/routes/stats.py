from flask import Blueprint, jsonify, request
from models import Brand, Product, ProductCalculation, Supplier
from utils.auth import token_required
from sqlalchemy import extract, func

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


def _build_stats_query(filters):
    """Build a filtered ProductCalculation query from common stat filters."""
    query = ProductCalculation.query.join(Supplier).join(Product).outerjoin(Brand)

    if filters.get("supplier_id"):
        query = query.filter(ProductCalculation.supplier_id == filters["supplier_id"])
    if filters.get("brand_id"):
        query = query.filter(Product.brand_id == filters["brand_id"])
    if filters.get("product_id"):
        query = query.filter(Product.id == filters["product_id"])

    start_week = filters.get("start_week")
    if start_week:
        sy, sw = _parse_week(start_week)
        query = query.filter(
            extract("year", ProductCalculation.date) * 100
            + extract("week", ProductCalculation.date)
            >= sy * 100 + sw
        )
    end_week = filters.get("end_week")
    if end_week:
        ey, ew = _parse_week(end_week)
        query = query.filter(
            extract("year", ProductCalculation.date) * 100
            + extract("week", ProductCalculation.date)
            <= ey * 100 + ew
        )

    return query


@bp.route("/price_stats", methods=["GET"])
@token_required("admin")
def price_stats():
    """Return average prices per week. If a product_id is supplied, results are
    grouped by supplier, otherwise aggregated globally.
    ---
    tags:
      - Stats
    responses:
      200:
        description: List of graph settings
    """

    product_id = request.args.get("product_id", type=int)
    filters = {
        "supplier_id": request.args.get("supplier_id", type=int),
        "brand_id": request.args.get("brand_id", type=int),
        "product_id": product_id,
        "start_week": request.args.get("start_week"),
        "end_week": request.args.get("end_week"),
    }

    query = _build_stats_query(filters)

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
        fields = [
            Supplier.name.label("supplier"),
            Brand.brand.label("brand"),
            week_field,
            year_field,
            func.avg(ProductCalculation.price).label("avg_price"),
        ]
        group_by = [Supplier.name, Brand.brand, week_field, year_field]

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
            "supplier": r.supplier,
        }

        if not product_id:
            entry["brand"] = r.brand
        data.append(entry)

    return jsonify(data)


@bp.route("/brand_supplier_average", methods=["GET"])
@token_required("admin")
def brand_supplier_average():
    """Average price by brand and supplier.

    Optional query parameters:
    - brand_id: filter on a specific brand
    - supplier_id: filter on a specific supplier
    - start_week / end_week: limit to a week range
    ---
    tags:
      - Stats
    responses:
      200:
        description: Average price grouped by brand and supplier
    """

    filters = {
        "supplier_id": request.args.get("supplier_id", type=int),
        "brand_id": request.args.get("brand_id", type=int),
        "start_week": request.args.get("start_week"),
        "end_week": request.args.get("end_week"),
    }

    query = _build_stats_query(filters)

    results = (
        query.with_entities(
            Supplier.name.label("supplier"),
            Brand.brand.label("brand"),
            func.avg(ProductCalculation.price).label("avg_price"),
        )
        .group_by(Supplier.name, Brand.brand)
        .order_by(Brand.brand, Supplier.name)
        .all()
    )

    data = [
        {"supplier": r.supplier, "brand": r.brand, "avg_price": float(r.avg_price)}
        for r in results
    ]

    return jsonify(data)


@bp.route("/product_supplier_average", methods=["GET"])
@token_required("admin")
def product_supplier_average():
    """Average price by product and supplier.

    Optional query parameters:
    - brand_id: filter on a specific brand
    - product_id: filter on a specific product
    - supplier_id: filter on a specific supplier
    - start_week / end_week: limit to a week range
    ---
    tags:
      - Stats
    responses:
      200:
        description: Average price grouped by product and supplier
    """

    filters = {
        "supplier_id": request.args.get("supplier_id", type=int),
        "brand_id": request.args.get("brand_id", type=int),
        "product_id": request.args.get("product_id", type=int),
        "start_week": request.args.get("start_week"),
        "end_week": request.args.get("end_week"),
    }

    query = _build_stats_query(filters)

    results = (
        query.with_entities(
            Supplier.name.label("supplier"),
            Product.model.label("product"),
            func.avg(ProductCalculation.price).label("avg_price"),
        )
        .group_by(Supplier.name, Product.model)
        .order_by(Product.model, Supplier.name)
        .all()
    )

    data = [
        {"supplier": r.supplier, "product": r.product, "avg_price": float(r.avg_price)}
        for r in results
    ]

    return jsonify(data)
