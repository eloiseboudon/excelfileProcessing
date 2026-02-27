"""Odoo XML-RPC client and product synchronization engine."""

from __future__ import annotations

import logging
import re
import xmlrpc.client
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from utils.normalize import normalize_description_units, normalize_ram, normalize_storage
from models import (
    Brand,
    Color,
    ColorTranslation,
    DeviceType,
    InternalProduct,
    MemoryOption,
    NormeOption,
    OdooConfig,
    OdooSyncJob,
    PendingMatch,
    Product,
    ProductCalculation,
    RAMOption,
    SupplierProductRef,
    db,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Attribute classification map (case-insensitive)
# Maps Odoo attribute names to AJT PRO reference fields.
# ---------------------------------------------------------------------------
ATTRIBUTE_MAP: Dict[str, str] = {
    "couleur": "color",
    "color": "color",
    "colour": "color",
    "memoire": "memory",
    "memory": "memory",
    "stockage": "memory",
    "storage": "memory",
    "ram": "ram",
    "norme": "norme",
    "grade": "norme",
    "qualite": "norme",
}

BATCH_SIZE = 200
MAX_REPORT_ITEMS = 10_000


# ---------------------------------------------------------------------------
# XML-RPC transports with timeout
# ---------------------------------------------------------------------------
XMLRPC_TIMEOUT = 60


class _TimeoutTransport(xmlrpc.client.Transport):
    """XML-RPC HTTP transport with configurable timeout."""

    def __init__(self, timeout=XMLRPC_TIMEOUT, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout = timeout

    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self.timeout
        return conn


class _TimeoutSafeTransport(xmlrpc.client.SafeTransport):
    """XML-RPC HTTPS transport with configurable timeout."""

    def __init__(self, timeout=XMLRPC_TIMEOUT, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout = timeout

    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self.timeout
        return conn


# ---------------------------------------------------------------------------
# OdooClient — thin wrapper around xmlrpc.client
# ---------------------------------------------------------------------------
class OdooClient:
    """XML-RPC client for Odoo 17."""

    def __init__(self, url: str, database: str, login: str, password: str):
        self.url = url.rstrip("/")
        self.database = database
        self.login = login
        self.password = password
        self._uid: Optional[int] = None
        use_ssl = self.url.startswith("https")
        transport = (
            _TimeoutSafeTransport() if use_ssl else _TimeoutTransport()
        )
        self._common = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/common", transport=transport
        )
        self._object = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/object", transport=transport
        )

    def authenticate(self) -> int:
        uid = self._common.authenticate(
            self.database, self.login, self.password, {}
        )
        if not uid:
            raise ConnectionError("Authentification Odoo échouée")
        self._uid = uid
        return uid

    def execute_kw(
        self,
        model: str,
        method: str,
        args: list,
        kwargs: Optional[dict] = None,
    ) -> Any:
        if self._uid is None:
            self.authenticate()
        return self._object.execute_kw(
            self.database,
            self._uid,
            self.password,
            model,
            method,
            args,
            kwargs or {},
        )

    def search_read(
        self,
        model: str,
        domain: list,
        fields: list,
        limit: int = 0,
        offset: int = 0,
    ) -> list:
        kwargs: dict = {"fields": fields}
        if limit:
            kwargs["limit"] = limit
        if offset:
            kwargs["offset"] = offset
        return self.execute_kw(model, "search_read", [domain], kwargs)

    def search_count(self, model: str, domain: list) -> int:
        return self.execute_kw(model, "search_count", [domain])

    def test_connection(self) -> dict:
        version_info = self._common.version()
        uid = self.authenticate()
        count = self.search_count("product.product", [["active", "=", True]])
        return {
            "server_version": version_info.get("server_version", "unknown"),
            "uid": uid,
            "product_count": count,
        }


# ---------------------------------------------------------------------------
# Reference lookup helpers
# ---------------------------------------------------------------------------
def _build_lookup(model_cls, attr: str) -> Dict[str, int]:
    """Build a {lowercase_value: id} dict for a reference table."""
    return {
        getattr(row, attr).lower(): row.id
        for row in model_cls.query.all()
        if getattr(row, attr, None)
    }


def _find_or_create(
    model_cls, attr: str, value: str, lookup: Dict[str, int], **extra_kwargs
) -> int:
    """Find a reference row by value or create it. Returns the id."""
    key = value.strip().lower()
    if key in lookup:
        return lookup[key]
    row = model_cls.query.filter(db.func.lower(getattr(model_cls, attr)) == key).first()
    if row:
        lookup[key] = row.id
        return row.id
    new_row = model_cls(**{attr: value.strip()}, **extra_kwargs)
    db.session.add(new_row)
    db.session.flush()
    lookup[key] = new_row.id
    return new_row.id


# ---------------------------------------------------------------------------
# Attribute extraction
# ---------------------------------------------------------------------------
def _classify_attributes(
    attribute_value_ids: List[int],
    attr_values_cache: Dict[int, dict],
) -> Dict[str, str]:
    """Classify product attribute values into color/memory/ram/norme."""
    result: Dict[str, str] = {}
    for av_id in attribute_value_ids:
        av = attr_values_cache.get(av_id)
        if not av:
            continue
        attr_name = (av.get("attribute_id") or [0, ""])[1].lower().strip()
        category = ATTRIBUTE_MAP.get(attr_name)
        if category and category not in result:
            display = av.get("name", "").strip()
            if display:
                result[category] = display
    return result


# ---------------------------------------------------------------------------
# Name-based fallback parsing
# ---------------------------------------------------------------------------
def _parse_name_fallback(
    name: str,
    brand_id: Optional[int],
    color_id: Optional[int],
    memory_id: Optional[int],
    ram_id: Optional[int],
    norme_id: Optional[int],
    type_id: Optional[int],
    brand_lookup: Dict[str, int],
    color_lookup: Dict[str, int],
    color_translation_lookup: Dict[str, int],
    memory_lookup: Dict[str, int],
    ram_lookup: Dict[str, int],
    norme_lookup: Dict[str, int],
    type_lookup: Dict[str, int],
) -> Tuple[dict, List[str]]:
    """Parse product name to extract missing reference fields via substring matching.

    For each field still None, search for a matching key in the corresponding
    lookup dict.  Keys are tried longest-first so that "bleu nuit" matches
    before "bleu" and "128 go" before "128".

    Returns (result_dict, matched_strings) where matched_strings contains the
    lookup keys that were found in the name (used later for model name extraction).
    """
    name_lower = name.lower()
    result: dict = {}
    matched_strings: List[str] = []

    def _find_in(lookup: Dict[str, int]) -> Optional[int]:
        for key in sorted(lookup, key=len, reverse=True):
            # Skip purely numeric keys — too ambiguous in product names
            # (e.g. "12" could be RAM or model number as in "iPhone 12")
            if key.strip().isdigit():
                continue
            if re.search(r"\b" + re.escape(key) + r"\b", name_lower):
                matched_strings.append(key)
                return lookup[key]
        return None

    if brand_id is None:
        result["brand_id"] = _find_in(brand_lookup)
    if color_id is None:
        found = _find_in(color_translation_lookup)
        if found is None:
            found = _find_in(color_lookup)
        result["color_id"] = found
    if memory_id is None:
        result["memory_id"] = _find_in(memory_lookup)
    if ram_id is None:
        # Try to extract RAM from "RAM/StorageGo" pattern (e.g. "8/256Go", "8/256GB")
        ram_match = re.search(r"\b(\d+)/\d+\s*(?:go|gb)\b", name_lower)
        if ram_match:
            ram_key = f"{ram_match.group(1)} go"
            if ram_key in ram_lookup:
                matched_strings.append(ram_key)
                result["ram_id"] = ram_lookup[ram_key]
            else:
                result["ram_id"] = _find_in(ram_lookup)
        else:
            result["ram_id"] = _find_in(ram_lookup)
    if norme_id is None:
        result["norme_id"] = _find_in(norme_lookup)
    if type_id is None:
        result["type_id"] = _find_in(type_lookup)

    return result, matched_strings


def _extract_model_name(name: str, parts_to_remove: List[str]) -> str:
    """Extract the model name by removing brand, color, memory, etc. from the full name.

    Parts are removed longest-first to avoid partial matches (e.g. "128GB" before "128").
    Word boundaries prevent matching inside compound words (e.g. "black" won't match "BlackBerry").
    """
    result = name
    for part in sorted((p for p in parts_to_remove if p), key=len, reverse=True):
        # Skip purely numeric parts — likely model version numbers (e.g. "12" in "iPhone 12")
        if part.strip().isdigit():
            continue
        result = re.sub(
            r"\b" + re.escape(part) + r"\b", "", result, count=1, flags=re.IGNORECASE,
        )
    result = " ".join(result.split()).strip()
    return result if result else name


# ---------------------------------------------------------------------------
# Single product processing
# ---------------------------------------------------------------------------
def _process_single_product(
    odoo_product: dict,
    attr_values_cache: Dict[int, dict],
    brand_lookup: Dict[str, int],
    color_lookup: Dict[str, int],
    memory_lookup: Dict[str, int],
    ram_lookup: Dict[str, int],
    norme_lookup: Dict[str, int],
    type_lookup: Dict[str, int],
    internal_by_odoo_id: Dict[str, InternalProduct],
    product_by_ean: Dict[str, Product],
    product_by_pn: Dict[str, Product],
    color_translation_lookup: Optional[Dict[str, int]] = None,
) -> Tuple[str, dict]:
    """Process a single Odoo product. Returns (status, report_item).

    status: 'created' | 'updated' | 'unchanged' | 'error'
    """
    odoo_id = str(odoo_product["id"])
    name = (odoo_product.get("name") or "").strip()
    barcode = (odoo_product.get("barcode") or "") if odoo_product.get("barcode") else ""
    default_code = (odoo_product.get("default_code") or "") if odoo_product.get("default_code") else ""
    list_price = odoo_product.get("list_price") or 0.0

    report_item = {
        "odoo_id": odoo_id,
        "name": name,
        "ean": barcode,
        "part_number": default_code,
    }

    # Resolve brand from product_brand_id tuple [id, "Name"]
    brand_id = None
    brand_tuple = odoo_product.get("product_brand_id")
    if brand_tuple and isinstance(brand_tuple, (list, tuple)) and len(brand_tuple) == 2:
        brand_name = str(brand_tuple[1]).strip()
        if brand_name:
            brand_id = _find_or_create(Brand, "brand", brand_name, brand_lookup)

    # Resolve device type from categ_id tuple [id, "Parent / Child"]
    type_id = None
    categ_tuple = odoo_product.get("categ_id")
    if categ_tuple and isinstance(categ_tuple, (list, tuple)) and len(categ_tuple) == 2:
        categ_str = str(categ_tuple[1]).strip()
        if "/" in categ_str:
            type_name = categ_str.rsplit("/", 1)[-1].strip()
        else:
            type_name = categ_str
        if type_name:
            type_id = _find_or_create(DeviceType, "type", type_name, type_lookup)

    # Classify attributes (color, memory, ram, norme)
    attr_ids = odoo_product.get("product_template_attribute_value_ids") or []
    attrs = _classify_attributes(attr_ids, attr_values_cache)

    color_id = None
    if "color" in attrs:
        color_id = _find_or_create(Color, "color", attrs["color"], color_lookup)

    memory_id = None
    if "memory" in attrs:
        normalized_mem = normalize_storage(attrs["memory"]) or attrs["memory"].strip()
        digits = re.sub(r"[^\d]", "", normalized_mem)
        tcp_val = int(digits) if digits else 0
        memory_id = _find_or_create(
            MemoryOption, "memory", normalized_mem, memory_lookup, tcp_value=tcp_val
        )

    ram_id = None
    if "ram" in attrs:
        normalized_ram = normalize_ram(attrs["ram"]) or attrs["ram"].strip()
        ram_id = _find_or_create(RAMOption, "ram", normalized_ram, ram_lookup)

    norme_id = None
    if "norme" in attrs:
        norme_id = _find_or_create(NormeOption, "norme", attrs["norme"], norme_lookup)

    # Fallback: parse product name for missing fields
    fallback, fallback_matched = _parse_name_fallback(
        name, brand_id, color_id, memory_id, ram_id, norme_id, type_id,
        brand_lookup, color_lookup, color_translation_lookup or {},
        memory_lookup, ram_lookup, norme_lookup, type_lookup,
    )
    brand_id = brand_id or fallback.get("brand_id")
    color_id = color_id or fallback.get("color_id")
    memory_id = memory_id or fallback.get("memory_id")
    ram_id = ram_id or fallback.get("ram_id")
    norme_id = norme_id or fallback.get("norme_id")
    type_id = type_id or fallback.get("type_id")

    # Extract model name by removing brand, attributes, and fallback matches
    parts_to_remove: List[str] = list(fallback_matched)
    if brand_tuple and isinstance(brand_tuple, (list, tuple)) and len(brand_tuple) == 2:
        brand_name = str(brand_tuple[1]).strip()
        if brand_name:
            parts_to_remove.append(brand_name)
    for attr_val in attrs.values():
        parts_to_remove.append(attr_val)

    model_name = _extract_model_name(name, parts_to_remove)

    # Build product field dict
    product_fields = {
        "model": model_name,
        "description": normalize_description_units(name),
        "ean": barcode or None,
        "part_number": default_code or None,
        "recommended_price": list_price if list_price else None,
        "brand_id": brand_id,
        "color_id": color_id,
        "memory_id": memory_id,
        "RAM_id": ram_id,
        "norme_id": norme_id,
        "type_id": type_id,
    }

    # --- Try to find existing link via InternalProduct ---
    internal = internal_by_odoo_id.get(odoo_id)
    if internal:
        product = internal.product
        changed = False
        for key, value in product_fields.items():
            if getattr(product, key) != value:
                setattr(product, key, value)
                changed = True
        if changed:
            return "updated", report_item
        return "unchanged", report_item

    # --- Try to find existing product by EAN or part_number ---
    product = None
    if barcode:
        product = product_by_ean.get(barcode)
    if not product and default_code:
        product = product_by_pn.get(default_code)

    if product:
        # Link existing product and update fields
        link = InternalProduct(product_id=product.id, odoo_id=odoo_id)
        db.session.add(link)
        internal_by_odoo_id[odoo_id] = link
        changed = False
        for key, value in product_fields.items():
            if getattr(product, key) != value:
                setattr(product, key, value)
                changed = True
        return "updated" if changed else "unchanged", report_item

    # --- Create new product + link ---
    product = Product(**product_fields)
    db.session.add(product)
    db.session.flush()
    link = InternalProduct(product_id=product.id, odoo_id=odoo_id)
    db.session.add(link)
    internal_by_odoo_id[odoo_id] = link

    if barcode:
        product_by_ean[barcode] = product
    if default_code:
        product_by_pn[default_code] = product

    return "created", report_item


# ---------------------------------------------------------------------------
# Orphan deletion
# ---------------------------------------------------------------------------
def _delete_orphaned_products(
    internal_by_odoo_id: Dict[str, InternalProduct],
    seen_odoo_ids: set,
    counters: Dict[str, int],
    reports: Dict[str, list],
) -> None:
    """Delete products linked to Odoo that are no longer present in the sync."""
    orphaned_ids = set(internal_by_odoo_id.keys()) - seen_odoo_ids
    for orphan_odoo_id in orphaned_ids:
        try:
            internal = internal_by_odoo_id[orphan_odoo_id]
            product = internal.product
            product_id = product.id
            report_item = {
                "odoo_id": orphan_odoo_id,
                "name": product.model or "",
                "ean": product.ean or "",
                "part_number": product.part_number or "",
            }

            # Detach supplier refs (set product_id to NULL)
            SupplierProductRef.query.filter_by(product_id=product_id).update(
                {"product_id": None}
            )
            # Detach pending matches referencing this product as resolved
            PendingMatch.query.filter_by(resolved_product_id=product_id).update(
                {"resolved_product_id": None}, synchronize_session=False
            )
            # Delete product calculations
            ProductCalculation.query.filter_by(product_id=product_id).delete()
            # Delete internal product link
            db.session.delete(internal)
            # Delete product
            db.session.delete(product)

            counters["deleted"] += 1
            if len(reports["deleted"]) < MAX_REPORT_ITEMS:
                reports["deleted"].append(report_item)
        except Exception as e:
            db.session.rollback()
            counters["error"] += 1
            if len(reports["errors"]) < MAX_REPORT_ITEMS:
                reports["errors"].append(
                    {
                        "odoo_id": orphan_odoo_id,
                        "name": internal_by_odoo_id[orphan_odoo_id].product.model
                        if orphan_odoo_id in internal_by_odoo_id
                        else "",
                        "error": f"Suppression échouée: {e}",
                    }
                )
            logger.warning(
                "Error deleting orphan product odoo_id=%s: %s", orphan_odoo_id, e
            )


# ---------------------------------------------------------------------------
# Main sync function
# ---------------------------------------------------------------------------
def run_odoo_sync(job_id: int) -> None:
    """Run a full Odoo product synchronization for the given job."""
    job = db.session.get(OdooSyncJob, job_id)
    if not job:
        logger.error("OdooSyncJob %s not found", job_id)
        return

    try:
        config = OdooConfig.query.first()
        if not config:
            raise ValueError("Configuration Odoo manquante")

        client = OdooClient(config.url, config.database, config.login, config.password)
        client.authenticate()

        # Count active products
        domain = [["active", "=", True]]
        total_count = client.search_count("product.product", domain)
        job.total_odoo_products = total_count

        # Detect available fields on product.product
        available_fields = set(
            client.execute_kw(
                "product.product", "fields_get", [], {"attributes": ["string"]},
            ).keys()
        )

        # Build fields list, skipping optional fields not present on this Odoo
        product_fields = [
            "id",
            "name",
            "barcode",
            "default_code",
            "list_price",
            "categ_id",
            "product_template_attribute_value_ids",
        ]
        optional_fields = ["product_brand_id"]
        for f in optional_fields:
            if f in available_fields:
                product_fields.append(f)

        # Fetch all products in batches
        all_products: List[dict] = []
        offset = 0
        while offset < total_count:
            batch = client.search_read(
                "product.product",
                domain,
                product_fields,
                limit=BATCH_SIZE,
                offset=offset,
            )
            if not batch:
                break
            all_products.extend(batch)
            offset += len(batch)

        # Collect all attribute value IDs for batch fetch
        all_attr_ids: set = set()
        for p in all_products:
            ids = p.get("product_template_attribute_value_ids") or []
            all_attr_ids.update(ids)

        # Batch-fetch attribute values
        attr_values_cache: Dict[int, dict] = {}
        if all_attr_ids:
            attr_ids_list = list(all_attr_ids)
            av_offset = 0
            while av_offset < len(attr_ids_list):
                batch_ids = attr_ids_list[av_offset : av_offset + BATCH_SIZE]
                avs = client.search_read(
                    "product.template.attribute.value",
                    [["id", "in", batch_ids]],
                    ["id", "name", "attribute_id"],
                )
                for av in avs:
                    attr_values_cache[av["id"]] = av
                av_offset += len(batch_ids)

        # Pre-load reference lookups
        brand_lookup = _build_lookup(Brand, "brand")
        color_lookup = _build_lookup(Color, "color")
        memory_lookup = _build_lookup(MemoryOption, "memory")
        ram_lookup = _build_lookup(RAMOption, "ram")
        norme_lookup = _build_lookup(NormeOption, "norme")
        type_lookup = _build_lookup(DeviceType, "type")
        color_translation_lookup: Dict[str, int] = {
            t.color_source.lower(): t.color_target_id
            for t in ColorTranslation.query.all()
            if t.color_source
        }

        # Pre-load internal products and product lookups
        internal_by_odoo_id: Dict[str, InternalProduct] = {
            ip.odoo_id: ip
            for ip in InternalProduct.query.options(
                db.joinedload(InternalProduct.product)
            ).all()
        }
        product_by_ean: Dict[str, Product] = {
            p.ean: p for p in Product.query.all() if p.ean
        }
        product_by_pn: Dict[str, Product] = {
            p.part_number: p for p in Product.query.all() if p.part_number
        }

        # Process each product
        counters = {"created": 0, "updated": 0, "unchanged": 0, "error": 0, "deleted": 0}
        reports: Dict[str, list] = {
            "created": [],
            "updated": [],
            "unchanged": [],
            "errors": [],
            "deleted": [],
        }

        seen_odoo_ids: set = set()
        for odoo_product in all_products:
            seen_odoo_ids.add(str(odoo_product["id"]))
            try:
                status, report_item = _process_single_product(
                    odoo_product,
                    attr_values_cache,
                    brand_lookup,
                    color_lookup,
                    memory_lookup,
                    ram_lookup,
                    norme_lookup,
                    type_lookup,
                    internal_by_odoo_id,
                    product_by_ean,
                    product_by_pn,
                    color_translation_lookup,
                )
                counters[status] += 1
                report_key = "errors" if status == "error" else status
                if len(reports[report_key]) < MAX_REPORT_ITEMS:
                    reports[report_key].append(report_item)
            except Exception as e:
                counters["error"] += 1
                if len(reports["errors"]) < MAX_REPORT_ITEMS:
                    reports["errors"].append(
                        {
                            "odoo_id": str(odoo_product.get("id", "?")),
                            "name": odoo_product.get("name", ""),
                            "error": str(e),
                        }
                    )
                logger.warning("Error processing product %s: %s", odoo_product.get("id"), e)

        # Delete orphaned products (linked to Odoo but no longer present)
        _delete_orphaned_products(
            internal_by_odoo_id, seen_odoo_ids, counters, reports,
        )

        db.session.commit()

        # Finalize job
        job.created_count = counters["created"]
        job.updated_count = counters["updated"]
        job.unchanged_count = counters["unchanged"]
        job.error_count = counters["error"]
        job.deleted_count = counters["deleted"]
        job.report_created = reports["created"]
        job.report_updated = reports["updated"]
        job.report_unchanged = reports["unchanged"]
        job.report_errors = reports["errors"]
        job.report_deleted = reports["deleted"]
        job.status = "success"
        job.ended_at = datetime.now(timezone.utc)
        db.session.commit()

    except Exception as e:
        logger.exception("Odoo sync job %s failed: %s", job_id, e)
        db.session.rollback()
        job.status = "failed"
        job.error_message = str(e)
        job.ended_at = datetime.now(timezone.utc)
        db.session.commit()
