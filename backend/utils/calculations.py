import math
from datetime import datetime, timezone

from models import (
    BrandTranslation,
    ColorTranslation,
    MemoryTranslation,
    Product,
    ProductCalculation,
    TemporaryImport,
    TypeTranslation,
    db,
)


def process_description(description: str):
    """Process the description to extract product characteristics."""
    # Normalize the description
    description = description.lower().strip()

    # Extract brand
    brand = BrandTranslation.query.filter(
        BrandTranslation.brand_source.ilike(f"%{description}%")
    ).first()

    # Extract memory
    memory = MemoryTranslation.query.filter(
        MemoryTranslation.memory_source.ilike(f"%{description}%")
    ).first()

    # Extract color
    color = ColorTranslation.query.filter(
        ColorTranslation.color_source.ilike(f"%{description}%")
    ).first()

    # Extract type
    type_ = TypeTranslation.query.filter(
        TypeTranslation.type_source.ilike(f"%{description}%")
    ).first()

    return {
        "brand_id": brand.brand_target_id if brand else None,
        "memory_id": memory.memory_target_id if memory else None,
        "color_id": color.color_target_id if color else None,
        "type_id": type_.type_target_id if type_ else None,
    }


def recalculate_product_calculations():
    """Recompute ProductCalculation entries from TemporaryImport data."""

    # Récupérer tous les imports temporaires
    temps = TemporaryImport.query.all()

    # D'abord enrichir les données des imports temporaires
    for temp in temps:
        # Extraire les caractéristiques de la description
        characteristics = process_description(temp.description)

        # Mettre à jour les champs de l'import temporaire
        temp.brand_id = characteristics["brand_id"]
        temp.memory_id = characteristics["memory_id"]
        temp.color_id = characteristics["color_id"]
        temp.type_id = characteristics["type_id"]

        # Sauvegarder les changements
        db.session.add(temp)

    # Commit les mises à jour des imports temporaires
    db.session.commit()

    # Maintenant faire la recherche de correspondance
    for temp in temps:
        # Étape 1 : Recherche sans le type
        product = Product.query.filter(
            Product.brand_id == temp.brand_id,
            Product.memory_id == temp.memory_id,
            Product.color_id == temp.color_id,
        ).first()

        # Si non trouvé et que le type est défini, on essaie avec le type
        if not product and temp.type_id:
            product = Product.query.filter(
                Product.brand_id == temp.brand_id,
                Product.memory_id == temp.memory_id,
                Product.color_id == temp.color_id,
                Product.type_id == temp.type_id,
            ).first()

        # Si toujours non trouvé, passer au suivant
        if not product:
            continue

        # Calculer les valeurs
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

        # Créer une nouvelle entrée de calcul avec la date courante
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
