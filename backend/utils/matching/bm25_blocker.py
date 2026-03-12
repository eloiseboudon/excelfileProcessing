"""BM25 blocking for candidate pre-selection.

Builds a TF-IDF/BM25 index over LabelCache entries and retrieves the
top-k most relevant candidates for each product query. This replaces
the linear scan over all entries of a brand.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from rank_bm25 import BM25Plus


def _tokenize(text: str) -> List[str]:
    """Lowercase, strip accents-insensitive, split on non-alphanumeric."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _label_cache_to_doc(attrs: Dict) -> str:
    """Build a searchable document string from LabelCache extracted_attributes."""
    parts = [
        attrs.get("brand", ""),
        attrs.get("model_family", ""),
        attrs.get("model", ""),
        attrs.get("storage", ""),
        attrs.get("color", ""),
        attrs.get("device_type", ""),
        attrs.get("ram", ""),
        attrs.get("connectivity", ""),
        attrs.get("raw_label", ""),
    ]
    return " ".join(p for p in parts if p)


def _product_to_query(product) -> str:
    """Build a search query string from a Product ORM object."""
    parts = [
        product.brand.brand if product.brand else "",
        product.model or "",
        product.description or "",
        product.memory.memory if product.memory else "",
        product.color.color if product.color else "",
        product.device_type.name if product.device_type else "",
    ]
    return " ".join(p for p in parts if p)


class BM25Blocker:
    """BM25-based candidate blocker for product matching.

    Usage:
        blocker = BM25Blocker(cache_entries)
        candidates = blocker.get_candidates(product, top_k=50)
    """

    def __init__(self, cache_entries: list) -> None:
        self._entries = cache_entries
        self._entry_ids = [e.id for e in cache_entries]

        corpus = []
        for entry in cache_entries:
            attrs = entry.extracted_attributes or {}
            doc = _label_cache_to_doc(attrs)
            corpus.append(_tokenize(doc))

        self._bm25 = BM25Plus(corpus) if corpus else None
        self._id_to_entry = {e.id: e for e in cache_entries}

    @property
    def size(self) -> int:
        return len(self._entries)

    def get_candidates(self, product, top_k: int = 50) -> List:
        """Return the top-k LabelCache entries most relevant to the product."""
        if not self._bm25 or not self._entries:
            return []

        query_text = _product_to_query(product)
        query_tokens = _tokenize(query_text)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)

        scored_indices: List[Tuple[float, int]] = []
        for idx, score in enumerate(scores):
            if score > 0:
                scored_indices.append((score, idx))

        scored_indices.sort(key=lambda x: x[0], reverse=True)
        top_indices = scored_indices[:top_k]

        return [self._entries[idx] for _, idx in top_indices]
