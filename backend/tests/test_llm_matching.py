"""Tests for utils/llm_matching.py — LLM extraction, scoring, and orchestration."""

import json
from unittest.mock import MagicMock, patch

import pytest

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
from utils.llm_matching import (
    _find_fuzzy_cache_entry,
    _fuzzy_ratio,
    _make_attr_key,
    _normalize_storage,
    build_context,
    build_extraction_prompt,
    call_llm_extraction,
    create_product_from_extraction,
    find_best_matches,
    normalize_label,
    run_matching_job,
    score_match,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def supplier():
    s = Supplier(name="Yukatel")
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture()
def brand_samsung():
    b = Brand(brand="Samsung")
    db.session.add(b)
    db.session.commit()
    return b


@pytest.fixture()
def brand_apple():
    b = Brand(brand="Apple")
    db.session.add(b)
    db.session.commit()
    return b


@pytest.fixture()
def memory_256():
    m = MemoryOption(memory="256 Go", tcp_value=256)
    db.session.add(m)
    db.session.commit()
    return m


@pytest.fixture()
def memory_128():
    m = MemoryOption(memory="128 Go", tcp_value=128)
    db.session.add(m)
    db.session.commit()
    return m


@pytest.fixture()
def color_noir():
    c = Color(color="Noir")
    db.session.add(c)
    db.session.commit()
    return c


@pytest.fixture()
def color_blanc():
    c = Color(color="Blanc")
    db.session.add(c)
    db.session.commit()
    return c


@pytest.fixture()
def device_type():
    dt = DeviceType(type="Smartphone")
    db.session.add(dt)
    db.session.commit()
    return dt


@pytest.fixture()
def color_translations(color_noir, color_blanc):
    t1 = ColorTranslation(
        color_source="Black", color_target="Noir", color_target_id=color_noir.id
    )
    t2 = ColorTranslation(
        color_source="Midnight", color_target="Noir", color_target_id=color_noir.id
    )
    t3 = ColorTranslation(
        color_source="White", color_target="Blanc", color_target_id=color_blanc.id
    )
    db.session.add_all([t1, t2, t3])
    db.session.commit()
    return [t1, t2, t3]


@pytest.fixture()
def model_references(brand_samsung):
    refs = [
        ModelReference(
            manufacturer_code="SM-S938B",
            commercial_name="Galaxy S25 Ultra",
            brand_id=brand_samsung.id,
        ),
        ModelReference(
            manufacturer_code="S938B",
            commercial_name="Galaxy S25 Ultra",
            brand_id=brand_samsung.id,
        ),
    ]
    db.session.add_all(refs)
    db.session.commit()
    return refs


@pytest.fixture()
def product_s25(brand_samsung, memory_256, color_noir):
    p = Product(
        model="Galaxy S25 Ultra",
        brand_id=brand_samsung.id,
        memory_id=memory_256.id,
        color_id=color_noir.id,
    )
    db.session.add(p)
    db.session.commit()
    return p


@pytest.fixture()
def product_iphone(brand_apple, memory_128, color_blanc):
    p = Product(
        model="iPhone 16 Pro",
        brand_id=brand_apple.id,
        memory_id=memory_128.id,
        color_id=color_blanc.id,
    )
    db.session.add(p)
    db.session.commit()
    return p


# ---------------------------------------------------------------------------
# Tests: normalize_label
# ---------------------------------------------------------------------------


class TestNormalizeLabel:
    def test_basic(self):
        # GB is normalized to go
        assert normalize_label("Apple iPhone 15 128GB - Black") == "apple iphone 15 128go black"

    def test_multiple_spaces(self):
        assert normalize_label("  Samsung   Galaxy  S25  ") == "samsung galaxy s25"

    def test_special_chars(self):
        # GB is normalized to go
        assert normalize_label("SM-S938B/DS (256GB)") == "sm s938b ds 256go"

    def test_empty(self):
        assert normalize_label("") == ""

    def test_unicode(self):
        result = normalize_label("Écran OLED")
        assert result == "écran oled"

    def test_storage_gb_variants_all_map_to_same_key(self):
        """256GB, 256 GB, 256 Go all produce the same normalized key."""
        assert normalize_label("Samsung 256GB") == normalize_label("Samsung 256 GB")
        assert normalize_label("Samsung 256GB") == normalize_label("Samsung 256 Go")
        assert normalize_label("Samsung 256GB") == normalize_label("Samsung 256go")
        assert normalize_label("Samsung 256GB") == "samsung 256go"

    def test_storage_tb_variants_all_map_to_same_key(self):
        """1TB, 1 TB, 1 To all produce the same normalized key."""
        assert normalize_label("NAS 1TB") == normalize_label("NAS 1 TB")
        assert normalize_label("NAS 1TB") == normalize_label("NAS 1 To")
        assert normalize_label("NAS 1TB") == "nas 1to"

    def test_underscore_becomes_space(self):
        assert normalize_label("SM_S938B_256GB") == "sm s938b 256go"


# ---------------------------------------------------------------------------
# Tests: build_context
# ---------------------------------------------------------------------------


class TestBuildContext:
    def test_returns_all_keys(
        self, brand_samsung, color_noir, color_translations, memory_256, device_type, model_references
    ):
        ctx = build_context()
        assert "brands" in ctx
        assert "Samsung" in ctx["brands"]
        assert "colors" in ctx
        assert "Noir" in ctx["colors"]
        assert "storage_options" in ctx
        assert "256 Go" in ctx["storage_options"]
        assert "model_references" in ctx
        assert "SM-S938B" in ctx["model_references"]
        assert "device_types" in ctx
        assert "Smartphone" in ctx["device_types"]
        assert "few_shot_examples" in ctx

    def test_color_synonyms(self, color_noir, color_translations):
        ctx = build_context()
        assert "Black" in ctx["colors"]["Noir"]
        assert "Midnight" in ctx["colors"]["Noir"]

    def test_few_shot_brand_diversity(self, supplier, brand_samsung, brand_apple, memory_256, color_noir):
        """N-shot selection must include at most 3 examples per brand."""
        # Insert 5 Samsung entries + 2 Apple entries with high scores
        for i in range(5):
            db.session.add(LabelCache(
                supplier_id=supplier.id,
                normalized_label=f"samsung label {i}",
                product_id=None,
                match_score=95,
                match_source="auto",
                extracted_attributes={"brand": "Samsung", "model_family": f"Galaxy S{i}", "raw_label": f"Samsung {i}"},
            ))
        for i in range(2):
            db.session.add(LabelCache(
                supplier_id=supplier.id,
                normalized_label=f"apple label {i}",
                product_id=None,
                match_score=92,
                match_source="auto",
                extracted_attributes={"brand": "Apple", "model_family": f"iPhone {i}", "raw_label": f"Apple {i}"},
            ))
        db.session.commit()

        ctx = build_context()
        samsung_count = sum(1 for ex in ctx["few_shot_examples"] if ex["attributes"].get("brand") == "Samsung")
        assert samsung_count <= 3


# ---------------------------------------------------------------------------
# Tests: build_extraction_prompt
# ---------------------------------------------------------------------------


class TestBuildExtractionPrompt:
    def test_contains_brands(self, brand_samsung, brand_apple):
        ctx = build_context()
        prompt = build_extraction_prompt(ctx)
        assert "Samsung" in prompt
        assert "Apple" in prompt

    def test_contains_rules(self):
        ctx = {"brands": [], "colors": {}, "storage_options": [], "model_references": {}, "device_types": []}
        prompt = build_extraction_prompt(ctx)
        assert "REGLES D'EXTRACTION" in prompt
        assert "JSON array" in prompt

    def test_no_examples_section_when_empty(self):
        ctx = {"brands": [], "colors": {}, "storage_options": [], "model_references": {}, "device_types": [], "few_shot_examples": []}
        prompt = build_extraction_prompt(ctx)
        assert "EXEMPLES DE LIBELLES VALIDES" not in prompt

    def test_examples_injected_when_available(self):
        ctx = {
            "brands": [],
            "colors": {},
            "storage_options": [],
            "model_references": {},
            "device_types": [],
            "few_shot_examples": [
                {"label": "SM-S938B 256 BLK", "attributes": {"brand": "Samsung", "model_family": "Galaxy S25 Ultra", "storage": "256 Go"}},
            ],
        }
        prompt = build_extraction_prompt(ctx)
        assert "EXEMPLES DE LIBELLES VALIDES" in prompt
        assert "SM-S938B 256 BLK" in prompt
        assert "Galaxy S25 Ultra" in prompt

    def test_missing_few_shot_key_is_tolerated(self):
        """build_extraction_prompt must work when few_shot_examples key is absent."""
        ctx = {"brands": [], "colors": {}, "storage_options": [], "model_references": {}, "device_types": []}
        prompt = build_extraction_prompt(ctx)
        assert "REGLES D'EXTRACTION" in prompt


# ---------------------------------------------------------------------------
# Tests: call_llm_extraction
# ---------------------------------------------------------------------------


class TestCallLlmExtraction:
    def _make_mock_anthropic(self):
        mock_module = MagicMock()
        # Provide real exception classes so `except` clauses work
        mock_module.AuthenticationError = type("AuthenticationError", (Exception,), {})
        mock_module.RateLimitError = type("RateLimitError", (Exception,), {})
        mock_module.APIConnectionError = type("APIConnectionError", (Exception,), {})
        mock_module.APIStatusError = type("APIStatusError", (Exception,), {})
        return mock_module

    def test_success(self):
        import sys

        mock_module = self._make_mock_anthropic()
        mock_client = MagicMock()
        mock_module.Anthropic.return_value = mock_client

        mock_usage = MagicMock()
        mock_usage.input_tokens = 100
        mock_usage.output_tokens = 50

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text=json.dumps([{"brand": "Samsung", "model_family": "Galaxy S25 Ultra"}]))
        ]
        mock_response.usage = mock_usage
        mock_client.messages.create.return_value = mock_response

        ctx = {"brands": ["Samsung"], "colors": {}, "storage_options": [], "model_references": {}, "device_types": []}
        with patch.dict(sys.modules, {"anthropic": mock_module}):
            result = call_llm_extraction(["SM-S938B 256 BLK"], ctx)

        assert len(result) == 1
        assert result[0]["brand"] == "Samsung"

    def test_strips_markdown_fences(self):
        import sys

        mock_module = self._make_mock_anthropic()
        mock_client = MagicMock()
        mock_module.Anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text='```json\n[{"brand": "Apple"}]\n```')
        ]
        mock_response.usage = MagicMock(input_tokens=0, output_tokens=0)
        mock_client.messages.create.return_value = mock_response

        ctx = {"brands": [], "colors": {}, "storage_options": [], "model_references": {}, "device_types": []}
        with patch.dict(sys.modules, {"anthropic": mock_module}):
            result = call_llm_extraction(["iPhone 16"], ctx)

        assert result[0]["brand"] == "Apple"

    def test_retry_on_failure(self):
        import sys

        mock_module = self._make_mock_anthropic()
        mock_client = MagicMock()
        mock_module.Anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='[{"brand": "Samsung"}]')]
        mock_response.usage = MagicMock(input_tokens=0, output_tokens=0)

        mock_client.messages.create.side_effect = [
            Exception("timeout"),
            mock_response,
        ]

        ctx = {"brands": [], "colors": {}, "storage_options": [], "model_references": {}, "device_types": []}
        with patch.dict(sys.modules, {"anthropic": mock_module}):
            result = call_llm_extraction(["test"], ctx)
        assert result[0]["brand"] == "Samsung"
        assert mock_client.messages.create.call_count == 2


