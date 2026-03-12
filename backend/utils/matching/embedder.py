"""Bi-encoder embeddings for semantic product matching.

Uses sentence-transformers to encode product descriptions and supplier
labels into dense vectors for similarity search.
"""

from __future__ import annotations

import os
from typing import List, Optional

import numpy as np

_MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"
_FINETUNED_PATH = os.environ.get(
    "MATCHING_MODEL_PATH", "/app/data/models/matching-finetuned"
)

_model = None


def _get_model():
    """Lazy-load the sentence-transformer model (singleton)."""
    global _model
    if _model is not None:
        return _model

    from sentence_transformers import SentenceTransformer

    if os.path.isdir(_FINETUNED_PATH):
        _model = SentenceTransformer(_FINETUNED_PATH)
    else:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def embed_text(text: str) -> np.ndarray:
    """Encode a single text into a normalized embedding vector."""
    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.astype(np.float32)


def embed_texts(texts: List[str], batch_size: int = 64) -> np.ndarray:
    """Encode multiple texts into normalized embedding vectors."""
    model = _get_model()
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=batch_size,
        show_progress_bar=False,
    )
    return embeddings.astype(np.float32)


def product_to_text(product) -> str:
    """Build a text representation from a Product ORM object for embedding."""
    parts = [
        product.brand.brand if product.brand else "",
        product.model or "",
        product.description or "",
        product.memory.memory if product.memory else "",
        product.color.color if product.color else "",
        product.device_type.name if product.device_type else "",
    ]
    return " ".join(p for p in parts if p).strip()


def label_cache_to_text(attrs: dict) -> str:
    """Build a text representation from LabelCache extracted_attributes."""
    parts = [
        attrs.get("brand", ""),
        attrs.get("model_family", ""),
        attrs.get("model", ""),
        attrs.get("storage", ""),
        attrs.get("color", ""),
        attrs.get("device_type", ""),
        attrs.get("raw_label", ""),
    ]
    return " ".join(p for p in parts if p).strip()


def compute_product_embeddings(products: list) -> dict:
    """Compute embeddings for a list of Product objects.

    Returns dict mapping product_id -> np.ndarray embedding.
    """
    texts = [product_to_text(p) for p in products]
    ids = [p.id for p in products]
    embeddings = embed_texts(texts)
    return {pid: emb for pid, emb in zip(ids, embeddings)}


def compute_label_embeddings(cache_entries: list) -> dict:
    """Compute embeddings for a list of LabelCache entries.

    Returns dict mapping label_cache_id -> np.ndarray embedding.
    """
    texts = [label_cache_to_text(e.extracted_attributes or {}) for e in cache_entries]
    ids = [e.id for e in cache_entries]
    embeddings = embed_texts(texts)
    return {lid: emb for lid, emb in zip(ids, embeddings)}


def get_model_name() -> str:
    """Return the name of the currently loaded model."""
    if os.path.isdir(_FINETUNED_PATH):
        return f"finetuned:{_FINETUNED_PATH}"
    return _MODEL_NAME
