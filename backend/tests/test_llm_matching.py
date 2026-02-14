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
    TemporaryImport,
    db,
)
from utils.llm_matching import (
    _fuzzy_ratio,
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
        assert normalize_label("Apple iPhone 15 128GB - Black") == "apple iphone 15 128gb black"

    def test_multiple_spaces(self):
        assert normalize_label("  Samsung   Galaxy  S25  ") == "samsung galaxy s25"

    def test_special_chars(self):
        assert normalize_label("SM-S938B/DS (256GB)") == "sm s938b ds 256gb"

    def test_empty(self):
        assert normalize_label("") == ""

    def test_unicode(self):
        result = normalize_label("Écran OLED")
        assert result == "écran oled"


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

    def test_color_synonyms(self, color_noir, color_translations):
        ctx = build_context()
        assert "Black" in ctx["colors"]["Noir"]
        assert "Midnight" in ctx["colors"]["Noir"]


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


# ---------------------------------------------------------------------------
# Tests: call_llm_extraction
# ---------------------------------------------------------------------------


class TestCallLlmExtraction:
    def _make_mock_anthropic(self):
        mock_module = MagicMock()
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

    def test_brand_mismatch_returns_zero(self, product_s25):
        extracted = {"brand": "Apple", "model_family": "Galaxy S25 Ultra", "storage": "256 Go"}
        score, details = score_match(extracted, product_s25, {})
        assert score == 0
        assert details.get("disqualified") == "brand_mismatch"

    def test_storage_mismatch_returns_zero(self, product_s25):
        extracted = {"brand": "Samsung", "model_family": "Galaxy S25 Ultra", "storage": "128 Go"}
        score, details = score_match(extracted, product_s25, {})
        assert score == 0
        assert details.get("disqualified") == "storage_mismatch"

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
# Tests: run_matching_job
# ---------------------------------------------------------------------------


class TestRunMatchingJob:
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
        # Create unmatched temp imports
        ti1 = TemporaryImport(
            description="Samsung Galaxy S25 Ultra 256Go Noir",
            model="SM-S938B",
            quantity=5,
            selling_price=1200.0,
            ean="1234567890123",
            supplier_id=supplier.id,
        )
        ti2 = TemporaryImport(
            description="Unknown Product XYZ",
            model="XYZ-123",
            quantity=1,
            selling_price=50.0,
            ean="9999999999999",
            supplier_id=supplier.id,
        )
        db.session.add_all([ti1, ti2])
        db.session.commit()

        # Mock LLM response
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

        assert report["total_labels"] == 2
        assert report["from_cache"] == 0
        assert report["llm_calls"] == 1
        assert report["auto_matched"] + report["auto_created"] + report["pending_review"] == 2
        assert report["errors"] == 0
        assert "duration_seconds" in report

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

        ti = TemporaryImport(
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
        # Create a matched import (has SupplierProductRef)
        ti = TemporaryImport(
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

        report = run_matching_job(supplier_id=supplier.id)

        assert report["total_labels"] == 0
        mock_llm.assert_not_called()