# ---------------------------------------------------------------------------
# Tests: score_match
# ---------------------------------------------------------------------------


class TestScoreMatch:
    def test_perfect_match(self, product_s25, color_translations):
        """All fields match, no region info on either side (null = EU) → 100 pts."""
        extracted = {
            "brand": "Samsung",
            "model_family": "Galaxy S25 Ultra",
            "storage": "256 Go",
            "color": "Noir",
            "region": None,
        }
        mappings = {"color_translations": {"black": "Noir"}}
        score, details = score_match(extracted, product_s25, mappings)
        assert score == 100

    def test_perfect_match_with_region(self, brand_samsung, memory_256, color_noir, color_translations):
        """All fields match including region → 100 pts."""
        p = Product(
            model="Galaxy S25 Ultra",
            brand_id=brand_samsung.id,
            memory_id=memory_256.id,
            color_id=color_noir.id,
            region="EU",
        )
        db.session.add(p)
        db.session.commit()

        extracted = {
            "brand": "Samsung",
            "model_family": "Galaxy S25 Ultra",
            "storage": "256 Go",
            "color": "Noir",
            "region": "EU",
        }
        mappings = {"color_translations": {"black": "Noir"}}
        score, details = score_match(extracted, p, mappings)
        assert score == 100

    def test_brand_mismatch_returns_zero(self, product_s25):
        extracted = {"brand": "Apple", "model_family": "Galaxy S25 Ultra", "storage": "256 Go"}
        score, details = score_match(extracted, product_s25, {})
        assert score == 0
        assert details.get("disqualified") == "brand_mismatch"

    def test_brand_none_does_not_disqualify(self, product_s25):
        """If extracted brand is missing, must not disqualify."""
        extracted = {"brand": None, "model_family": "Galaxy S25 Ultra", "storage": "256 Go"}
        score, details = score_match(extracted, product_s25, {})
        assert score > 0
        assert details.get("disqualified") != "brand_mismatch"

    def test_storage_mismatch_returns_zero(self, product_s25):
        extracted = {"brand": "Samsung", "model_family": "Galaxy S25 Ultra", "storage": "128 Go"}
        score, details = score_match(extracted, product_s25, {})
        assert score == 0
        assert details.get("disqualified") == "storage_mismatch"

    def test_storage_mismatch_in_model_name_disqualifies(self, brand_apple):
        """Storage inferred from model name (no memory record) must hard-disqualify
        when supplier storage differs — model name is treated as a definitive storage source."""
        product_1tb = Product(
            model="iPhone 17 Pro Max 1TB",
            brand_id=brand_apple.id,
        )
        db.session.add(product_1tb)
        db.session.commit()

        extracted = {
            "brand": "Apple",
            "model_family": "iPhone 17 Pro Max",
            "storage": "512 Go",
        }
        score, details = score_match(extracted, product_1tb, {})
        assert score == 0
        assert details.get("disqualified") == "storage_mismatch"

    def test_color_mismatch_disqualifies(self, brand_apple, memory_128):
        """Orange label must not match Bleu product."""
        color_bleu = Color(color="Bleu")
        db.session.add(color_bleu)
        db.session.commit()

        product_bleu = Product(
            model="iPhone 17 Pro",
            brand_id=brand_apple.id,
            memory_id=memory_128.id,
            color_id=color_bleu.id,
        )
        db.session.add(product_bleu)
        db.session.commit()

        extracted = {
            "brand": "Apple",
            "model_family": "iPhone 17 Pro",
            "storage": "128 Go",
            "color": "Orange",
            "region": None,
        }
        score, details = score_match(extracted, product_bleu, {})
        assert score == 0
        assert details.get("disqualified") == "color_mismatch"

    def test_color_none_does_not_disqualify(self, brand_apple, memory_128):
        """If product has no color, extracted color must not disqualify."""
        product_no_color = Product(
            model="iPhone 17 Pro",
            brand_id=brand_apple.id,
            memory_id=memory_128.id,
        )
        db.session.add(product_no_color)
        db.session.commit()

        extracted = {
            "brand": "Apple",
            "model_family": "iPhone 17 Pro",
            "storage": "128 Go",
            "color": "Orange",
            "region": None,
        }
        score, details = score_match(extracted, product_no_color, {})
        assert score > 0
        assert details.get("disqualified") != "color_mismatch"

    def test_region_mismatch_disqualifies(self, brand_apple, memory_128, color_noir):
        """Indian Spec label must not match EU product."""
        product_eu = Product(
            model="iPhone 16",
            brand_id=brand_apple.id,
            memory_id=memory_128.id,
            color_id=color_noir.id,
            region="EU",
        )
        db.session.add(product_eu)
        db.session.commit()

        extracted = {
            "brand": "Apple",
            "model_family": "iPhone 16",
            "storage": "128 Go",
            "color": "Noir",
            "region": "IN",
        }
        score, details = score_match(extracted, product_eu, {})
        assert score == 0
        assert details.get("disqualified") == "region_mismatch"

    def test_region_null_treated_as_eu(self, brand_apple, memory_128, color_noir):
        """Null region on both sides = EU match → +5 pts, no disqualification."""
        product_null_region = Product(
            model="iPhone 16",
            brand_id=brand_apple.id,
            memory_id=memory_128.id,
            color_id=color_noir.id,
            region=None,
        )
        db.session.add(product_null_region)
        db.session.commit()

        extracted = {
            "brand": "Apple",
            "model_family": "iPhone 16",
            "storage": "128 Go",
            "color": "Noir",
            "region": None,
        }
        score, details = score_match(extracted, product_null_region, {})
        assert score > 0
        assert details.get("disqualified") != "region_mismatch"
        assert details.get("region") == 5

    def test_non_eu_label_disqualifies_null_region_product(self, brand_apple, memory_128, color_noir):
        """Non-EU label (IN) must disqualify a product with null region (= EU)."""
        product_no_region = Product(
            model="iPhone 16",
            brand_id=brand_apple.id,
            memory_id=memory_128.id,
            color_id=color_noir.id,
            region=None,
        )
        db.session.add(product_no_region)
        db.session.commit()

        extracted = {
            "brand": "Apple",
            "model_family": "iPhone 16",
            "storage": "128 Go",
            "color": "Noir",
            "region": "IN",
        }
        score, details = score_match(extracted, product_no_region, {})
        assert score == 0
        assert details.get("disqualified") == "region_mismatch"

    def test_device_type_mismatch_returns_zero(self, brand_apple, memory_128, color_noir, device_type):
        """A Watch should never match a Smartphone regardless of brand/color."""
        iphone = Product(
            model="iPhone 13",
            brand_id=brand_apple.id,
            memory_id=memory_128.id,
            color_id=color_noir.id,
            type_id=device_type.id,  # Smartphone
        )
        db.session.add(iphone)
        db.session.commit()

        extracted = {
            "brand": "Apple",
            "model_family": "Watch Ultra 3",
            "storage": None,
            "color": "Noir",
            "device_type": "Montre connectee",
        }
        score, details = score_match(extracted, iphone, {})
        assert score == 0
        assert details.get("disqualified") == "device_type_mismatch"

    def test_model_version_mismatch_disqualifies(self, brand_apple, memory_128, color_noir):
        """iPhone 16 label must not match iPhone 15 product despite identical other attributes."""
        iphone15 = Product(
            model="iPhone 15",
            brand_id=brand_apple.id,
            memory_id=memory_128.id,
            color_id=color_noir.id,
        )
        db.session.add(iphone15)
        db.session.commit()

        extracted = {
            "brand": "Apple",
            "model_family": "iPhone 16",
            "storage": "128 Go",
            "color": "Noir",
            "region": None,
        }
        score, details = score_match(extracted, iphone15, {})
        assert score == 0
        assert details.get("disqualified") == "model_version_mismatch"

    def test_model_same_version_different_variant_is_not_disqualified(self, brand_apple, memory_128, color_noir):
        """iPhone 16 Pro must not be disqualified against iPhone 16 (same version number)."""
        iphone16 = Product(
            model="iPhone 16 Pro",
            brand_id=brand_apple.id,
            memory_id=memory_128.id,
            color_id=color_noir.id,
        )
        db.session.add(iphone16)
        db.session.commit()

        extracted = {
            "brand": "Apple",
            "model_family": "iPhone 16",
            "storage": "128 Go",
            "color": "Noir",
            "region": None,
        }
        score, details = score_match(extracted, iphone16, {})
        assert score > 0
        assert details.get("disqualified") != "model_version_mismatch"

    def test_label_similarity_bonus(self, product_s25, color_translations):
        """Exact raw label match gives a +10 bonus, capped at 100."""
        extracted = {
            "brand": "Samsung",
            "model_family": "Galaxy S25 Ultra",
            "storage": "256 Go",
            "color": "Noir",
            "region": None,
            "raw_label": "Galaxy S25 Ultra",
        }
        mappings = {"color_translations": {}}
        score, details = score_match(extracted, product_s25, mappings)
        assert details["label_similarity"] == 10
        assert score == 100  # capped at 100

    def test_label_similarity_malus(self, brand_apple, memory_128, color_noir):
        """Very different raw label penalises a match — version numbers must match to reach this check."""
        # iPhone 13 Pro: model_family will match exactly (version 13 == 13), no version disqualifier
        iphone = Product(
            model="iPhone 13 Pro",
            brand_id=brand_apple.id,
            memory_id=memory_128.id,
            color_id=color_noir.id,
        )
        db.session.add(iphone)
        db.session.commit()

        base = {
            "brand": "Apple",
            "model_family": "iPhone 13 Pro",
            "storage": None,
            "color": None,
            "region": None,
            "device_type": None,
        }
        mappings = {"color_translations": {}}
        score_without, _ = score_match({**base}, product=iphone, mappings=mappings)
        score_with, details = score_match(
            {**base, "raw_label": "Samsung Galaxy S25 Ultra 256 Go Phantom Black"},
            product=iphone,
            mappings=mappings,
        )
        assert details["label_similarity"] == -10
        assert score_with < score_without

    def test_color_via_translation(self, product_s25, color_translations):
        extracted = {
            "brand": "Samsung",
            "model_family": "Galaxy S25 Ultra",
            "storage": "256 Go",
            "color": "Black",
            "region": None,
        }
        mappings = {"color_translations": {"black": "Noir"}}
        score, details = score_match(extracted, product_s25, mappings)
        assert details["color"] == 15

    def test_partial_model_match(self, product_s25, color_translations):
        extracted = {
            "brand": "Samsung",
            "model_family": "Galaxy S25",
            "storage": "256 Go",
            "color": "Noir",
            "region": None,
        }
        mappings = {"color_translations": {}}
        score, details = score_match(extracted, product_s25, mappings)
        assert 0 < details["model_family"] < 40


