"""Retrieval pipeline orchestrating BM25 + FAISS + cross-encoder.

Replaces the linear scan in Phase 2 of llm_matching with a multi-stage
candidate retrieval pipeline:

    1. BM25 blocking → top-k sparse candidates
    2. FAISS ANN search → top-k dense candidates
    3. Union + dedup → merged candidate set
    4. score_match() deterministic scoring
    5. Cross-encoder reranking on grey zone (70-90)
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app

# Single feature flag — activates BM25 + FAISS + cross-encoder.
# FAISS/cross-encoder degrade gracefully if sentence-transformers is not installed.
MATCHING_V2_ENABLED = os.environ.get("MATCHING_V2_ENABLED", "false").lower() == "true"


def is_v2_enabled() -> bool:
    return MATCHING_V2_ENABLED


class RetrievalPipeline:
    """Multi-stage candidate retrieval for product matching.

    Combines BM25 sparse retrieval with optional FAISS dense retrieval
    and cross-encoder reranking.
    """

    def __init__(
        self,
        cache_entries: list,
        score_match_fn,
        mappings: Dict[str, Any],
        label_to_catalogs: Dict,
        label_eans: Dict,
        ean_to_product_ids: Dict,
        threshold_auto: int = 90,
        threshold_review: int = 70,
        bm25_top_k: int = 200,
        faiss_top_k: int = 200,
    ) -> None:
        self._cache_entries = cache_entries
        self._score_match = score_match_fn
        self._mappings = mappings
        self._label_to_catalogs = label_to_catalogs
        self._label_eans = label_eans
        self._ean_to_product_ids = ean_to_product_ids
        self._threshold_auto = threshold_auto
        self._threshold_review = threshold_review
        self._bm25_top_k = bm25_top_k
        self._faiss_top_k = faiss_top_k

        self._id_to_entry = {e.id: e for e in cache_entries}
        self._bm25_blocker = None
        self._faiss_index = None
        self._product_embeddings: Dict[int, Any] = {}
        self._label_embeddings: Dict[int, Any] = {}
        self._stats = {
            "bm25_candidates_avg": 0.0,
            "faiss_candidates_avg": 0.0,
            "cross_encoder_calls": 0,
            "merged_candidates_avg": 0.0,
        }

        self._init_bm25()
        if is_v2_enabled():
            self._init_faiss()

    def _init_bm25(self) -> None:
        from utils.matching.bm25_blocker import BM25Blocker

        self._bm25_blocker = BM25Blocker(self._cache_entries)
        current_app.logger.info(
            "BM25 blocker initialized with %d entries", self._bm25_blocker.size
        )

    def _init_faiss(self) -> None:
        try:
            from utils.matching.embedder import compute_label_embeddings
            from utils.matching.faiss_index import FAISSIndex

            self._label_embeddings = compute_label_embeddings(self._cache_entries)
            self._faiss_index = FAISSIndex()
            self._faiss_index.build(self._label_embeddings)
            current_app.logger.info(
                "FAISS index built with %d entries", self._faiss_index.size
            )
        except (ImportError, OSError) as exc:
            current_app.logger.warning(
                "FAISS/sentence-transformers not available, skipping dense retrieval: %s", exc
            )
            self._faiss_index = None

    def compute_product_embeddings(self, products: list) -> None:
        """Pre-compute embeddings for all products (call once before scoring)."""
        if self._faiss_index is None:
            return
        try:
            from utils.matching.embedder import compute_product_embeddings

            self._product_embeddings = compute_product_embeddings(products)
            current_app.logger.info(
                "Computed embeddings for %d products", len(self._product_embeddings)
            )
        except (ImportError, OSError):
            pass

    def get_candidates(self, product) -> List:
        """Retrieve candidates using BM25 + optional FAISS, then merge."""
        bm25_candidates = set()
        faiss_candidates = set()

        # Stage 1: BM25 blocking
        if self._bm25_blocker:
            bm25_results = self._bm25_blocker.get_candidates(
                product, top_k=self._bm25_top_k
            )
            bm25_candidates = {e.id for e in bm25_results}

        # Stage 2: FAISS ANN search
        if self._faiss_index and product.id in self._product_embeddings:
            from utils.matching.faiss_index import FAISSIndex

            query_emb = self._product_embeddings[product.id]
            faiss_results = self._faiss_index.search(
                query_emb, top_k=self._faiss_top_k
            )
            faiss_candidates = {lid for lid, _ in faiss_results}

        # Merge candidates (union)
        merged_ids = bm25_candidates | faiss_candidates
        if not merged_ids:
            # Fallback: return all entries (like v1 behavior)
            return self._cache_entries

        # Track stats
        self._stats["bm25_candidates_avg"] += len(bm25_candidates)
        self._stats["faiss_candidates_avg"] += len(faiss_candidates)
        self._stats["merged_candidates_avg"] += len(merged_ids)

        return [self._id_to_entry[lid] for lid in merged_ids if lid in self._id_to_entry]

    def score_product(
        self, product, candidates: List
    ) -> Tuple[List[Tuple[int, Dict, Any]], Optional[Tuple[Dict, Any]]]:
        """Score candidates against a product, with optional cross-encoder reranking.

        Returns (scored, best_disqualified) where:
        - scored: list of (score, details, cache_entry) sorted by score desc
        - best_disqualified: (details, cache_entry) for the first disqualified candidate, or None
        """
        scored: List[Tuple[int, Dict, Any]] = []
        best_disqualified: Optional[Tuple[Dict, Any]] = None

        for cache_entry in candidates:
            attrs = dict(cache_entry.extracted_attributes or {})
            score, details = self._score_match(attrs, product, self._mappings)

            # EAN bonus
            if score > 0:
                entry_eans = self._label_eans.get(
                    (cache_entry.supplier_id, cache_entry.normalized_label), set()
                )
                if entry_eans:
                    for ean in entry_eans:
                        if product.id in self._ean_to_product_ids.get(ean, set()):
                            details["ean_bonus"] = 20
                            score = min(score + 20, 100)
                            break

            if score > 0:
                scored.append((score, details, cache_entry))
            elif best_disqualified is None and details.get("disqualified"):
                best_disqualified = (details, cache_entry)

        if not scored:
            return scored, best_disqualified

        scored.sort(key=lambda x: x[0], reverse=True)

        # Cross-encoder disabled — passage-ranking model not suited for
        # product matching (see project_cross_encoder.md in memory).
        # if is_v2_enabled():
        #     scored = self._apply_cross_encoder(product, scored)

        return scored, best_disqualified

    def _apply_cross_encoder(
        self, product, scored: List[Tuple[int, Dict, Any]]
    ) -> List[Tuple[int, Dict, Any]]:
        """Rerank candidates in the grey zone using the cross-encoder.

        The cross-encoder only reorders candidates with the same deterministic
        score — it does NOT modify scores. This avoids false positives from
        the passage-ranking model boosting unrelated products.
        """
        try:
            from utils.matching.cross_encoder import rerank_pairs
            from utils.matching.embedder import product_to_text
        except ImportError:
            return scored

        grey_zone = [
            (i, s, d, e)
            for i, (s, d, e) in enumerate(scored)
            if self._threshold_review <= s < self._threshold_auto
        ]

        if not grey_zone:
            return scored

        product_text = product_to_text(product)
        pairs = []
        for _, _, _, cache_entry in grey_zone:
            raw_label = (cache_entry.extracted_attributes or {}).get("raw_label", "")
            if not raw_label:
                raw_label = cache_entry.normalized_label or ""
            pairs.append((product_text, raw_label))

        ce_scores = rerank_pairs(pairs)
        self._stats["cross_encoder_calls"] += len(pairs)

        # Annotate details with cross-encoder score (for debugging) but
        # do NOT modify the deterministic score.
        result = list(scored)
        for (orig_idx, orig_score, details, entry), ce_score in zip(grey_zone, ce_scores):
            new_details = dict(details)
            new_details["cross_encoder_score"] = round(ce_score, 4)
            result[orig_idx] = (orig_score, new_details, entry)

        # Stable sort: among candidates with the same deterministic score,
        # prefer the one the cross-encoder ranks higher.
        result.sort(key=lambda x: (x[0], x[1].get("cross_encoder_score", 0)), reverse=True)
        return result

    def get_stats(self) -> Dict[str, Any]:
        """Return pipeline statistics for the run."""
        return dict(self._stats)
