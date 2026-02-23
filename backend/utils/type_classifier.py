"""Keyword-based device type classifier for products.

Rules are ordered by priority: more specific patterns first.
Audio is checked before Accessoire to avoid "Charging Case" in AirPods
names being incorrectly classified as a case accessory.
"""

from typing import Dict, List, Optional, Tuple


# (list of lowercase substrings to match, target type name)
_MODEL_RULES: List[Tuple[List[str], str]] = [
    # Audio — first because AirPods names contain "Charging Case"
    (
        [
            "airpods", "earpods", " buds", "ear (", "ear a)",
            "headset", "headphone", "casque", "écouteur", "écouteurs",
            "earphone", "earphones",
            "boombox", "enceinte", "speaker", "soundbar",
            "nest audio", "nest mini", "home mini",
            "link portable", "live pro",
            "live 66", "live 67", "live 77",
            "tune 51", "tune 52", "tune 57", "tune 67", "tune 76", "tune 77",
            "tour one", "charge 5", "charge 6", "flip 7", "flip 6",
        ],
        "Audio",
    ),
    # Montre
    (
        ["watch", "galaxy watch", "gear s3", "gear s4", "band fit", "smartwatch"],
        "Montre",
    ),
    # Tablette
    (
        ["ipad", "galaxy tab", " tab s", " tab a ", "mediapad", "matepad",
         "surface pro", "surface go"],
        "Tablette",
    ),
    # Smart home Google → Accessoire
    (
        ["nest cam", "nest doorbell", "nest wifi", "nest pro wifi",
         "nest hub", "google home"],
        "Accessoire",
    ),
    # Câble
    (
        ["câble usb", "cable usb", "usb-c to", "usb-c/usb-c",
         "usb a/lightning", "usb c/usb c", "lightning to usb",
         "thunderbolt cable", "me291", "muqw3", "mu2g3"],
        "Câble",
    ),
    # Chargeur / alimentation
    (
        ["adapter", "adaptateur", "chargeur", "charger", "charging combo",
         "magsafe", "power bank", "powerbank", "power adapter",
         "fast charge adapter", "turbo charging power",
         "ep-ta", "ep-t25", "bnb"],
        "Chargeur",
    ),
    # Accessoire (coques, verres, accessoires divers)
    (
        ["coque", "clear case", "verre trempé", "tempered glass",
         "protection à rabat", "housse", " tpu ", "airtag"],
        "Accessoire",
    ),
    # Smartphone — le plus générique, en dernier
    (
        ["iphone", " ds ", "dual sim", "dualsim",
         "pixel 6", "pixel 7", "pixel 8", "pixel 9", "pixel 10",
         "nothing phone"],
        "Smartphone",
    ),
]

# Brand-level fallback when no model keyword matched
_BRAND_FALLBACK: Dict[str, str] = {
    "JBL": "Audio",
    "Hotwav": "Smartphone",
    "Honor": "Smartphone",
    "Nokia": "Smartphone",
    "Redmi": "Smartphone",
}


def classify_device_type(model: Optional[str], brand: Optional[str]) -> Optional[str]:
    """Return a device type name for the given product, or None if unclassified."""
    model_lower = (model or "").lower()

    for patterns, type_name in _MODEL_RULES:
        for pattern in patterns:
            if pattern in model_lower:
                return type_name

    if brand and brand in _BRAND_FALLBACK:
        return _BRAND_FALLBACK[brand]

    return None


def dry_run_classification(
    products: list,
) -> Tuple[List[Dict], List[Dict]]:
    """Classify a list of Product ORM objects.

    Returns (classified, unclassified) where each item is a dict with
    product_id, model, brand, new_type.
    """
    classified: List[Dict] = []
    unclassified: List[Dict] = []

    for product in products:
        brand = product.brand.brand if product.brand else None
        new_type = classify_device_type(product.model, brand)
        entry = {
            "product_id": product.id,
            "model": product.model,
            "brand": brand,
        }
        if new_type:
            classified.append({**entry, "new_type": new_type})
        else:
            unclassified.append(entry)

    return classified, unclassified