class TestNormalizeStorage:
    def test_with_go(self):
        assert _normalize_storage("256 Go") == "256"

    def test_with_gb(self):
        assert _normalize_storage("128GB") == "128"

    def test_none(self):
        assert _normalize_storage(None) is None

    def test_empty(self):
        assert _normalize_storage("") is None


class TestFuzzyRatio:
    def test_identical(self):
        assert _fuzzy_ratio("Galaxy S25 Ultra", "Galaxy S25 Ultra") == 1.0

    def test_similar(self):
        ratio = _fuzzy_ratio("Galaxy S25 Ultra", "Galaxy S25")
        assert 0.5 < ratio < 1.0


# ---------------------------------------------------------------------------
# Tests: find_best_matches
# ---------------------------------------------------------------------------


class TestFindBestMatches:
    def test_finds_correct_product(self, product_s25, product_iphone, color_translations):
        extracted = {
            "brand": "Samsung",
            "model_family": "Galaxy S25 Ultra",
            "storage": "256 Go",
            "color": "Noir",
        }
        mappings = {"color_translations": {"black": "Noir"}}
        results = find_best_matches(extracted, [product_s25, product_iphone], mappings)
        assert len(results) >= 1
        assert results[0]["product_id"] == product_s25.id

    def test_no_match(self, product_s25):
        extracted = {"brand": "Xiaomi", "model_family": "14 Ultra", "storage": "256 Go"}
        mappings = {"color_translations": {}}
        results = find_best_matches(extracted, [product_s25], mappings)
        assert len(results) == 0

    def test_respects_top_n(self, brand_samsung, memory_256, color_noir):
        products = []
        for i in range(5):
            p = Product(model=f"Galaxy S2{i}", brand_id=brand_samsung.id, memory_id=memory_256.id)
            db.session.add(p)
            products.append(p)
        db.session.commit()

        extracted = {"brand": "Samsung", "model_family": "Galaxy S25", "storage": "256 Go"}
        mappings = {"color_translations": {}}
        results = find_best_matches(extracted, products, mappings, top_n=2)
        assert len(results) <= 2


