"""LLM-based product matching module.

Extracts structured attributes from supplier labels using Claude Haiku,
then scores them against the product referential to create matches.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app
from sqlalchemy import func

from utils.normalize import normalize_storage
from models import (
    Brand,
    Color,
    ColorTranslation,
    DeviceType,
    LabelCache,
    MemoryOption,
    ModelReference,
    PendingMatch,
    Product,
    ProductCalculation,
    Supplier,
    SupplierProductRef,
    SupplierCatalog,
    db,
)


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _get_env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Function 1: normalize_label
# ---------------------------------------------------------------------------

def normalize_label(label: str) -> str:
    """Normalize a supplier label for cache key usage.

    Lowercase, strip special characters, reduce multiple spaces.
    Example: 'Apple iPhone 15 128GB - Black' -> 'apple iphone 15 128gb black'
    """
    text = label.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# Function 2: build_context
# ---------------------------------------------------------------------------

def build_context() -> Dict[str, Any]:
    """Load reference data from the database for LLM prompt injection."""
    brands = [b.brand for b in Brand.query.all()]

    colors_raw = Color.query.all()
    translations = ColorTranslation.query.all()
    color_synonyms: Dict[str, List[str]] = {}
    for c in colors_raw:
        color_synonyms[c.color] = []
    for t in translations:
        target = t.color_target
        if target not in color_synonyms:
            color_synonyms[target] = []
        color_synonyms[target].append(t.color_source)

    storage_options = [m.memory for m in MemoryOption.query.all()]

    model_refs = ModelReference.query.all()
    model_reference_map = {r.manufacturer_code: r.commercial_name for r in model_refs}

    device_types = [d.type for d in DeviceType.query.all()]

    return {
        "brands": brands,
        "colors": color_synonyms,
        "storage_options": storage_options,
        "model_references": model_reference_map,
        "device_types": device_types,
    }


# ---------------------------------------------------------------------------
# Function 3: build_extraction_prompt + call_llm_extraction
# ---------------------------------------------------------------------------

def build_extraction_prompt(context: Dict[str, Any]) -> str:
    """Build the system prompt for LLM extraction with injected references."""
    brands_str = ", ".join(context["brands"])

    colors_lines = []
    for color, synonyms in context["colors"].items():
        if synonyms:
            colors_lines.append(f"  {color} : {', '.join(synonyms)}")
        else:
            colors_lines.append(f"  {color}")
    colors_str = "\n".join(colors_lines)

    storage_str = ", ".join(context["storage_options"])

    refs_lines = [
        f"  {code} -> {name}"
        for code, name in context["model_references"].items()
    ]
    refs_str = "\n".join(refs_lines)

    types_str = ", ".join(context["device_types"])

    return f"""Tu es un expert en identification de produits electroniques (smartphones, \
tablettes, accessoires, audio). A partir de chaque libelle fournisseur, \
extrais les attributs structures.

MARQUES CONNUES : {brands_str}

COULEURS CONNUES (nom francais -> synonymes acceptes) :
{colors_str}

STOCKAGES CONNUS : {storage_str}

CORRESPONDANCES CODES CONSTRUCTEUR :
{refs_str}

TYPES D'APPAREILS : {types_str}

REGLES D'EXTRACTION :
1. brand : identifie la marque parmi les marques connues
2. model_family : le nom commercial du modele SANS la marque, le stockage \
ni la couleur. Ex: "iPhone 15 Pro Max", "Galaxy S25 Ultra", "AirPods 4 ANC"
   - Si un code constructeur Samsung est present (S938B, A566B...), \
utilise la table de correspondance
3. storage : capacite de stockage en "Go" (128GB -> "128 Go"). null si absent
4. color : normalise en francais en utilisant les synonymes fournis. \
Si la couleur n est dans aucun synonyme, garde le nom original
5. device_type : Smartphone, Tablette, Accessoire, Audio, etc.
6. region : "EU" si standard EU. "US" si US Spec, "IN" si Indian Spec, \
"DE" si (DE), etc.
7. connectivity : "WiFi" si [W], "Cellular" si mention cellular/LTE, \
"5G" si mentionne, null sinon
8. grade : A, B, C si mentionne, null sinon
9. confidence : score entre 0.0 et 1.0

