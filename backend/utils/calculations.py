from datetime import datetime, timezone
import math
from models import db, Product, TemporaryImport, ProductCalculation


def recalculate_product_calculations():
    """Recompute ProductCalculation entries from TemporaryImport data."""
    ProductCalculation.query.delete()
    db.session.commit()

    temps = TemporaryImport.query.all()
    for temp in temps:
        product = Product.query.filter_by(ean=temp.ean).first()
        if not product:
            continue

        price = temp.selling_price or 0
        memory = product.memory.memory.upper() if product.memory else ""
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
            product_id=product.id,
            supplier_id=temp.supplier_id,
            price=round(price, 2),
            tcp=round(tcp, 2),
            marge4_5=round(margin45, 2),
            prixht_tcp_marge4_5=round(price_with_tcp, 2),
            prixht_marge4_5=round(price_with_margin, 2),
            prixht_max=max_price,
            date=datetime.now(timezone.utc),
        )
        db.session.add(calc)

    db.session.commit()