# ---------------------------------------------------------------------------
# Tests: create_product_from_extraction
# ---------------------------------------------------------------------------


class TestCreateProductFromExtraction:
    def test_creates_product(self, brand_samsung, memory_256, color_noir, device_type):
        extracted = {
            "brand": "Samsung",
            "model_family": "Galaxy S25 Ultra",
            "storage": "256 Go",
            "color": "Noir",
            "device_type": "Smartphone",
            "region": None,
        }
        product = create_product_from_extraction(extracted, "SM-S938B 256 BLK")
        assert product.id is not None
        assert product.model == "Galaxy S25 Ultra"
        assert product.description == "[AUTO] SM-S938B 256 BLK"
        assert product.brand_id == brand_samsung.id
        assert product.memory_id == memory_256.id
        assert product.color_id == color_noir.id
        assert product.type_id == device_type.id

    def test_creates_missing_brand(self):
        extracted = {
            "brand": "Xiaomi",
            "model_family": "14 Ultra",
        }
        product = create_product_from_extraction(extracted, "Xiaomi 14 Ultra")
        assert product.brand_id is not None
        brand = Brand.query.get(product.brand_id)
        assert brand.brand == "Xiaomi"

    def test_creates_missing_color(self):
        extracted = {
            "brand": "",
            "color": "Rose Gold",
        }
        product = create_product_from_extraction(extracted, "test")
        assert product.color_id is not None
        color = Color.query.get(product.color_id)
        assert color.color == "Rose Gold"