Reponds UNIQUEMENT avec un JSON array, sans markdown ni texte autour.
Un objet par libelle, dans le meme ordre que les entrees."""


def _build_user_message(labels: List[str]) -> str:
    """Build the user message listing labels to extract."""
    lines = [f"{i + 1}. {label}" for i, label in enumerate(labels)]
    return f"Extrais les attributs de ces {len(labels)} libelles :\n" + "\n".join(lines)


def call_llm_extraction(
    labels: List[str], context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Call Claude Haiku to extract attributes from supplier labels.

    Retries up to 2 times on failure. Falls back to splitting the batch
    if JSON parsing fails.
    """
    import anthropic

    client = anthropic.Anthropic()
    model = os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")
    system_prompt = build_extraction_prompt(context)
    user_message = _build_user_message(labels)

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            raw_text = response.content[0].text.strip()
            # Strip markdown fences if present
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)

            results = json.loads(raw_text)
            if not isinstance(results, list):
                raise ValueError("LLM response is not a JSON array")

            usage = getattr(response, "usage", None)
            token_info = {}
            if usage:
                token_info = {
                    "input_tokens": getattr(usage, "input_tokens", 0),
                    "output_tokens": getattr(usage, "output_tokens", 0),
                }

            for item in results:
                item["_token_info"] = token_info

            return results

        except json.JSONDecodeError:
            if attempt < max_retries and len(labels) > 1:
                mid = len(labels) // 2
                left = call_llm_extraction(labels[:mid], context)
                right = call_llm_extraction(labels[mid:], context)
                return left + right
            raise
        except anthropic.AuthenticationError:
            raise RuntimeError(
                "Cle API Anthropic invalide ou manquante"
            )
        except anthropic.RateLimitError:
            if attempt < max_retries:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(
                "Limite de requetes Anthropic atteinte, "
                "reessayez dans quelques minutes"
            )
        except anthropic.APIConnectionError:
            if attempt < max_retries:
                time.sleep(1 * (attempt + 1))
                continue
            raise RuntimeError(
                "Impossible de contacter l'API Anthropic "
                "(verifiez la connexion reseau)"
            )
        except anthropic.APIStatusError as exc:
            if attempt < max_retries:
                time.sleep(1 * (attempt + 1))
                continue
            raise RuntimeError(
                f"Erreur API Anthropic (code {exc.status_code})"
            )
        except Exception:
            if attempt < max_retries:
                time.sleep(1 * (attempt + 1))
                continue
            raise


# ---------------------------------------------------------------------------
# Function 4: score_match
# ---------------------------------------------------------------------------

def _normalize_storage(value: Optional[str]) -> Optional[str]:
    """Normalize storage strings for comparison.

    Handles units: '512 Go', '512GB' -> '512'; '1 To', '1TB' -> '1024'.
    Requires an explicit unit suffix so model version numbers are not mistaken
    for storage values (e.g. 'iPhone 17' → no match).
    """
    if not value:
        return None
    m = re.search(r'\b(\d+)\s*(tb|to|gb|go)\b', value.lower())
    if m:
        num, unit = int(m.group(1)), m.group(2)
        return str(num * 1024) if unit in ('tb', 'to') else str(num)
    return None


