"""Cross-encoder reranker for the grey zone (scores 50-89).

Uses a cross-encoder model to rerank candidates in the grey zone.
The cross-encoder does NOT modify scores — it only reorders candidates
so the best semantic match appears first. Score adjustments are left
to the deterministic scoring pipeline.
"""

from __future__ import annotations

from typing import List, Tuple

_MODEL_NAME = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
_cross_encoder = None
_cross_encoder_failed = False


def _get_cross_encoder():
    """Lazy-load the cross-encoder model (singleton).

    Returns None if the model cannot be loaded (missing deps or network).
    Caches failure to avoid retrying on every call.
    """
    global _cross_encoder, _cross_encoder_failed
    if _cross_encoder is not None:
        return _cross_encoder
    if _cross_encoder_failed:
        return None

    try:
        from sentence_transformers import CrossEncoder

        _cross_encoder = CrossEncoder(_MODEL_NAME)
        return _cross_encoder
    except (ImportError, OSError) as exc:
        import logging

        logging.getLogger(__name__).warning(
            "Cross-encoder unavailable, skipping reranking: %s", exc
        )
        _cross_encoder_failed = True
        return None


def rerank_pairs(pairs: List[Tuple[str, str]]) -> List[float]:
    """Score multiple (query, document) pairs.

    Returns a list of relevance scores in the same order, or 0.5 if unavailable.
    """
    if not pairs:
        return []
    model = _get_cross_encoder()
    if model is None:
        return [0.5] * len(pairs)
    scores = model.predict(pairs)
    return [float(s) for s in scores]
