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
                  color="Noir", description=None, device_type="smartphone",
                  region="EU"):
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
    product.region = region
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

    def test_rerank_pairs_unavailable(self):
        from utils.matching.cross_encoder import rerank_pairs
        # When model is not loaded, should return 0.5 for each pair
        scores = rerank_pairs([("query1", "doc1"), ("query2", "doc2")])
        assert len(scores) == 2

    def test_rerank_pairs_empty(self):
        from utils.matching.cross_encoder import rerank_pairs
        assert rerank_pairs([]) == []


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


# ---------------------------------------------------------------------------
# Model cleaning & variant extraction — prevent false cross-matches
# ---------------------------------------------------------------------------

class TestCleanModelForScoring:

    def test_strips_reference_codes(self):
        from utils.llm_matching import _clean_model_for_scoring
        # SM-prefixed codes (Samsung)
        assert "sm-" not in _clean_model_for_scoring("Galaxy Tab A9+ SM-X216R")
        assert "sm-" not in _clean_model_for_scoring("Galaxy Watch 3 SM-R840N")
        # Short alpha+digits codes (X216R, GA09958, L505)
        cleaned = _clean_model_for_scoring("Galaxy Tab A9+ X216R 11.0 8/256GB")
        assert "x216r" not in cleaned
        assert "11.0" not in cleaned

    def test_strips_screen_sizes(self):
        from utils.llm_matching import _clean_model_for_scoring
        assert "12.4" not in _clean_model_for_scoring("Galaxy Tab S10+ 12.4")
        assert "11.0" not in _clean_model_for_scoring("Tab A9+ 11.0")

    def test_preserves_model_identity(self):
        from utils.llm_matching import _clean_model_for_scoring
        # Core model names must survive cleaning
        assert "galaxy tab s10" in _clean_model_for_scoring("Galaxy Tab S10+")
        assert "galaxy tab a9" in _clean_model_for_scoring("Galaxy Tab A9+")
        assert "iphone 16" in _clean_model_for_scoring("iPhone 16 Pro Max 256GB")
        assert "redmi note 13" in _clean_model_for_scoring("Redmi Note 13 Pro 5G DS 8/256GB")


class TestExtractModelVariants:

    def test_galaxy_tab_series_differ(self):
        """Galaxy Tab A ≠ Galaxy Tab S — must be disqualified."""
        from utils.llm_matching import _extract_model_variants
        v_a = _extract_model_variants("galaxy tab a9")
        v_s = _extract_model_variants("galaxy tab s10")
        assert v_a != v_s
        assert "tab-a" in v_a
        assert "tab-s" in v_s

    def test_galaxy_phone_series_differ(self):
        """Galaxy A15 ≠ Galaxy S24."""
        from utils.llm_matching import _extract_model_variants
        v_a = _extract_model_variants("galaxy a15")
        v_s = _extract_model_variants("galaxy s24")
        assert v_a != v_s

    def test_watch_standard_vs_classic(self):
        """Galaxy Watch 3 ≠ Galaxy Watch 8 Classic."""
        from utils.llm_matching import _extract_model_variants
        v_std = _extract_model_variants("galaxy watch 3")
        v_cls = _extract_model_variants("galaxy watch 8 classic")
        assert v_std != v_cls
        assert "watch-standard" in v_std
        assert "watch-classic" in v_cls

    def test_same_series_same_variants(self):
        """Galaxy Tab A9+ and Galaxy Tab A11+ should have same series variant."""
        from utils.llm_matching import _extract_model_variants
        v1 = _extract_model_variants("galaxy tab a9+")
        v2 = _extract_model_variants("galaxy tab a11+")
        # Both have tab-a and plus — series match (version check handles 9 vs 11)
        assert "tab-a" in v1
        assert "tab-a" in v2

    def test_existing_variants_preserved(self):
        """Pro, Ultra, FE etc. still work."""
        from utils.llm_matching import _extract_model_variants
        assert "pro" in _extract_model_variants("iphone 16 pro")
        assert "ultra" in _extract_model_variants("galaxy s25 ultra")
        assert "fe" in _extract_model_variants("galaxy s24 fe")
        assert "lite" in _extract_model_variants("redmi note 13 lite")


class TestModelScoringDisqualification:
    """End-to-end tests: wrong model cross-matches must be disqualified."""

    def _score(self, ext_model, prod_model, brand="Samsung"):
        """Helper: score only the model component."""
        from utils.llm_matching import score_match
        extracted = {
            "brand": brand,
            "model_family": ext_model,
            "storage": "256 Go",
            "device_type": "Tablette" if "tab" in ext_model.lower() else "Smartphone",
            "region": "EU",
        }
        product = _make_product(
            1, brand=brand, model=prod_model, memory="256Go",
            device_type="tablette" if "tab" in prod_model.lower() else "smartphone",
            region="EU",
        )
        return score_match(extracted, product, {"color_translations": {}, "color_words": set()})

    def test_tab_a11_vs_tab_s9_disqualified(self):
        """Galaxy Tab A11+ must NOT match Galaxy Tab S9."""
        score, details = self._score("Galaxy Tab A11+", "Galaxy Tab S9 X716B 11.0 12/256GB")
        assert score == 0, f"Should be disqualified, got score={score}, details={details}"
        assert "disqualified" in details

    def test_tab_s10_vs_tab_a9_disqualified(self):
        """Galaxy Tab S10+ must NOT match Galaxy Tab A9+."""
        score, details = self._score("Galaxy Tab S10+", "Galaxy Tab A9+ X216R 11.0 8/256GB")
        assert score == 0, f"Should be disqualified, got score={score}, details={details}"
        assert "disqualified" in details

    def test_watch3_vs_watch8_classic_disqualified(self):
        """Galaxy Watch 3 must NOT match Galaxy Watch 8 Classic."""
        score, details = self._score("Galaxy Watch 3 45mm", "Galaxy Watch 8 Classic L505 46mm LTE")
        assert score == 0, f"Should be disqualified, got score={score}, details={details}"
        assert "disqualified" in details

    def test_galaxy_a15_vs_galaxy_s24_disqualified(self):
        """Galaxy A15 must NOT match Galaxy S24."""
        score, details = self._score("Galaxy A15", "Galaxy S24")
        assert score == 0, f"Should be disqualified, got score={score}, details={details}"
        assert "disqualified" in details

    def test_same_model_still_matches(self):
        """Galaxy Tab S10+ must still match Galaxy Tab S10+ (different ref code)."""
        score, details = self._score("Galaxy Tab S10+", "Galaxy Tab S10+ SM-X820N 12.4 12/256GB")
        assert score > 70, f"Should match, got score={score}, details={details}"

    def test_iphone_16_vs_17_disqualified(self):
        """iPhone 16 must NOT match iPhone 17e."""
        score, details = self._score("iPhone 16", "iPhone 17e", brand="Apple")
        assert score == 0, f"Should be disqualified, got score={score}, details={details}"

    def test_redmi_15_matches_redmi_15(self):
        """Redmi 15 5G must still match Redmi 15 DS."""
        score, details = self._score("Redmi 15", "Redmi 15 DS 8/256GB", brand="Xiaomi")
        assert score > 70, f"Should match, got score={score}, details={details}"
