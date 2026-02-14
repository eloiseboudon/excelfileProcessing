from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Dict, Iterable, Tuple

from models import (
    Brand,
    Color,
    ColorTranslation,
    DeviceType,
    LabelCache,
    MemoryOption,
    Product,
    ProductCalculation,
    TemporaryImport,
    db,
)
from utils.llm_matching import normalize_label
from utils.pricing import compute_margin_prices


def _load_mappings() -> Dict[str, Iterable[Tuple[str, int]]]:
    """Load translation mappings into memory for faster lookups."""
    def _build_pairs(queryset, attr: str) -> list[Tuple[str, int]]:
        pairs: list[Tuple[str, int]] = []
        for item in queryset:
            value = getattr(item, attr, None)
            if value:
                pairs.append((value.lower(), item.id))
        return pairs

    mappings: Dict[str, Iterable[Tuple[str, int]]] = {
        "brand": _build_pairs(Brand.query.all(), "brand"),
        "memory": _build_pairs(MemoryOption.query.all(), "memory"),
        "color": _build_pairs(Color.query.all(), "color"),
        "type": _build_pairs(DeviceType.query.all(), "type"),
    }

    # Include additional color translations (e.g. synonyms) if available.
    color_translations = [
        (t.color_source.lower(), t.color_target_id)
        for t in ColorTranslation.query.all()
        if t.color_source
    ]
    if color_translations:
        mappings["color"] = list(mappings["color"]) + color_translations

    return mappings


def process_description(
    description: str | None,
    model: str | None,
    mappings: Dict[str, Iterable[Tuple[str, int]]],
):
    """Extract identifiers from the product description using cached mappings."""
    desc = (description or "").lower()
    model = (model or description or "").lower()
    texts = [desc, model]

    def find_id(items: Iterable[Tuple[str, int]]):
        for src, target in items:
            if not src:
                continue
            for text in texts:
                if src in text:
                    return target
        return None

    return {
        "brand_id": find_id(mappings.get("brand", [])),
        "memory_id": find_id(mappings.get("memory", [])),
        "color_id": find_id(mappings.get("color", [])),
        "type_id": find_id(mappings.get("type", [])),
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

    # Preload LabelCache as dict: (supplier_id, normalized_label) → product_id
    label_cache_map: Dict[Tuple[int, str], int] = {}
    for lc in LabelCache.query.filter(LabelCache.product_id.isnot(None)).all():
        label_cache_map[(lc.supplier_id, lc.normalized_label)] = lc.product_id

    for temp in temps:
        product = None
        ean = (temp.ean or "").strip() if temp.ean else ""
        if ean:
            product = Product.query.filter(Product.ean == ean).first()

        if not product:
            query = Product.query
            if temp.model is not None:
                if temp.brand_id is not None:
                    query = query.filter(Product.brand_id == temp.brand_id)
                if temp.memory_id is not None:
                    query = query.filter(Product.memory_id == temp.memory_id)
                if temp.color_id is not None:
                    query = query.filter(Product.color_id == temp.color_id)
                query = query.filter(Product.model.ilike(f"%{temp.model}%"))
            product = query.first()

        # Fallback: LabelCache lookup for LLM-matched products
        if not product and temp.supplier_id:
            raw_label = temp.description or temp.model or ""
            if raw_label:
                normalized = normalize_label(raw_label)
                cached_product_id = label_cache_map.get(
                    (temp.supplier_id, normalized)
                )
                if cached_product_id:
                    product = db.session.get(Product, cached_product_id)

        if not product:
            continue

        price = temp.selling_price or 0
        memory = product.memory.memory.upper() if product.memory else ""

        memory_option = MemoryOption.query.filter_by(memory=memory).first()
        if not memory_option:
            tcp = 0
        else:
            tcp = memory_option.tcp_value

        (
            margin45,
            price_with_tcp,
            price_with_margin,
            max_price,
            marge_value,
            marge_percent,
        ) = compute_margin_prices(price, tcp)

        # Vérifier que les valeurs ne sont pas NaN
        if math.isnan(price_with_tcp) or math.isnan(price_with_margin):
            print(f"Valeurs NaN détectées pour le produit {product.id}")
            continue

        calc = ProductCalculation(
            product_id=product.id,
            supplier_id=temp.supplier_id,
            price=round(price, 2),
            tcp=round(tcp, 2),
            marge4_5=margin45,
            prixht_tcp_marge4_5=price_with_tcp,
            prixht_marge4_5=price_with_margin,
            prixht_max=max_price,
            date=datetime.now(timezone.utc),
            marge=marge_value,
            marge_percent=marge_percent,
            stock=temp.quantity,
        )
        db.session.add(calc)

    db.session.commit()


def update_product_calculations_for_memory_option(memory_option_id: int) -> None:
    """Update ProductCalculation rows when a memory option's TCP changes."""
    option = db.session.get(MemoryOption, memory_option_id)
    if not option:
        return

    calcs = (
        ProductCalculation.query.join(Product)
        .filter(Product.memory_id == option.id)
        .all()
    )

    for calc in calcs:
        price = calc.price or 0
        tcp = option.tcp_value
        (
            margin45,
            price_with_tcp,
            price_with_margin,
            max_price,
            marge_value,
            marge_percent,
        ) = compute_margin_prices(price, tcp)

        calc.tcp = round(tcp, 2)
        calc.marge4_5 = margin45
        calc.prixht_tcp_marge4_5 = price_with_tcp
        calc.prixht_marge4_5 = price_with_margin
        calc.prixht_max = max_price
        calc.marge = marge_value
        calc.marge_percent = marge_percent

    if calcs:
        db.session.commit()