# ---------------------------------------------------------------------------
# Tests: _make_attr_key
# ---------------------------------------------------------------------------


class TestMakeAttrKey:
    def test_canonical_key_is_stable(self):
        attrs = {"brand": "Samsung", "model_family": "Galaxy S25 Ultra", "storage": "256 Go", "color": "Noir", "region": "EU"}
        assert _make_attr_key(attrs) == _make_attr_key(attrs)

    def test_different_storage_units_produce_same_key(self):
        """256GB and 256 Go must produce identical keys."""
        a = {"brand": "Samsung", "model_family": "Galaxy S25 Ultra", "storage": "256GB", "color": "Noir", "region": "EU"}
        b = {"brand": "Samsung", "model_family": "Galaxy S25 Ultra", "storage": "256 Go", "color": "Noir", "region": "EU"}
        assert _make_attr_key(a) == _make_attr_key(b)

    def test_brand_case_insensitive(self):
        a = {"brand": "Samsung", "model_family": "Galaxy S25 Ultra", "storage": None, "color": None, "region": None}
        b = {"brand": "samsung", "model_family": "Galaxy S25 Ultra", "storage": None, "color": None, "region": None}
        assert _make_attr_key(a) == _make_attr_key(b)

    def test_null_region_treated_as_eu(self):
        a = {"brand": "Apple", "model_family": "iPhone 16", "storage": None, "color": None, "region": None}
        b = {"brand": "Apple", "model_family": "iPhone 16", "storage": None, "color": None, "region": "EU"}
        assert _make_attr_key(a) == _make_attr_key(b)

    def test_different_colors_produce_different_keys(self):
        a = {"brand": "Apple", "model_family": "iPhone 16", "storage": "128 Go", "color": "Noir", "region": "EU"}
        b = {"brand": "Apple", "model_family": "iPhone 16", "storage": "128 Go", "color": "Blanc", "region": "EU"}
        assert _make_attr_key(a) != _make_attr_key(b)

    def test_returns_none_when_brand_missing(self):
        attrs = {"brand": "", "model_family": "Galaxy S25 Ultra", "storage": "256 Go"}
        assert _make_attr_key(attrs) is None

    def test_returns_none_when_model_missing(self):
        attrs = {"brand": "Samsung", "model_family": "", "storage": "256 Go"}
        assert _make_attr_key(attrs) is None


