"""Cross-encoder reranker for the grey zone (scores 70-90).

Uses a cross-encoder model to produce a more accurate relevance score
for ambiguous product-label pairs, potentially promoting them to
auto-match or confirming them as pending review.
"""

from __future__ import annotations

from typing import List, Tuple

_MODEL_NAME = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
_cross_encoder = None
_cross_encoder_failed = False

BOOST_THRESHOLD = 0.8
PENALIZE_THRESHOLD = 0.3
BOOST_POINTS = 15
PENALIZE_POINTS = 15


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


def rerank_pair(query: str, document: str) -> float:
    """Score a single (query, document) pair with the cross-encoder.

    Returns a relevance score (higher = more relevant), or 0.5 if unavailable.
    """
    model = _get_cross_encoder()
    if model is None:
        return 0.5
    score = model.predict([(query, document)])[0]
    return float(score)


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


def adjust_score(
    original_score: int, cross_encoder_score: float
) -> Tuple[int, str]:
    """Adjust the attribute-based score using the cross-encoder output.

    Args:
        original_score: the deterministic score from score_match().
        cross_encoder_score: the cross-encoder relevance score.

    Returns:
        (adjusted_score, reason) where reason explains the adjustment.
    """
    if cross_encoder_score >= BOOST_THRESHOLD:
        adjusted = min(original_score + BOOST_POINTS, 100)
        return adjusted, f"cross_encoder_boost (+{adjusted - original_score})"
    elif cross_encoder_score <= PENALIZE_THRESHOLD:
        adjusted = max(original_score - PENALIZE_POINTS, 0)
        return adjusted, f"cross_encoder_penalize (-{original_score - adjusted})"
    return original_score, "cross_encoder_neutral"
