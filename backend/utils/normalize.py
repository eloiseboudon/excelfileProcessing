"""Normalization helpers for memory/storage, RAM values, and supplier labels.

Ensures consistent formatting across all data sources
(API suppliers, Odoo sync, LLM matching).
"""

from __future__ import annotations

import re
from typing import Optional

_STORAGE_RE = re.compile(
    r"^\s*(\d+(?:[.,]\d+)?)\s*(go|gb|to|tb)?\s*$",
    re.IGNORECASE,
)


def normalize_storage(value: Optional[str]) -> Optional[str]:
    """Normalize a storage value to the canonical French format.

    Examples:
        "512GB" -> "512 Go"
        "512go" -> "512 Go"
        "512"   -> "512 Go"
        "1TB"   -> "1 To"
        "1 To"  -> "1 To"
    """
    if not value or not value.strip():
        return None

    m = _STORAGE_RE.match(value.strip())
    if not m:
        return value.strip()

    number = m.group(1).replace(",", ".")
    if "." in number:
        number = number.rstrip("0").rstrip(".")
    number = str(int(float(number))) if float(number) == int(float(number)) else number

    unit = (m.group(2) or "").lower()
    if unit in ("tb", "to"):
        return f"{number} To"
    return f"{number} Go"


def normalize_label(label: str) -> str:
    """Normalize a supplier label for cache key usage.

    Lowercase, strip special characters, normalize storage units so that
    '256GB', '256 GB', '256 Go' and '256go' all map to the same key '256go'.
    Example: 'Apple iPhone 15 128GB - Black' -> 'apple iphone 15 128go black'
    """
    text = label.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)  # removes -, (, ), [, ], /
    text = re.sub(r"_", " ", text)         # underscores to spaces
    # Normalize storage units: 256GB/256 GB → 256go, 1TB/1 TB → 1to
    text = re.sub(r"(\d+)\s*gb\b", r"\1go", text)
    text = re.sub(r"(\d+)\s*tb\b", r"\1to", text)
    # Remove space between digit and go/to unit: "256 go" → "256go"
    text = re.sub(r"(\d+)\s+(go|to)\b", r"\1\2", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_ram(value: Optional[str]) -> Optional[str]:
    """Normalize a RAM value to the canonical French format.

    Examples:
        "4"   -> "4 Go"
        "4Go" -> "4 Go"
        "4GB" -> "4 Go"
        "8 go" -> "8 Go"
    """
    if not value or not value.strip():
        return None

    m = _STORAGE_RE.match(value.strip())
    if not m:
        return value.strip()

    number = m.group(1).replace(",", ".")
    if "." in number:
        number = number.rstrip("0").rstrip(".")
    number = str(int(float(number))) if float(number) == int(float(number)) else number

    return f"{number} Go"
