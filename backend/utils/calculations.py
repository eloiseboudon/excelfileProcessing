import math
from datetime import datetime, timezone
from typing import Dict, Iterable, Tuple

from models import (
    BrandTranslation,
    ColorTranslation,
    MemoryOption,
    MemoryTranslation,
    Product,
    ProductCalculation,
    TemporaryImport,
    TypeTranslation,
    db,
)


def _load_mappings() -> Dict[str, Iterable[Tuple[str, int]]]:
    """Load translation mappings into memory for faster lookups."""
    return {
        "brand": [
            (t.brand_source.lower(), t.brand_target_id)
            for t in BrandTranslation.query.all()
        ],
        "memory": [
            (t.memory_source.lower(), t.memory_target_id)
            for t in MemoryTranslation.query.all()
        ],
        "color": [
            (t.color_source.lower(), t.color_target_id)
            for t in ColorTranslation.query.all()
        ],
        "type": [
            (t.type_source.lower(), t.type_target_id)
            for t in TypeTranslation.query.all()
        ],
    }


def process_description(
    description: str | None,
    model: str | None,
    mappings: Dict[str, Iterable[Tuple[str, int]]],
):
    """Extract identifiers from the product description using cached mappings."""
    desc = (description or "").lower()
    model = (model or description or "").lower()

    def find_id(items: Iterable[Tuple[str, int]]):
        for src, target in items:
            if src and src in desc:
                return target
        return None

    return {
        "brand_id": find_id(mappings["brand"]),
        "memory_id": find_id(mappings["memory"]),
        "color_id": find_id(mappings["color"]),
        "type_id": find_id(mappings["type"]),
    }


def recalculate_product_calculations():
    """Recompute ProductCalculation entries from TemporaryImport data."""
    mappings = _load_mappings()
    temps = TemporaryImport.query.all()

    for temp in temps:
        characteristics = process_description(temp.description, temp.model, mappings)
        temp.brand_id = characteristics["brand_id"]
        temp.memory_id = characteristics["memory_id"]
        temp.color_id = characteristics["color_id"]
        temp.type_id = characteristics["type_id"]
        db.session.add(temp)

    db.session.commit()

    for temp in temps:
        query = Product.query

        if temp.brand_id is not None:
            query = query.filter(Product.brand_id == temp.brand_id)
        if temp.memory_id is not None:
            query = query.filter(Product.memory_id == temp.memory_id)
        if temp.color_id is not None:
            query = query.filter(Product.color_id == temp.color_id)
        if temp.model_id is not None:
            query = query.filter(Product.model.ilike(f"%{temp.model}%"))
        product = query.first()

        # if not product and temp.type_id is not None:
        #     query_type = query.filter(Product.type_id == temp.type_id)
        #     product = query_type.first()

        if not product:
            continue

        price = temp.selling_price or 0
        memory = product.memory.memory.upper() if product.memory else ""

        memory_option = MemoryOption.query.filter_by(memory=memory).first()
        if not memory_option:
            tcp = 0
        else:
            tcp = memory_option.tcp_value

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
