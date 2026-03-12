"""Tests for the advanced matching pipeline (BM25, embeddings, FAISS, cross-encoder)."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cache_entry(id_, supplier_id, normalized_label, attrs):
    """Create a mock LabelCache-like object."""
    entry = MagicMock()
    entry.id = id_
    entry.supplier_id = supplier_id
    entry.normalized_label = normalized_label
    entry.extracted_attributes = attrs
    return entry


def _make_product(id_, brand="Samsung", model="Galaxy S25 Ultra", memory="256Go",
                  color="Noir", description=None, device_type="smartphone"):
    product = MagicMock()
    product.id = id_
    product.model = model
    product.description = description or model
    product.brand = MagicMock()
    product.brand.brand = brand
    product.memory = MagicMock()
    product.memory.memory = memory
    product.color = MagicMock()
    product.color.color = color
    product.type = MagicMock()
    product.type.type = device_type
    product.ean = None
    return product


# ---------------------------------------------------------------------------
# BM25 Blocker
# ---------------------------------------------------------------------------

class TestBM25Blocker:

    def test_empty_corpus(self):
        from utils.matching.bm25_blocker import BM25Blocker
        blocker = BM25Blocker([])
        assert blocker.size == 0
        product = _make_product(1)
        assert blocker.get_candidates(product) == []

    def test_single_entry_match(self):
        from utils.matching.bm25_blocker import BM25Blocker
        entry = _make_cache_entry(1, 10, "samsung galaxy s25 ultra 256go noir", {
            "brand": "Samsung",
            "model_family": "Galaxy",
            "model": "Galaxy S25 Ultra",
            "storage": "256Go",
            "color": "Noir",
            "device_type": "smartphone",
            "raw_label": "Samsung Galaxy S25 Ultra 256Go Noir",
        })
        blocker = BM25Blocker([entry])
        product = _make_product(1)
        candidates = blocker.get_candidates(product, top_k=10)
        assert len(candidates) == 1
        assert candidates[0].id == 1

    def test_top_k_limits_results(self):
        from utils.matching.bm25_blocker import BM25Blocker
        entries = [
            _make_cache_entry(i, 10, f"samsung product {i}", {
                "brand": "Samsung",
                "model": f"Product {i}",
                "raw_label": f"Samsung Product {i}",
            })
            for i in range(20)
        ]
        blocker = BM25Blocker(entries)
        product = _make_product(1, model="Product 5")
        candidates = blocker.get_candidates(product, top_k=5)
        assert len(candidates) <= 5

    def test_irrelevant_entries_filtered(self):
        from utils.matching.bm25_blocker import BM25Blocker
        relevant = _make_cache_entry(1, 10, "samsung galaxy s25", {
            "brand": "Samsung",
            "model": "Galaxy S25",
            "raw_label": "Samsung Galaxy S25",
        })
        irrelevant = _make_cache_entry(2, 10, "apple iphone 16 pro", {
            "brand": "Apple",
            "model": "iPhone 16 Pro",
            "raw_label": "Apple iPhone 16 Pro 256Go",
        })
        blocker = BM25Blocker([relevant, irrelevant])
        product = _make_product(1, brand="Samsung", model="Galaxy S25")
        candidates = blocker.get_candidates(product, top_k=10)
        # Samsung query should rank Samsung entry higher
        assert candidates[0].id == 1


# ---------------------------------------------------------------------------
# Embedder
# ---------------------------------------------------------------------------

class TestEmbedder:

    def test_product_to_text(self):
        from utils.matching.embedder import product_to_text
        product = _make_product(1)
        text = product_to_text(product)
        assert "Samsung" in text
        assert "Galaxy S25 Ultra" in text
        assert "256Go" in text

    def test_label_cache_to_text(self):
        from utils.matching.embedder import label_cache_to_text
        attrs = {"brand": "Samsung", "model": "Galaxy S25", "color": "Noir"}
        text = label_cache_to_text(attrs)
        assert "Samsung" in text
        assert "Galaxy S25" in text

    def test_label_cache_to_text_empty(self):
        from utils.matching.embedder import label_cache_to_text
        assert label_cache_to_text({}) == ""


# ---------------------------------------------------------------------------
# FAISS Index
# ---------------------------------------------------------------------------

class TestFAISSIndex:

    def test_build_and_search(self):
        from utils.matching.faiss_index import FAISSIndex
        idx = FAISSIndex()

        # Random normalized embeddings
        rng = np.random.default_rng(42)
        embeddings = {}
        for i in range(10):
            vec = rng.random(768).astype(np.float32)
            vec /= np.linalg.norm(vec)
            embeddings[i + 1] = vec

        idx.build(embeddings)
        assert idx.size == 10

        # Search with the first entry's embedding → should return itself as top-1
        results = idx.search(embeddings[1], top_k=5)
        assert len(results) == 5
        assert results[0][0] == 1  # top result is itself
        assert results[0][1] > 0.99  # cosine ~ 1.0

    def test_empty_index(self):
        from utils.matching.faiss_index import FAISSIndex
        idx = FAISSIndex()
        idx.build({})
        assert idx.size == 0
        assert idx.search(np.zeros(768, dtype=np.float32)) == []

    def test_search_top_k_larger_than_index(self):
        from utils.matching.faiss_index import FAISSIndex
        idx = FAISSIndex()
        rng = np.random.default_rng(42)
        embeddings = {1: rng.random(768).astype(np.float32)}
        embeddings[1] /= np.linalg.norm(embeddings[1])
        idx.build(embeddings)
        results = idx.search(embeddings[1], top_k=100)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Cross-encoder
# ---------------------------------------------------------------------------

class TestCrossEncoder:

    def test_adjust_score_boost(self):
        from utils.matching.cross_encoder import adjust_score
        adjusted, reason = adjust_score(80, 0.9)
        assert adjusted == 95
        assert "boost" in reason

    def test_adjust_score_penalize(self):
        from utils.matching.cross_encoder import adjust_score
        adjusted, reason = adjust_score(75, 0.1)
        assert adjusted == 60
        assert "penalize" in reason

    def test_adjust_score_neutral(self):
        from utils.matching.cross_encoder import adjust_score
        adjusted, reason = adjust_score(80, 0.5)
        assert adjusted == 80
        assert "neutral" in reason

    def test_adjust_score_clamp_max(self):
        from utils.matching.cross_encoder import adjust_score
        adjusted, _ = adjust_score(95, 0.9)
        assert adjusted == 100

    def test_adjust_score_clamp_min(self):
        from utils.matching.cross_encoder import adjust_score
        adjusted, _ = adjust_score(5, 0.1)
        assert adjusted == 0


# ---------------------------------------------------------------------------
# Fine-tuner (unit tests — no actual training)
# ---------------------------------------------------------------------------

class TestFineTuner:

    def test_export_requires_db(self):
        """export_training_pairs needs a db session — smoke test the import."""
        from utils.matching.fine_tuner import MIN_PAIRS_REQUIRED
        assert MIN_PAIRS_REQUIRED > 0

    def test_run_fine_tuning_rejects_small_dataset(self):
        from utils.matching.fine_tuner import run_fine_tuning
        pairs = [("a", "b", True)] * 10
        with pytest.raises(ValueError, match="Need at least"):
            run_fine_tuning(pairs)
