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
6. region : null si standard EU. "US" si US Spec, "IN" si Indian Spec, \
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
    """Normalize storage strings for comparison: '128 Go', '128GB' -> '128'."""
    if not value:
        return None
    digits = re.sub(r"[^\d]", "", value)
    return digits if digits else None


def _fuzzy_ratio(a: str, b: str) -> float:
    """Return similarity ratio between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


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

    # --- Brand (15 pts) ---
    ext_brand = (extracted.get("brand") or "").strip().lower()
    prod_brand = (product.brand.brand if product.brand else "").lower()
    if not ext_brand or not prod_brand or ext_brand != prod_brand:
        details["brand"] = 0
        details["disqualified"] = "brand_mismatch"
        return 0, details
    details["brand"] = 15
    score += 15

    # --- Storage (25 pts) ---
    ext_storage = _normalize_storage(extracted.get("storage"))
    prod_storage = _normalize_storage(product.memory.memory if product.memory else None)
    if ext_storage and prod_storage:
        if ext_storage == prod_storage:
            details["storage"] = 25
            score += 25
        else:
            details["storage"] = 0
            details["disqualified"] = "storage_mismatch"
            return 0, details
    elif ext_storage and not prod_storage:
        details["storage"] = 0
    elif not ext_storage and prod_storage:
        details["storage"] = 0
    else:
        details["storage"] = 25
        score += 25

    # --- Model family (40 pts) ---
    ext_model = (extracted.get("model_family") or "").strip().lower()
    prod_model = (product.model or "").strip().lower()
    # Remove brand from product model for comparison
    if prod_brand and prod_model.startswith(prod_brand):
        prod_model = prod_model[len(prod_brand):].strip()

    if ext_model and prod_model:
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

    # --- Color (15 pts) ---
    ext_color = (extracted.get("color") or "").strip().lower()
    prod_color = (product.color.color if product.color else "").lower()
    color_translations = mappings.get("color_translations", {})

    if ext_color and prod_color:
        if ext_color == prod_color:
            details["color"] = 15
            score += 15
        elif color_translations.get(ext_color, "").lower() == prod_color:
            details["color"] = 15
            score += 15
        else:
            details["color"] = 0
            score -= 5
    elif not ext_color and not prod_color:
        details["color"] = 15
        score += 15
    else:
        details["color"] = 0

    # --- Region (5 pts) ---
    ext_region = extracted.get("region")
    prod_region = product.region
    if ext_region == prod_region:
        details["region"] = 5
        score += 5
    else:
        details["region"] = 0

    return max(score, 0), details


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
        results.append({
            "product_id": product.id,
            "score": match_score,
            "product_name": product.model or product.description or f"Product #{product.id}",
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
    """Orchestrate the full LLM matching process.

    1. Load unmatched SupplierCatalogs (no SupplierProductRef)
    2. Deduplicate labels, check LabelCache
    3. Batch LLM extraction (25/call)
    4. Score >= 90 -> auto-match
    5. Score 50-89 -> PendingMatch
    6. Score < 50 -> create Product
    7. Return report
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

    # Step 1: Load unmatched temporary imports
    query = SupplierCatalog.query
    if supplier_id:
        query = query.filter_by(supplier_id=supplier_id)

    all_temp_imports = query.all()

    # Find which temp imports already have a SupplierProductRef.
    # Use the same (supplier_id, ean, part_number) key as _create_supplier_ref so that
    # items matched by part_number (ean=None) are also detected as already processed.
    # Python set handles None correctly: (1, None, "X") == (1, None, "X") → True.
    matched_keys: set[tuple] = set()
    if all_temp_imports:
        supplier_ids = {ti.supplier_id for ti in all_temp_imports if ti.supplier_id}
        for sid in supplier_ids:
            refs = SupplierProductRef.query.filter_by(supplier_id=sid).filter(
                SupplierProductRef.product_id.isnot(None)
            ).all()
            for ref in refs:
                matched_keys.add((sid, ref.ean, ref.part_number))

    # Load IDs of catalog entries that already have a pending PendingMatch
    # to avoid re-queuing them and creating duplicates
    existing_pending_ids: set[int] = {
        pm.temporary_import_id
        for pm in PendingMatch.query.filter_by(status="pending").all()
        if pm.temporary_import_id is not None
    }

    unmatched = []
    for ti in all_temp_imports:
        if (ti.supplier_id, ti.ean, ti.part_number) in matched_keys:
            continue
        if ti.id in existing_pending_ids:
            continue
        if ti.description or ti.model:
            unmatched.append(ti)

    # Step 2: Deduplicate labels and check cache
    label_to_imports: Dict[str, List[SupplierCatalog]] = {}
    for ti in unmatched:
        label = ti.description or ti.model or ""
        normalized = normalize_label(label)
        if normalized:
            label_to_imports.setdefault(normalized, []).append(ti)

    from_cache = 0
    auto_matched = 0
    pending_review = 0
    auto_created = 0
    errors = 0
    error_message: Optional[str] = None
    total_input_tokens = 0
    total_output_tokens = 0
    labels_to_extract: List[Tuple[str, str, List[SupplierCatalog]]] = []

    # Check cache
    for normalized, temp_imports in label_to_imports.items():
        first_ti = temp_imports[0]
        sid = first_ti.supplier_id
        if not sid:
            continue

        cached = LabelCache.query.filter_by(
            supplier_id=sid, normalized_label=normalized
        ).first()

        if cached:
            cached.last_used_at = datetime.now(timezone.utc)
            from_cache += 1
            if cached.product_id:
                # Create SupplierProductRef for all matching imports
                for ti in temp_imports:
                    _create_supplier_ref(sid, ti, cached.product_id)
                auto_matched += 1
        else:
            original_label = first_ti.description or first_ti.model or ""
            labels_to_extract.append((normalized, original_label, temp_imports))

    # Apply limit to labels_to_extract (batching)
    total_to_extract = len(labels_to_extract)
    if limit is not None and limit > 0 and len(labels_to_extract) > limit:
        labels_to_extract = labels_to_extract[:limit]
    remaining = total_to_extract - len(labels_to_extract)

    # Step 3: Load products for scoring
    all_products = Product.query.all()
    mappings = _build_mappings()
    context = build_context()

    # Step 4: Batch LLM extraction
    llm_calls = 0
    original_labels = [item[1] for item in labels_to_extract]

    for batch_start in range(0, len(original_labels), batch_size):
        batch_labels = original_labels[batch_start:batch_start + batch_size]
        batch_items = labels_to_extract[batch_start:batch_start + batch_size]

        try:
            extractions = call_llm_extraction(batch_labels, context)
            llm_calls += 1
        except Exception as exc:
            current_app.logger.error("LLM extraction failed: %s", exc)
            errors += len(batch_labels)
            if error_message is None:
                error_message = str(exc)
            continue

        # Process each extraction
        for idx, extraction in enumerate(extractions):
            if idx >= len(batch_items):
                break

            normalized, original_label, temp_imports = batch_items[idx]
            first_ti = temp_imports[0]
            sid = first_ti.supplier_id
            if not sid:
                continue

            # Track token usage
            token_info = extraction.pop("_token_info", {})
            total_input_tokens += token_info.get("input_tokens", 0) // max(len(batch_labels), 1)
            total_output_tokens += token_info.get("output_tokens", 0) // max(len(batch_labels), 1)

            # Step 5: Score against referential
            best = find_best_matches(extraction, all_products, mappings, top_n=3)
            top_score = best[0]["score"] if best else 0

            if top_score >= threshold_auto:
                # Auto-match
                product_id = best[0]["product_id"]
                for ti in temp_imports:
                    _create_supplier_ref(sid, ti, product_id)
                _save_cache(sid, normalized, product_id, top_score, "auto", extraction)
                auto_matched += 1

            elif top_score >= threshold_review:
                # Pending review
                pm = PendingMatch(
                    supplier_id=sid,
                    temporary_import_id=first_ti.id,
                    source_label=original_label,
                    extracted_attributes=extraction,
                    candidates=best,
                    status="pending",
                )
                db.session.add(pm)
                pending_review += 1

            else:
                # Create new product
                product = create_product_from_extraction(extraction, original_label)
                for ti in temp_imports:
                    _create_supplier_ref(sid, ti, product.id)
                _save_cache(sid, normalized, product.id, top_score, "auto", extraction)
                auto_created += 1

    db.session.commit()

    # Cost estimation (Haiku pricing: ~$0.25/MTok input, ~$1.25/MTok output)
    cost_estimate = round(
        (total_input_tokens * 0.25 + total_output_tokens * 1.25) / 1_000_000, 4
    )

    duration = round(time.time() - start_time, 2)

    return {
        "total_labels": len(label_to_imports),
        "from_cache": from_cache,
        "llm_calls": llm_calls,
        "auto_matched": auto_matched,
        "pending_review": pending_review,
        "auto_created": auto_created,
        "errors": errors,
        "error_message": error_message,
        "cost_estimate": cost_estimate,
        "duration_seconds": duration,
        "remaining": remaining,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_supplier_ref(
    supplier_id: int, ti: SupplierCatalog, product_id: int
) -> None:
    """Create a SupplierProductRef if it doesn't already exist."""
    existing = SupplierProductRef.query.filter_by(
        supplier_id=supplier_id,
        ean=ti.ean,
        part_number=ti.part_number,
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