def _fuzzy_ratio(a: str, b: str) -> float:
    """Return similarity ratio between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# Device types that carry no category information — skip disqualification
_DEVICE_TYPE_SKIP: set[str] = {"all", "a définir", "a definir"}

# Synonyms to normalize before comparison
_DEVICE_TYPE_SYNONYMS: Dict[str, str] = {
    "téléphone": "smartphone",
    "telephone": "smartphone",
}


def _normalize_device_type(value: str) -> str:
    normalized = value.strip().lower()
    return _DEVICE_TYPE_SYNONYMS.get(normalized, normalized)


def score_match(
    extracted: Dict[str, Any],
    product: Product,
    mappings: Dict[str, Any],
) -> Tuple[int, Dict[str, Any]]:
    """Score a match between extracted attributes and a product.

    Returns (score, details) where score is 0-100.
    Brand or storage mismatch -> 0.
    """
    details: Dict[str, Any] = {}
    score = 0

    # --- Brand (hard disqualifier if both sides have a brand and they differ) ---
    ext_brand = (extracted.get("brand") or "").strip().lower()
    prod_brand = (product.brand.brand if product.brand else "").lower()
    if ext_brand and prod_brand:
        if ext_brand != prod_brand:
            details["brand"] = 0
            details["disqualified"] = "brand_mismatch"
            return 0, details
        details["brand"] = 15
        score += 15
    else:
        details["brand"] = 0

    # --- Device type (hard disqualifier if both sides have a meaningful type) ---
    ext_type = _normalize_device_type(extracted.get("device_type") or "")
    prod_type_raw = (product.type.type if product.type else "").strip().lower()
    if prod_type_raw not in _DEVICE_TYPE_SKIP:
        prod_type = _normalize_device_type(prod_type_raw)
        if ext_type and prod_type and _fuzzy_ratio(ext_type, prod_type) < 0.6:
            details["device_type"] = 0
            details["disqualified"] = "device_type_mismatch"
            return 0, details

    # --- Storage (25 pts) ---
    ext_storage = _normalize_storage(extracted.get("storage"))
    # Use official memory field first, fall back to model name
    prod_storage = _normalize_storage(product.memory.memory if product.memory else None)
    if prod_storage is None and product.model:
        prod_storage = _normalize_storage(product.model)

    if ext_storage and prod_storage:
        # Both sides have storage → hard disqualifier on mismatch
        if ext_storage == prod_storage:
            details["storage"] = 25
            score += 25
        else:
            details["storage"] = 0
            details["disqualified"] = "storage_mismatch"
            return 0, details
    elif ext_storage or prod_storage:
        # Only one side has storage → 0 pts, no disqualify
        details["storage"] = 0
    else:
        # Neither side has storage → assume OK
        details["storage"] = 25
        score += 25

    # --- Model family (40 pts) ---
    ext_model = (extracted.get("model_family") or "").strip().lower()
    prod_model = (product.model or "").strip().lower()
    # Remove brand from product model for comparison
    if prod_brand and prod_model.startswith(prod_brand):
        prod_model = prod_model[len(prod_brand):].strip()

    if ext_model and prod_model:
        # Hard disqualifier: same model name structure but different version number
        # e.g. "iphone 16" vs "iphone 15", "galaxy s25" vs "galaxy s24"
        ext_ver = re.search(r'\d+', ext_model)
        prod_ver = re.search(r'\d+', prod_model)
        if ext_ver and prod_ver and ext_ver.group() != prod_ver.group():
            details["model_family"] = 0
            details["disqualified"] = "model_version_mismatch"
            return 0, details

        ratio = _fuzzy_ratio(ext_model, prod_model)
        if ratio >= 0.95:
            details["model_family"] = 40
            score += 40
        elif ratio >= 0.8:
            pts = int(20 + (ratio - 0.8) * 100)
            details["model_family"] = min(pts, 35)
            score += details["model_family"]
        elif ratio >= 0.6:
            details["model_family"] = int(ratio * 20)
            score += details["model_family"]
        else:
            details["model_family"] = 0
    elif not ext_model:
        details["model_family"] = 0
    else:
        details["model_family"] = 0

    # --- Color (hard disqualifier if both sides have a color and they differ) ---
    ext_color = (extracted.get("color") or "").strip().lower()
    prod_color = (product.color.color if product.color else "").lower()
    color_translations = mappings.get("color_translations", {})

    if ext_color and prod_color:
        normalized_ext = color_translations.get(ext_color, ext_color).lower()
        if normalized_ext == prod_color or ext_color == prod_color:
            details["color"] = 15
            score += 15
        else:
            details["color"] = 0
            details["disqualified"] = "color_mismatch"
            return 0, details
    elif not ext_color and not prod_color:
        details["color"] = 15
        score += 15
    else:
        details["color"] = 0

    # --- Region (hard disqualifier; null or empty = EU) ---
    ext_region = (extracted.get("region") or "EU").strip().upper()
    prod_region = (product.region or "EU").strip().upper()
    if ext_region == prod_region:
        details["region"] = 5
        score += 5
    else:
        details["region"] = 0
        details["disqualified"] = "region_mismatch"
        return 0, details

    # --- Label similarity bonus/malus (up to ±10 pts) ---
    raw_label = (extracted.get("raw_label") or "").strip()
    if raw_label and product.model:
        ratio = _fuzzy_ratio(normalize_label(raw_label), normalize_label(product.model))
        if ratio >= 0.80:
            details["label_similarity"] = 10
            score += 10
        elif ratio >= 0.60:
            details["label_similarity"] = 5
            score += 5
        elif ratio < 0.25:
            details["label_similarity"] = -10
            score = max(score - 10, 0)
        else:
            details["label_similarity"] = 0
    else:
        details["label_similarity"] = 0

    return min(max(score, 0), 100), details


# ---------------------------------------------------------------------------
# Function 5: find_best_matches
# ---------------------------------------------------------------------------

def _build_mappings() -> Dict[str, Any]:
    """Build lookup mappings for scoring."""
    translations = ColorTranslation.query.all()
    color_map = {t.color_source.lower(): t.color_target for t in translations}
    return {"color_translations": color_map}


def find_best_matches(
    extracted: Dict[str, Any],
    products: List[Product],
    mappings: Dict[str, Any],
    top_n: int = 3,
) -> List[Dict[str, Any]]:
    """Find the best matching products for extracted attributes.

    Pre-filters by brand_id, then scores all candidates.
    Returns top_n results sorted by score descending.
    """
    ext_brand = (extracted.get("brand") or "").strip().lower()

    # Pre-filter by brand
    brand = Brand.query.filter(func.lower(Brand.brand) == ext_brand).first() if ext_brand else None
    if brand:
        candidates = [p for p in products if p.brand_id == brand.id]
    else:
        candidates = products

    scored: List[Tuple[int, Dict[str, Any], Product]] = []
    for product in candidates:
        match_score, details = score_match(extracted, product, mappings)
        if match_score > 0:
            scored.append((match_score, details, product))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for match_score, details, product in scored[:top_n]:
        parts = [product.model or product.description or f"Product #{product.id}"]
        if product.memory:
            parts.append(product.memory.memory)
        if product.color:
            parts.append(product.color.color)
        results.append({
            "product_id": product.id,
            "score": match_score,
            "product_name": " — ".join(parts),
            "details": details,
        })

    return results


# ---------------------------------------------------------------------------
# Function 6: create_product_from_extraction
# ---------------------------------------------------------------------------

def _find_or_create_brand(name: str) -> Optional[int]:
    """Find brand by name (case-insensitive) or create it."""
    if not name:
        return None
    brand = Brand.query.filter(func.lower(Brand.brand) == name.lower()).first()
    if brand:
        return brand.id
    brand = Brand(brand=name)
    db.session.add(brand)
    db.session.flush()
    return brand.id


def _find_or_create_memory(storage: str) -> Optional[int]:
    """Find memory option or create it."""
    if not storage:
        return None
    normalized = normalize_storage(storage) or storage.strip()
    mem = MemoryOption.query.filter(
        func.lower(MemoryOption.memory) == normalized.lower()
    ).first()
    if mem:
        return mem.id
    # Extract numeric value for tcp_value
    digits = re.sub(r"[^\d]", "", normalized)
    tcp_val = int(digits) if digits else 0
    mem = MemoryOption(memory=normalized, tcp_value=tcp_val)
    db.session.add(mem)
    db.session.flush()
    return mem.id


def _find_color_id(color_name: str) -> Optional[int]:
    """Find color by name or via translations."""
    if not color_name:
        return None
    color = Color.query.filter(func.lower(Color.color) == color_name.lower()).first()
    if color:
        return color.id
    translation = ColorTranslation.query.filter(
        func.lower(ColorTranslation.color_source) == color_name.lower()
    ).first()
    if translation:
        return translation.color_target_id
    # Create new color
    color = Color(color=color_name)
    db.session.add(color)
    db.session.flush()
    return color.id


def _find_device_type_id(type_name: str) -> Optional[int]:
    """Find device type by name or create it."""
    if not type_name:
        return None
    dt = DeviceType.query.filter(
        func.lower(DeviceType.type) == type_name.lower()
    ).first()
    if dt:
        return dt.id
    dt = DeviceType(type=type_name)
    db.session.add(dt)
    db.session.flush()
    return dt.id


def create_product_from_extraction(
    extracted: Dict[str, Any], source_label: str
) -> Product:
    """Create a new product in the referential from LLM-extracted attributes."""
    product = Product(
        model=extracted.get("model_family"),
        description=f"[AUTO] {source_label}",
        brand_id=_find_or_create_brand(extracted.get("brand", "")),
        memory_id=_find_or_create_memory(extracted.get("storage", "")),
        color_id=_find_color_id(extracted.get("color", "")),
        type_id=_find_device_type_id(extracted.get("device_type", "")),
        region=extracted.get("region"),
    )
    db.session.add(product)
    db.session.flush()
    return product


# ---------------------------------------------------------------------------
# Function 7: run_matching_job
# ---------------------------------------------------------------------------

def run_matching_job(
    supplier_id: Optional[int] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Orchestrate the LLM matching process (product-centric direction).

    Phase 1: Extract all unextracted SupplierCatalog labels → LabelCache
             (product_id=None, match_source='extracted').
    Phase 2: For each Odoo Product without SupplierProductRef, score against
             extracted cache entries.
             Score >= 90 → auto-match + SupplierProductRef.
             50-89 → PendingMatch.
             < 50 → not_found (no product created).
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "Cle API Anthropic manquante. "
            "Configurez la variable d'environnement ANTHROPIC_API_KEY."
        )

    start_time = time.time()

    threshold_auto = _get_env_int("MATCH_THRESHOLD_AUTO", 90)
    threshold_review = _get_env_int("MATCH_THRESHOLD_REVIEW", 50)
    batch_size = _get_env_int("LLM_BATCH_SIZE", 25)

    # -----------------------------------------------------------------------
    # Phase 1: Extract unextracted SupplierCatalog labels → LabelCache
    # -----------------------------------------------------------------------
    catalog_query = SupplierCatalog.query
    if supplier_id:
        catalog_query = catalog_query.filter_by(supplier_id=supplier_id)
    all_catalogs = catalog_query.all()

    # Build (supplier_id, normalized_label) → [SupplierCatalog entries]
    label_to_catalogs: Dict[Tuple[int, str], List[SupplierCatalog]] = {}
    for ti in all_catalogs:
        label = ti.description or ti.model or ""
        normalized = normalize_label(label)
        if normalized and ti.supplier_id:
            key = (ti.supplier_id, normalized)
            label_to_catalogs.setdefault(key, []).append(ti)

    # Determine which labels need LLM extraction.
    # Also re-extract entries where product_id=None AND extracted_attributes=None:
    # these were created by an older code path that didn't save LLM output, leaving
    # Phase 2 with no attributes to score against (score=0 → all products not_found).
    labels_to_extract: List[Tuple[int, str, str]] = []  # (supplier_id, normalized, original)
    for (sid, normalized), catalogs in label_to_catalogs.items():
        cached = LabelCache.query.filter_by(
            supplier_id=sid, normalized_label=normalized
        ).first()
        needs_extraction = (
            not cached
            or (cached.product_id is None and not cached.extracted_attributes)
        )
        if needs_extraction:
            original_label = catalogs[0].description or catalogs[0].model or ""
            labels_to_extract.append((sid, normalized, original_label))

    from_cache = len(label_to_catalogs) - len(labels_to_extract)
    llm_calls = 0
    errors = 0
    error_message: Optional[str] = None
    total_input_tokens = 0
    total_output_tokens = 0

    context = build_context()

    # Batch LLM extraction for Phase 1
    for batch_start in range(0, len(labels_to_extract), batch_size):
        batch_items = labels_to_extract[batch_start:batch_start + batch_size]
        batch_labels = [item[2] for item in batch_items]

        try:
            extractions = call_llm_extraction(batch_labels, context)
            llm_calls += 1
        except Exception as exc:
            current_app.logger.error("LLM extraction Phase 1 failed: %s", exc)
            errors += len(batch_labels)
            if error_message is None:
                error_message = str(exc)
            continue

        for idx, extraction in enumerate(extractions):
            if idx >= len(batch_items):
                break
            sid, normalized, original_label = batch_items[idx]
            token_info = extraction.pop("_token_info", {})
            total_input_tokens += token_info.get("input_tokens", 0) // max(len(batch_labels), 1)
            total_output_tokens += token_info.get("output_tokens", 0) // max(len(batch_labels), 1)
            extraction["raw_label"] = original_label
            _save_extraction_cache(sid, normalized, extraction)

    db.session.flush()

    # -----------------------------------------------------------------------
    # Phase 2: Match Odoo Products against extracted cache entries
    # -----------------------------------------------------------------------
    # Exclude products already matched — either via ETL (ProductCalculation exists)
    # or via previous LLM auto-match (SupplierProductRef exists, ETL not yet re-run).
    # ProductCalculation is the stat definition of "matched"; SPR covers the window
    # where LLM matched a product but the ETL price sync hasn't run yet.
    matched_product_ids: set[int] = {
        row[0]
        for row in db.session.query(ProductCalculation.product_id)
        .filter(ProductCalculation.product_id.isnot(None))
        .distinct()
        .all()
    } | {
        row[0]
        for row in db.session.query(SupplierProductRef.product_id)
        .filter(SupplierProductRef.product_id.isnot(None))
        .distinct()
        .all()
    }

    # Exclude products already queued in a pending or auto-rejected match
    pending_product_ids: set[int] = set()
    for pm in PendingMatch.query.filter(
        PendingMatch.status.in_(["pending", "rejected"])
    ).all():
        for c in pm.candidates or []:
            if c.get("product_id"):
                pending_product_ids.add(c["product_id"])

    all_products_list = Product.query.all()
    products_to_process = [
        p for p in all_products_list
        if p.id not in matched_product_ids and p.id not in pending_product_ids
    ]

    total_unmatched = len(products_to_process)
    if limit is not None and limit > 0:
        products_to_process = products_to_process[:limit]
    remaining = total_unmatched - len(products_to_process)

    # Load extracted cache entries awaiting matching (product_id=None)
    cache_filter_args = [
        LabelCache.match_source == "extracted",
        LabelCache.product_id.is_(None),
    ]
    if supplier_id:
        cache_filter_args.append(LabelCache.supplier_id == supplier_id)
    all_cache_entries = LabelCache.query.filter(*cache_filter_args).all()

    # Pre-build brand → cache entries index for fast filtering
    brand_to_entries: Dict[str, List[LabelCache]] = {}
    for entry in all_cache_entries:
        attrs = entry.extracted_attributes or {}
        brand = (attrs.get("brand") or "").strip().lower()
        brand_to_entries.setdefault(brand, []).append(entry)

    mappings = _build_mappings()
    auto_matched = 0
    pending_review = 0
    auto_rejected = 0
    not_found = 0

    for product in products_to_process:
        prod_brand = (product.brand.brand if product.brand else "").strip().lower()

        # Brand-filtered candidates + no-brand entries as fallback
        if prod_brand:
            candidates_list = (
                brand_to_entries.get(prod_brand, [])
                + brand_to_entries.get("", [])
            )
        else:
            candidates_list = all_cache_entries

        if not candidates_list:
            not_found += 1
            continue

        scored: List[Tuple[int, Dict, LabelCache]] = []
        best_disqualified: Optional[Tuple[Dict, LabelCache]] = None

        for cache_entry in candidates_list:
            attrs = dict(cache_entry.extracted_attributes or {})
            score, details = score_match(attrs, product, mappings)
            if score > 0:
                scored.append((score, details, cache_entry))
            elif best_disqualified is None and details.get("disqualified"):
                best_disqualified = (details, cache_entry)

        if not scored:
            if best_disqualified is not None:
                # All candidates triggered a hard disqualifier → auto-reject
                disq_details, disq_entry = best_disqualified
                original_label = (
                    (disq_entry.extracted_attributes or {}).get("raw_label")
                    or disq_entry.normalized_label
                )
                product_name = " — ".join(filter(None, [
                    product.model or product.description,
                    product.memory.memory if product.memory else None,
                    product.color.color if product.color else None,
                ]))
                pm = PendingMatch(
                    supplier_id=disq_entry.supplier_id,
                    temporary_import_id=None,
                    source_label=original_label,
                    extracted_attributes=disq_entry.extracted_attributes or {},
                    candidates=[{
                        "product_id": product.id,
                        "score": 0,
                        "product_name": product_name,
                        "details": disq_details,
                    }],
                    status="rejected",
                )
                db.session.add(pm)
                auto_rejected += 1
            else:
                not_found += 1
            continue

        scored.sort(key=lambda x: x[0], reverse=True)
        top_score, top_details, top_cache = scored[0]

        if top_score >= threshold_auto:
            catalog_entries = label_to_catalogs.get(
                (top_cache.supplier_id, top_cache.normalized_label), []
            )
            for ti in catalog_entries:
                _create_supplier_ref(ti.supplier_id, ti, product.id)
            top_cache.product_id = product.id
            top_cache.match_score = top_score
            top_cache.match_source = "auto"
            top_cache.last_used_at = datetime.now(timezone.utc)
            auto_matched += 1

        elif top_score >= threshold_review:
            catalog_entries = label_to_catalogs.get(
                (top_cache.supplier_id, top_cache.normalized_label), []
            )
            first_catalog = catalog_entries[0] if catalog_entries else None
            original_label = (
                (top_cache.extracted_attributes or {}).get("raw_label")
                or top_cache.normalized_label
            )
            product_name = " — ".join(filter(None, [
                product.model or product.description,
                product.memory.memory if product.memory else None,
                product.color.color if product.color else None,
            ]))
            pm = PendingMatch(
                supplier_id=top_cache.supplier_id,
                temporary_import_id=first_catalog.id if first_catalog else None,
                source_label=original_label,
                extracted_attributes=top_cache.extracted_attributes or {},
                candidates=[{
                    "product_id": product.id,
                    "score": top_score,
                    "product_name": product_name,
                    "details": top_details,
                }],
                status="pending",
            )
            db.session.add(pm)
            pending_review += 1

        else:
            not_found += 1

    db.session.commit()

    # Cost estimation (Haiku pricing: ~$0.25/MTok input, ~$1.25/MTok output)
    cost_estimate = round(
        (total_input_tokens * 0.25 + total_output_tokens * 1.25) / 1_000_000, 4
    )

    duration = round(time.time() - start_time, 2)

    return {
        "total_products": len(products_to_process),
        "from_cache": from_cache,
        "llm_calls": llm_calls,
        "auto_matched": auto_matched,
        "pending_review": pending_review,
        "auto_rejected": auto_rejected,
        "not_found": not_found,
        "errors": errors,
        "error_message": error_message,
        "cost_estimate": cost_estimate,
        "duration_seconds": duration,
        "remaining": remaining,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_extraction_cache(
    supplier_id: int,
    normalized_label: str,
    extracted: Dict[str, Any],
) -> None:
    """Save extracted attributes without product_id (pre-matching phase)."""
    existing = LabelCache.query.filter_by(
        supplier_id=supplier_id, normalized_label=normalized_label
    ).first()
    if existing:
        existing.extracted_attributes = extracted
        existing.last_used_at = datetime.now(timezone.utc)
    else:
        cache = LabelCache(
            supplier_id=supplier_id,
            normalized_label=normalized_label,
            product_id=None,
            match_score=None,
            match_source="extracted",
            extracted_attributes=extracted,
        )
        db.session.add(cache)


def _create_supplier_ref(
    supplier_id: int, ti: SupplierCatalog, product_id: int
) -> None:
    """Create a SupplierProductRef if it doesn't already exist."""
    existing = SupplierProductRef.query.filter_by(
        supplier_id=supplier_id,
        ean=ti.ean,
        part_number=ti.part_number,
        supplier_sku=ti.supplier_sku,
    ).first()
    if existing:
        existing.product_id = product_id
        existing.last_seen_at = datetime.now(timezone.utc)
    else:
        ref = SupplierProductRef(
            supplier_id=supplier_id,
            product_id=product_id,
            ean=ti.ean,
            part_number=ti.part_number,
            supplier_sku=ti.supplier_sku,
            last_seen_at=datetime.now(timezone.utc),
        )
        db.session.add(ref)


def _save_cache(
    supplier_id: int,
    normalized_label: str,
    product_id: int,
    score: int,
    source: str,
    extracted: Dict[str, Any],
) -> None:
    """Save a matching result in the label cache."""
    cache = LabelCache(
        supplier_id=supplier_id,
        normalized_label=normalized_label,
        product_id=product_id,
        match_score=score,
        match_source=source,
        extracted_attributes=extracted,
    )
    db.session.add(cache)