# ---------------------------------------------------------------------------
# Tests: _find_fuzzy_cache_entry
# ---------------------------------------------------------------------------


class TestFindFuzzyCacheEntry:
    def test_finds_similar_entry_above_threshold(self, supplier):
        entry = LabelCache(
            supplier_id=supplier.id,
            normalized_label="samsung galaxy s25 ultra 256go noir",
            match_source="auto",
            match_score=95,
            extracted_attributes={"brand": "Samsung", "model_family": "Galaxy S25 Ultra"},
        )
        db.session.add(entry)
        db.session.commit()

        # Very similar label (only "noire" vs "noir", ratio > 0.92)
        result = _find_fuzzy_cache_entry(
            "samsung galaxy s25 ultra 256go noire", [entry]
        )
        assert result is not None
        assert result.id == entry.id

    def test_returns_none_when_below_threshold(self, supplier):
        entry = LabelCache(
            supplier_id=supplier.id,
            normalized_label="samsung galaxy s25 ultra 256go noir",
            match_source="auto",
            match_score=95,
            extracted_attributes={"brand": "Samsung"},
        )
        db.session.add(entry)
        db.session.commit()

        # Very different label
        result = _find_fuzzy_cache_entry(
            "apple iphone 16 pro 128go blanc", [entry]
        )
        assert result is None

    def test_returns_none_on_empty_candidates(self):
        result = _find_fuzzy_cache_entry("samsung galaxy s25 ultra 256go noir", [])
        assert result is None

    def test_returns_best_match_among_multiple(self, supplier):
        entry_close = LabelCache(
            supplier_id=supplier.id,
            normalized_label="samsung galaxy s25 ultra 256go noir",
            match_source="auto",
            match_score=95,
            extracted_attributes={"brand": "Samsung"},
        )
        entry_far = LabelCache(
            supplier_id=supplier.id,
            normalized_label="apple iphone 16 pro 512go blanc",
            match_source="auto",
            match_score=90,
            extracted_attributes={"brand": "Apple"},
        )
        db.session.add_all([entry_close, entry_far])
        db.session.commit()

        result = _find_fuzzy_cache_entry(
            "samsung galaxy s25 ultra 256go noire", [entry_close, entry_far]
        )
        assert result is not None
        assert result.id == entry_close.id


# ---------------------------------------------------------------------------
# Tests: run_matching_job
# ---------------------------------------------------------------------------


