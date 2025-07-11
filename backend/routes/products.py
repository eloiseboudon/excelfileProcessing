import math
from datetime import datetime, timedelta, timezone
from io import BytesIO

import pandas as pd
from flask import Blueprint, jsonify, request, send_file
from models import (
    Brand,
    Color,
    ColorTranslation,
    DeviceType,
    Exclusion,
    MemoryOption,
    Product,
    ProductCalculation,
    ProductReference,
    db,
)

bp = Blueprint("products", __name__)


@bp.route("/product_calculation", methods=["GET"])
def list_product_calculations():
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
            "date": c.date.strftime("%D") if c.date else None,
            "week": (
                "S" + c.date.strftime("%W") + "-" + c.date.strftime("%Y")
                if c.date
                else None
            ),
        }
        for c in calculations
    ]
    return jsonify(result)


@bp.route("/products", methods=["GET"])
def list_products():
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
    count = ProductCalculation.query.count()
    return jsonify({"count": count})


@bp.route("/populate_products", methods=["POST"])
def populate_products_from_reference():
    references = ProductReference.query.all()
    brands = Brand.query.all()
    colors = Color.query.all()
    memories = MemoryOption.query.all()
    types = DeviceType.query.all()
    color_transcos = ColorTranslation.query.all()
    exclusions = [e.term.lower() for e in Exclusion.query.all()]

    created = 0
    updated = 0
    for ref in references:
        description_lower = ref.description.lower() if ref.description else ""
        if any(exc in description_lower for exc in exclusions):
            continue

        brand_id = None
        for b in brands:
            if b.brand.lower() in description_lower:
                brand_id = b.id
                break

        color_id = None
        for c in colors:
            if c.color.lower() in description_lower:
                color_id = c.id
                break
        if not color_id:
            for ct in color_transcos:
                if ct.color_source.lower() in description_lower:
                    color_id = ct.color_target_id
                    break

        memory_id = None
        for m in memories:
            if m.memory.lower() in description_lower:
                memory_id = m.id
                break

        type_id = None
        for t in types:
            if t.type.lower() in description_lower:
                type_id = t.id
                break

        existing = Product.query.filter_by(
            reference_id=ref.id,
            supplier_id=ref.supplier_id,
        ).first()
        if existing:
            existing.description = ref.description
            existing.name = ref.description
            existing.brand_id = brand_id
            existing.color_id = color_id
            existing.memory_id = memory_id
            existing.type_id = type_id
            existing.supplier_id = ref.supplier_id
            updated += 1
        else:
            product = Product(
                reference_id=ref.id,
                description=ref.description,
                name=ref.description,
                brand_id=brand_id,
                color_id=color_id,
                memory_id=memory_id,
                type_id=type_id,
                supplier_id=ref.supplier_id,
            )
            db.session.add(product)
            created += 1
    db.session.commit()
    return jsonify({"status": "success", "created": created, "updated": updated})


@bp.route("/calculate_products", methods=["POST"])
def calculate_products():
    ProductCalculation.query.delete()
    db.session.commit()
    products = Product.query.all()
    created = 0
    for p in products:
        price = (
            p.reference.selling_price
            if p.reference and p.reference.selling_price
            else 0
        )
        memory = p.memory.memory.upper() if p.memory else ""
        tcp = 0
        if memory == "32GB":
            tcp = 10
        elif memory == "64GB":
            tcp = 12
        elif memory in ["128GB", "256GB", "512GB", "1TB"]:
            tcp = 14
        margin45 = price * 0.045
        price_with_tcp = price + tcp + margin45
        thresholds = [15, 29, 49, 79, 99, 129, 149, 179, 209, 299, 499, 799, 999]
        margins = [
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
        price_with_margin = price
        for i, t in enumerate(thresholds):
            if price <= t:
                price_with_margin = price * margins[i]
                break
        if price > thresholds[-1]:
            price_with_margin = price * 1.06
        max_price = math.ceil(max(price_with_tcp, price_with_margin))
        calc = ProductCalculation(
            product_id=p.id,
            price=round(price, 2),
            tcp=round(tcp, 2),
            marge4_5=round(margin45, 2),
            prixht_tcp_marge4_5=round(price_with_tcp, 2),
            prixht_marge4_5=round(price_with_margin, 2),
            prixht_max=max_price,
            date=datetime.now(timezone.utc),
        )
        db.session.add(calc)
        created += 1
    db.session.commit()
    return jsonify({"status": "success", "created": created})


@bp.route("/export_calculates", methods=["GET"])
def export_calculates():
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
    ProductCalculation.query.delete()
    return jsonify({"status": "success", "message": "Product calculations empty"})


@bp.route("/refresh_week", methods=["POST"])
def refresh_week():
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