class TestRunMatchingJob:
    @pytest.fixture(autouse=True)
    def _set_api_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-dummy-key")

    @patch("utils.llm_matching.call_llm_extraction")
    def test_full_flow(
        self,
        mock_llm,
        supplier,
        product_s25,
        brand_samsung,
        memory_256,
        color_noir,
        device_type,
        color_translations,
    ):
        # Phase 1: create catalog entries to extract
        ti1 = SupplierCatalog(
            description="Samsung Galaxy S25 Ultra 256Go Noir",
            model="SM-S938B",
            quantity=5,
            selling_price=1200.0,
            ean="1234567890123",
            supplier_id=supplier.id,
        )
        ti2 = SupplierCatalog(
            description="Unknown Product XYZ",
            model="XYZ-123",
            quantity=1,
            selling_price=50.0,
            ean="9999999999999",
            supplier_id=supplier.id,
        )
        db.session.add_all([ti1, ti2])
        db.session.commit()

        # Mock LLM response (Phase 1 extraction of 2 labels)
        mock_llm.return_value = [
            {
                "brand": "Samsung",
                "model_family": "Galaxy S25 Ultra",
                "storage": "256 Go",
                "color": "Noir",
                "device_type": "Smartphone",
                "region": None,
                "confidence": 0.95,
            },
            {
                "brand": "Unknown",
                "model_family": "XYZ Product",
                "storage": None,
                "color": None,
                "device_type": "Accessoire",
                "region": None,
                "confidence": 0.3,
            },
        ]

        report = run_matching_job(supplier_id=supplier.id)

        # Phase 1: 2 labels extracted, 0 from cache
        assert report["from_cache"] == 0
        assert report["llm_calls"] == 1
        assert report["errors"] == 0
        # Phase 2: 1 product (product_s25) processed
        assert report["total_products"] == 1
        assert report["auto_matched"] + report["not_found"] + report["pending_review"] == 1
        assert "duration_seconds" in report
        assert "remaining" in report

    @patch("utils.llm_matching.call_llm_extraction")
    def test_limit_parameter(
        self,
        mock_llm,
        supplier,
        product_s25,
        brand_samsung,
        memory_256,
        color_noir,
        device_type,
        color_translations,
    ):
        """limit parameter should truncate labels_to_extract and report remaining."""
        for i in range(5):
            ti = SupplierCatalog(
                description=f"Product {i}",
                model=f"Model-{i}",
                quantity=1,
                selling_price=100.0 + i,
                ean=f"EAN-LIMIT-{i:05d}",
                supplier_id=supplier.id,
            )
            db.session.add(ti)
        db.session.commit()

        mock_llm.return_value = [
            {
                "brand": "Unknown",
                "model_family": f"Model-0",
                "storage": None,
                "color": None,
                "device_type": "Accessoire",
                "region": None,
                "confidence": 0.2,
            }
        ]

        report = run_matching_job(supplier_id=supplier.id, limit=1)
        assert report["remaining"] >= 0

    @patch("utils.llm_matching.call_llm_extraction")
    def test_cache_hit(
        self,
        mock_llm,
        supplier,
        product_s25,
        brand_samsung,
        memory_256,
        color_noir,
    ):
        # Pre-populate cache
        cache = LabelCache(
            supplier_id=supplier.id,
            normalized_label="samsung galaxy s25 ultra 256go noir",
            product_id=product_s25.id,
            match_score=95,
            match_source="auto",
        )
        db.session.add(cache)

        ti = SupplierCatalog(
            description="Samsung Galaxy S25 Ultra 256Go Noir",
            quantity=1,
            selling_price=1200.0,
            ean="1234567890123",
            supplier_id=supplier.id,
        )
        db.session.add(ti)
        db.session.commit()

        report = run_matching_job(supplier_id=supplier.id)

        assert report["from_cache"] == 1
        mock_llm.assert_not_called()

    @patch("utils.llm_matching.call_llm_extraction")
    def test_no_unmatched(self, mock_llm, supplier, product_s25):
        # Create a catalog entry with an existing SupplierProductRef
        ti = SupplierCatalog(
            description="Already matched",
            quantity=1,
            selling_price=100.0,
            ean="1111111111111",
            supplier_id=supplier.id,
        )
        db.session.add(ti)
        db.session.flush()

        ref = SupplierProductRef(
            supplier_id=supplier.id,
            product_id=product_s25.id,
            ean="1111111111111",
        )
        db.session.add(ref)
        db.session.commit()

        # Phase 1 extracts catalog labels regardless of matching status
        mock_llm.return_value = [
            {"brand": "Unknown", "model_family": "Already matched", "storage": None,
             "color": None, "device_type": None, "region": None, "confidence": 0.5}
        ]

        report = run_matching_job(supplier_id=supplier.id)

        # Phase 2: product_s25 already has a SupplierProductRef → not processed
        assert report["total_products"] == 0

    @patch("utils.llm_matching.call_llm_extraction")
    def test_auto_match_saves_reasoning(
        self,
        mock_llm,
        supplier,
        product_s25,
        brand_samsung,
        memory_256,
        color_noir,
        device_type,
        color_translations,
    ):
        """Phase 2 auto-match must save the score breakdown in match_reasoning."""
        ti = SupplierCatalog(
            description="Samsung Galaxy S25 Ultra 256Go Noir",
            model="SM-S938B",
            quantity=3,
            selling_price=1100.0,
            ean="1111222233334",
            supplier_id=supplier.id,
        )
        db.session.add(ti)
        db.session.commit()

        mock_llm.return_value = [{
            "brand": "Samsung",
            "model_family": "Galaxy S25 Ultra",
            "storage": "256 Go",
            "color": "Noir",
            "device_type": "Smartphone",
            "region": None,
            "confidence": 0.98,
        }]

        report = run_matching_job(supplier_id=supplier.id)

        if report["auto_matched"] == 1:
            cache = LabelCache.query.filter_by(
                supplier_id=supplier.id,
                match_source="auto",
            ).first()
            assert cache is not None
            assert cache.match_reasoning is not None
            assert "brand" in cache.match_reasoning
            assert "model_family" in cache.match_reasoning

    @patch("utils.llm_matching.call_llm_extraction")
    def test_cross_supplier_sharing(
        self,
        mock_llm,
        supplier,
        product_s25,
        brand_samsung,
        memory_256,
        color_noir,
    ):
        """Phase 1 must reuse extracted_attributes from another supplier
        when the same normalized_label is already cached, skipping the LLM call."""
        # Supplier B (different supplier with same label already cached)
        supplier_b = Supplier(name="PlusPos")
        db.session.add(supplier_b)
        db.session.commit()

        # Pre-populate cache for supplier_b with the same normalized label
        shared_attrs = {
            "brand": "Samsung",
            "model_family": "Galaxy S25 Ultra",
            "storage": "256 Go",
            "color": "Noir",
            "device_type": "Smartphone",
            "region": None,
            "raw_label": "Samsung Galaxy S25 Ultra 256Go Noir",
        }
        cache_b = LabelCache(
            supplier_id=supplier_b.id,
            normalized_label="samsung galaxy s25 ultra 256go noir",
            match_source="auto",
            match_score=95,
            extracted_attributes=shared_attrs,
        )
        db.session.add(cache_b)

        # Supplier A (our test supplier) has the same label but no cache entry
        ti = SupplierCatalog(
            description="Samsung Galaxy S25 Ultra 256Go Noir",
            quantity=1,
            selling_price=1100.0,
            ean="1234567890123",
            supplier_id=supplier.id,
        )
        db.session.add(ti)
        db.session.commit()

        report = run_matching_job(supplier_id=supplier.id)

        # LLM must NOT be called — attrs shared from supplier_b
        mock_llm.assert_not_called()
        assert report["cross_supplier_hits"] == 1
        assert report["from_cache"] == 1

        # A new LabelCache entry must have been created for supplier A
        new_cache = LabelCache.query.filter_by(
            supplier_id=supplier.id,
            normalized_label="samsung galaxy s25 ultra 256go noir",
        ).first()
        assert new_cache is not None
        assert new_cache.extracted_attributes is not None
        assert new_cache.extracted_attributes.get("brand") == "Samsung"

    @patch("utils.llm_matching.call_llm_extraction")
    def test_fuzzy_fallback(
        self,
        mock_llm,
        supplier,
        product_s25,
        brand_samsung,
        memory_256,
        color_noir,
    ):
        """Phase 1 must reuse a similar cache entry (fuzzy ratio > 0.92) for the
        same supplier, avoiding a redundant LLM call."""
        original_attrs = {
            "brand": "Samsung",
            "model_family": "Galaxy S25 Ultra",
            "storage": "256 Go",
            "color": "Noir",
            "device_type": "Smartphone",
            "region": None,
            "raw_label": "Samsung Galaxy S25 Ultra 256Go Noir",
        }
        # Existing cache entry for the SAME supplier with a very similar label
        existing_cache = LabelCache(
            supplier_id=supplier.id,
            normalized_label="samsung galaxy s25 ultra 256go noir",
            match_source="auto",
            match_score=95,
            extracted_attributes=original_attrs,
        )
        db.session.add(existing_cache)

        # New catalog entry with a slightly different label (e.g. "noire" vs "noir")
        ti = SupplierCatalog(
            description="Samsung Galaxy S25 Ultra 256Go Noire",
            quantity=1,
            selling_price=1100.0,
            ean="9876543210987",
            supplier_id=supplier.id,
        )
        db.session.add(ti)
        db.session.commit()

        report = run_matching_job(supplier_id=supplier.id)

        # LLM must NOT be called — attrs reused from the fuzzy-matched entry
        mock_llm.assert_not_called()
        assert report["fuzzy_hits"] == 1

        # A new LabelCache entry must exist for the new normalized label
        new_label = normalize_label("Samsung Galaxy S25 Ultra 256Go Noire")
        new_cache = LabelCache.query.filter_by(
            supplier_id=supplier.id,
            normalized_label=new_label,
        ).first()
        assert new_cache is not None
        assert new_cache.extracted_attributes.get("brand") == "Samsung"

    @patch("utils.llm_matching.call_llm_extraction")
    def test_attr_based_cross_supplier_sharing(
        self,
        mock_llm,
        supplier,
        product_s25,
        brand_samsung,
        memory_256,
        color_noir,
        device_type,
        color_translations,
    ):
        """After LLM extracts attributes for PlusPos's label, if those attributes
        match an already-validated entry from Yukatel (product_id set), PlusPos
        gets product_id assigned directly without Phase 2 scoring."""
        # Yukatel already has a matched cache entry for Galaxy S25 Ultra 256Go Noir
        yukatel_attrs = {
            "brand": "Samsung",
            "model_family": "Galaxy S25 Ultra",
            "storage": "256 Go",
            "color": "Noir",
            "device_type": "Smartphone",
            "region": None,
            "raw_label": "SM-S938B 256 BLK",
        }
        cache_yukatel = LabelCache(
            supplier_id=supplier.id,
            normalized_label="sm s938b 256go blk",
            product_id=product_s25.id,
            match_score=95,
            match_source="auto",
            extracted_attributes=yukatel_attrs,
        )
        db.session.add(cache_yukatel)

        # PlusPos (second supplier) has a completely different label for the same product
        supplier_pluspos = Supplier(name="PlusPos")
        db.session.add(supplier_pluspos)
        db.session.commit()

        ti = SupplierCatalog(
            description="Samsung Galaxy S25 Ultra 256Go Noir",
            quantity=2,
            selling_price=1050.0,
            ean="5551234567890",
            supplier_id=supplier_pluspos.id,
        )
        db.session.add(ti)
        db.session.commit()

        # LLM extracts the same logical attributes from PlusPos's different label
        mock_llm.return_value = [{
            "brand": "Samsung",
            "model_family": "Galaxy S25 Ultra",
            "storage": "256 Go",
            "color": "Noir",
            "device_type": "Smartphone",
            "region": None,
            "confidence": 0.97,
        }]

        report = run_matching_job(supplier_id=supplier_pluspos.id)

        # LLM was called once (PlusPos's label needed extraction)
        assert mock_llm.call_count == 1
        # But Phase 2 was bypassed via attr-based sharing
        assert report["attr_share_hits"] == 1

        # PlusPos's LabelCache entry must have product_id assigned directly
        new_cache = LabelCache.query.filter_by(
            supplier_id=supplier_pluspos.id,
        ).first()
        assert new_cache is not None
        assert new_cache.product_id == product_s25.id
        assert new_cache.match_source == "attr_share"

        # SupplierProductRef must have been created for PlusPos
        ref = SupplierProductRef.query.filter_by(
            supplier_id=supplier_pluspos.id,
            product_id=product_s25.id,
        ).first()
        assert ref is not None
