"""Tests for Odoo synchronization routes and sync engine."""

import json
from unittest.mock import MagicMock, patch

import pytest
from models import (
    Brand,
    Color,
    ColorTranslation,
    DeviceType,
    InternalProduct,
    MemoryOption,
    NormeOption,
    OdooConfig,
    OdooSyncJob,
    Product,
    ProductCalculation,
    RAMOption,
    Supplier,
    SupplierProductRef,
    db,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def odoo_config():
    config = OdooConfig(
        url="https://odoo.test.com",
        database="test_db",
        login="admin",
        password="secret",
    )
    db.session.add(config)
    db.session.commit()
    return config


# ---------------------------------------------------------------------------
# Config routes
# ---------------------------------------------------------------------------
class TestOdooConfig:
    def test_get_config_empty(self, client, admin_headers):
        rv = client.get("/odoo/config", headers=admin_headers)
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["configured"] is False

    def test_get_config_existing(self, client, admin_headers, odoo_config):
        rv = client.get("/odoo/config", headers=admin_headers)
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["configured"] is True
        assert data["url"] == "https://odoo.test.com"
        assert data["password"] == "__UNCHANGED__"

    def test_put_config_create(self, client, admin_headers):
        rv = client.put(
            "/odoo/config",
            data=json.dumps(
                {
                    "url": "https://odoo.example.com",
                    "database": "mydb",
                    "login": "user",
                    "password": "pass",
                }
            ),
            headers=admin_headers,
        )
        assert rv.status_code == 200
        config = OdooConfig.query.first()
        assert config is not None
        assert config.url == "https://odoo.example.com"

    def test_put_config_update_keeps_password(self, client, admin_headers, odoo_config):
        rv = client.put(
            "/odoo/config",
            data=json.dumps(
                {
                    "url": "https://new-url.com",
                    "database": "test_db",
                    "login": "admin",
                    "password": "__UNCHANGED__",
                }
            ),
            headers=admin_headers,
        )
        assert rv.status_code == 200
        config = OdooConfig.query.first()
        assert config.url == "https://new-url.com"
        assert config.password == "secret"  # unchanged

    def test_put_config_missing_fields(self, client, admin_headers):
        rv = client.put(
            "/odoo/config",
            data=json.dumps({"url": "https://x.com"}),
            headers=admin_headers,
        )
        assert rv.status_code == 400


# ---------------------------------------------------------------------------
# Test connection
# ---------------------------------------------------------------------------
class TestOdooConnection:
    def test_test_no_config(self, client, admin_headers):
        rv = client.post("/odoo/test", headers=admin_headers)
        assert rv.status_code == 400

    @patch("routes.odoo.OdooClient")
    def test_test_success(self, mock_cls, client, admin_headers, odoo_config):
        instance = MagicMock()
        instance.test_connection.return_value = {
            "server_version": "17.0",
            "uid": 2,
            "product_count": 42,
        }
        mock_cls.return_value = instance

        rv = client.post("/odoo/test", headers=admin_headers)
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["server_version"] == "17.0"
        assert data["product_count"] == 42

    @patch("routes.odoo.OdooClient")
    def test_test_failure(self, mock_cls, client, admin_headers, odoo_config):
        instance = MagicMock()
        instance.test_connection.side_effect = ConnectionError("timeout")
        mock_cls.return_value = instance

        rv = client.post("/odoo/test", headers=admin_headers)
        assert rv.status_code == 500


# ---------------------------------------------------------------------------
# Sync trigger
# ---------------------------------------------------------------------------
class TestOdooSync:
    def test_sync_no_config(self, client, admin_headers):
        rv = client.post("/odoo/sync", headers=admin_headers)
        assert rv.status_code == 400

    @patch("routes.odoo.run_odoo_sync")
    def test_sync_starts(self, mock_sync, client, admin_headers, odoo_config):
        rv = client.post("/odoo/sync", headers=admin_headers)
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["status"] == "running"
        assert "job_id" in data

    @patch("routes.odoo.run_odoo_sync")
    def test_sync_conflict(self, mock_sync, client, admin_headers, odoo_config):
        job = OdooSyncJob(status="running")
        db.session.add(job)
        db.session.commit()

        rv = client.post("/odoo/sync", headers=admin_headers)
        assert rv.status_code == 409


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------
class TestOdooAccess:
    def test_client_forbidden(self, client, client_headers):
        rv = client.get("/odoo/config", headers=client_headers)
        assert rv.status_code == 403

    def test_client_forbidden_sync(self, client, client_headers):
        rv = client.post("/odoo/sync", headers=client_headers)
        assert rv.status_code == 403


# ---------------------------------------------------------------------------
# Jobs history
# ---------------------------------------------------------------------------
class TestOdooJobs:
    def test_list_jobs_empty(self, client, admin_headers):
        rv = client.get("/odoo/jobs", headers=admin_headers)
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_list_jobs(self, client, admin_headers):
        job = OdooSyncJob(status="success", trigger="manual", created_count=5)
        db.session.add(job)
        db.session.commit()

        rv = client.get("/odoo/jobs", headers=admin_headers)
        assert rv.status_code == 200
        data = rv.get_json()
        assert len(data) == 1
        assert data[0]["created_count"] == 5

    def test_get_job_detail(self, client, admin_headers):
        job = OdooSyncJob(
            status="success",
            trigger="manual",
            report_created=[{"odoo_id": "1", "name": "Test"}],
        )
        db.session.add(job)
        db.session.commit()

        rv = client.get(f"/odoo/jobs/{job.id}", headers=admin_headers)
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["report_created"] is not None
        assert len(data["report_created"]) == 1

    def test_get_job_not_found(self, client, admin_headers):
        rv = client.get("/odoo/jobs/99999", headers=admin_headers)
        assert rv.status_code == 404


# ---------------------------------------------------------------------------
# Auto-sync settings
# ---------------------------------------------------------------------------
class TestOdooAutoSync:
    def test_auto_sync_no_config(self, client, admin_headers):
        rv = client.put(
            "/odoo/auto-sync",
            data=json.dumps({"enabled": True}),
            headers=admin_headers,
        )
        assert rv.status_code == 400

    def test_auto_sync_enable(self, client, admin_headers, odoo_config):
        rv = client.put(
            "/odoo/auto-sync",
            data=json.dumps({"enabled": True, "interval_minutes": 60}),
            headers=admin_headers,
        )
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["auto_sync_enabled"] is True
        assert data["auto_sync_interval_minutes"] == 60

    def test_auto_sync_interval_too_short(self, client, admin_headers, odoo_config):
        rv = client.put(
            "/odoo/auto-sync",
            data=json.dumps({"interval_minutes": 5}),
            headers=admin_headers,
        )
        assert rv.status_code == 400


# ---------------------------------------------------------------------------
# Sync engine unit test
# ---------------------------------------------------------------------------
class TestProcessSingleProduct:
    def test_create_new_product(self, app):
        from utils.odoo_sync import _process_single_product

        odoo_product = {
            "id": 100,
            "name": "iPhone 15 Pro",
            "barcode": "1234567890123",
            "default_code": "IP15PRO",
            "list_price": 999.0,
            "product_brand_id": [1, "Apple"],
            "categ_id": [5, "All / Smartphones"],
            "product_template_attribute_value_ids": [],
        }

        status, item = _process_single_product(
            odoo_product,
            attr_values_cache={},
            brand_lookup={},
            color_lookup={},
            memory_lookup={},
            ram_lookup={},
            norme_lookup={},
            type_lookup={},
            internal_by_odoo_id={},
            product_by_ean={},
            product_by_pn={},
        )
        assert status == "created"
        assert item["name"] == "iPhone 15 Pro"

        # Verify product was created
        product = Product.query.filter_by(ean="1234567890123").first()
        assert product is not None
        assert product.model == "iPhone 15 Pro"
        assert product.description == "iPhone 15 Pro"
        assert product.recommended_price == 999.0

        # Verify brand was created
        brand = Brand.query.filter_by(brand="Apple").first()
        assert brand is not None
        assert product.brand_id == brand.id

        # Verify device type was created
        dtype = DeviceType.query.filter_by(type="Smartphones").first()
        assert dtype is not None
        assert product.type_id == dtype.id

    def test_update_existing_linked_product(self, app):
        from utils.odoo_sync import _process_single_product

        # Create existing product + link
        product = Product(model="Old Name", ean="9999999999999")
        db.session.add(product)
        db.session.flush()
        link = InternalProduct(product_id=product.id, odoo_id="200")
        db.session.add(link)
        db.session.commit()

        odoo_product = {
            "id": 200,
            "name": "New Name",
            "barcode": "9999999999999",
            "default_code": "",
            "list_price": 500.0,
            "product_brand_id": False,
            "categ_id": False,
            "product_template_attribute_value_ids": [],
        }

        status, _ = _process_single_product(
            odoo_product,
            attr_values_cache={},
            brand_lookup={},
            color_lookup={},
            memory_lookup={},
            ram_lookup={},
            norme_lookup={},
            type_lookup={},
            internal_by_odoo_id={"200": link},
            product_by_ean={"9999999999999": product},
            product_by_pn={},
        )
        assert status == "updated"
        assert product.model == "New Name"
        assert product.description == "New Name"
        assert product.recommended_price == 500.0
        db.session.commit()

    def test_unchanged_product(self, app):
        from utils.odoo_sync import _process_single_product

        product = Product(
            model="Same",
            description="Same",
            ean="1111111111111",
            recommended_price=100.0,
        )
        db.session.add(product)
        db.session.flush()
        link = InternalProduct(product_id=product.id, odoo_id="300")
        db.session.add(link)
        db.session.commit()

        odoo_product = {
            "id": 300,
            "name": "Same",
            "barcode": "1111111111111",
            "default_code": None,
            "list_price": 100.0,
            "product_brand_id": False,
            "categ_id": False,
            "product_template_attribute_value_ids": [],
        }

        status, _ = _process_single_product(
            odoo_product,
            attr_values_cache={},
            brand_lookup={},
            color_lookup={},
            memory_lookup={},
            ram_lookup={},
            norme_lookup={},
            type_lookup={},
            internal_by_odoo_id={"300": link},
            product_by_ean={"1111111111111": product},
            product_by_pn={},
        )
        assert status == "unchanged"


# ---------------------------------------------------------------------------
# Orphan deletion tests
# ---------------------------------------------------------------------------
class TestOrphanDeletion:
    """Tests for orphan product deletion during Odoo sync."""

    def test_orphan_product_deleted(self, app):
        """Product+InternalProduct+ProductCalculation are deleted for orphans."""
        from utils.odoo_sync import _delete_orphaned_products

        product = Product(model="Orphan Phone", ean="0000000000001")
        db.session.add(product)
        db.session.flush()
        link = InternalProduct(product_id=product.id, odoo_id="999")
        db.session.add(link)
        calc = ProductCalculation(
            product_id=product.id, price=100, tcp=90, marge4_5=10,
            prixht_tcp_marge4_5=80, prixht_marge4_5=85, prixht_max=95,
        )
        db.session.add(calc)
        db.session.commit()
        product_id = product.id

        internal_by_odoo_id = {"999": link}
        seen_odoo_ids = set()  # empty → 999 is orphaned
        counters = {"deleted": 0, "error": 0}
        reports = {"deleted": [], "errors": []}

        _delete_orphaned_products(internal_by_odoo_id, seen_odoo_ids, counters, reports)
        db.session.commit()

        assert counters["deleted"] == 1
        assert len(reports["deleted"]) == 1
        assert reports["deleted"][0]["odoo_id"] == "999"

        assert db.session.get(Product, product_id) is None
        assert InternalProduct.query.filter_by(odoo_id="999").first() is None
        assert ProductCalculation.query.filter_by(product_id=product_id).first() is None

    def test_orphan_preserves_supplier_ref(self, app):
        """SupplierProductRef.product_id is set to NULL when product is orphaned."""
        from utils.odoo_sync import _delete_orphaned_products

        supplier = Supplier(name="Test Supplier")
        db.session.add(supplier)
        db.session.flush()

        product = Product(model="Orphan Phone 2", ean="0000000000002")
        db.session.add(product)
        db.session.flush()
        link = InternalProduct(product_id=product.id, odoo_id="888")
        db.session.add(link)
        ref = SupplierProductRef(
            supplier_id=supplier.id,
            product_id=product.id,
            ean="0000000000002",
        )
        db.session.add(ref)
        db.session.commit()
        ref_id = ref.id

        internal_by_odoo_id = {"888": link}
        seen_odoo_ids = set()
        counters = {"deleted": 0, "error": 0}
        reports = {"deleted": [], "errors": []}

        _delete_orphaned_products(internal_by_odoo_id, seen_odoo_ids, counters, reports)
        db.session.commit()

        ref = db.session.get(SupplierProductRef, ref_id)
        assert ref is not None
        assert ref.product_id is None

    def test_non_odoo_products_not_deleted(self, app):
        """Products without InternalProduct link are not deleted."""
        from utils.odoo_sync import _delete_orphaned_products

        product = Product(model="Standalone Product", ean="0000000000003")
        db.session.add(product)
        db.session.commit()
        product_id = product.id

        # No entries in internal_by_odoo_id → nothing to orphan
        internal_by_odoo_id = {}
        seen_odoo_ids = set()
        counters = {"deleted": 0, "error": 0}
        reports = {"deleted": [], "errors": []}

        _delete_orphaned_products(internal_by_odoo_id, seen_odoo_ids, counters, reports)
        db.session.commit()

        assert db.session.get(Product, product_id) is not None
        assert counters["deleted"] == 0

    def test_seen_product_not_deleted(self, app):
        """Products seen during sync are NOT deleted."""
        from utils.odoo_sync import _delete_orphaned_products

        product = Product(model="Still In Odoo", ean="0000000000004")
        db.session.add(product)
        db.session.flush()
        link = InternalProduct(product_id=product.id, odoo_id="777")
        db.session.add(link)
        db.session.commit()
        product_id = product.id

        internal_by_odoo_id = {"777": link}
        seen_odoo_ids = {"777"}  # seen → not orphaned
        counters = {"deleted": 0, "error": 0}
        reports = {"deleted": [], "errors": []}

        _delete_orphaned_products(internal_by_odoo_id, seen_odoo_ids, counters, reports)
        db.session.commit()

        assert db.session.get(Product, product_id) is not None
        assert counters["deleted"] == 0


# ---------------------------------------------------------------------------
# Name-based fallback parsing tests
# ---------------------------------------------------------------------------
class TestParseNameFallback:
    """Tests for _parse_name_fallback() substring matching."""

    def test_parse_name_extracts_brand(self, app):
        """Brand is extracted from product name when not resolved by Odoo."""
        from utils.odoo_sync import _parse_name_fallback

        brand = Brand(brand="Apple")
        db.session.add(brand)
        db.session.flush()

        result, matched = _parse_name_fallback(
            "Apple Iphone 15 128Gb Black",
            brand_id=None, color_id=None, memory_id=None,
            ram_id=None, norme_id=None, type_id=None,
            brand_lookup={"apple": brand.id},
            color_lookup={}, color_translation_lookup={},
            memory_lookup={}, ram_lookup={},
            norme_lookup={}, type_lookup={},
        )
        assert result["brand_id"] == brand.id
        assert "apple" in matched

    def test_parse_name_extracts_color_translation(self, app):
        """Color is found via ColorTranslation synonyms (e.g. 'black' → Noir)."""
        from utils.odoo_sync import _parse_name_fallback

        color = Color(color="Noir")
        db.session.add(color)
        db.session.flush()
        ct = ColorTranslation(
            color_source="black", color_target="Noir", color_target_id=color.id,
        )
        db.session.add(ct)
        db.session.flush()

        result, matched = _parse_name_fallback(
            "Samsung Galaxy S24 Black",
            brand_id=None, color_id=None, memory_id=None,
            ram_id=None, norme_id=None, type_id=None,
            brand_lookup={}, color_lookup={"noir": color.id},
            color_translation_lookup={"black": color.id},
            memory_lookup={}, ram_lookup={},
            norme_lookup={}, type_lookup={},
        )
        assert result["color_id"] == color.id
        assert "black" in matched

    def test_parse_name_extracts_memory(self, app):
        """Memory capacity is extracted from product name."""
        from utils.odoo_sync import _parse_name_fallback

        mem = MemoryOption(memory="128GB", tcp_value=0)
        db.session.add(mem)
        db.session.flush()

        result, matched = _parse_name_fallback(
            "Iphone 15 128gb Noir",
            brand_id=None, color_id=None, memory_id=None,
            ram_id=None, norme_id=None, type_id=None,
            brand_lookup={}, color_lookup={},
            color_translation_lookup={},
            memory_lookup={"128gb": mem.id}, ram_lookup={},
            norme_lookup={}, type_lookup={},
        )
        assert result["memory_id"] == mem.id
        assert "128gb" in matched

    def test_parse_name_no_override(self, app):
        """Fields already resolved by Odoo are not overridden by fallback."""
        from utils.odoo_sync import _parse_name_fallback

        brand_apple = Brand(brand="Apple")
        brand_samsung = Brand(brand="Samsung")
        db.session.add_all([brand_apple, brand_samsung])
        db.session.flush()

        result, matched = _parse_name_fallback(
            "Samsung Galaxy S24",
            brand_id=brand_apple.id,  # already resolved
            color_id=None, memory_id=None,
            ram_id=None, norme_id=None, type_id=None,
            brand_lookup={"samsung": brand_samsung.id, "apple": brand_apple.id},
            color_lookup={}, color_translation_lookup={},
            memory_lookup={}, ram_lookup={},
            norme_lookup={}, type_lookup={},
        )
        # brand_id was already set, so it should NOT appear in result
        assert "brand_id" not in result

    def test_parse_name_longest_match(self, app):
        """Longest key matches first: 'bleu nuit' before 'bleu'."""
        from utils.odoo_sync import _parse_name_fallback

        bleu = Color(color="Bleu")
        bleu_nuit = Color(color="Bleu Nuit")
        db.session.add_all([bleu, bleu_nuit])
        db.session.flush()

        result, matched = _parse_name_fallback(
            "Samsung Galaxy S24 Bleu Nuit 256Gb",
            brand_id=None, color_id=None, memory_id=None,
            ram_id=None, norme_id=None, type_id=None,
            brand_lookup={}, color_lookup={
                "bleu": bleu.id, "bleu nuit": bleu_nuit.id,
            },
            color_translation_lookup={},
            memory_lookup={}, ram_lookup={},
            norme_lookup={}, type_lookup={},
        )
        assert result["color_id"] == bleu_nuit.id
        assert "bleu nuit" in matched

    def test_parse_name_skips_numeric_ram(self, app):
        """Purely numeric keys like '12' are not matched — avoids 'iPhone 12' → RAM 12."""
        from utils.odoo_sync import _parse_name_fallback

        ram = RAMOption(ram="12")
        db.session.add(ram)
        db.session.flush()

        result, matched = _parse_name_fallback(
            "Apple iPhone 12 128GB Purple",
            brand_id=None, color_id=None, memory_id=None,
            ram_id=None, norme_id=None, type_id=None,
            brand_lookup={}, color_lookup={},
            color_translation_lookup={},
            memory_lookup={}, ram_lookup={"12": ram.id},
            norme_lookup={}, type_lookup={},
        )
        # "12" is purely numeric → should NOT match as RAM
        assert result.get("ram_id") is None
        assert "12" not in matched

    def test_parse_name_word_boundary(self, app):
        """Word boundaries prevent partial matches (e.g. 'lg' inside 'flagship')."""
        from utils.odoo_sync import _parse_name_fallback

        brand_lg = Brand(brand="LG")
        db.session.add(brand_lg)
        db.session.flush()

        result, matched = _parse_name_fallback(
            "Flagship Phone 128GB",
            brand_id=None, color_id=None, memory_id=None,
            ram_id=None, norme_id=None, type_id=None,
            brand_lookup={"lg": brand_lg.id},
            color_lookup={}, color_translation_lookup={},
            memory_lookup={}, ram_lookup={},
            norme_lookup={}, type_lookup={},
        )
        # "lg" is inside "flagship" but not a standalone word → should NOT match
        assert result.get("brand_id") is None


# ---------------------------------------------------------------------------
# Model name extraction tests
# ---------------------------------------------------------------------------
class TestExtractModelName:
    """Tests for _extract_model_name() function."""

    def test_basic_extraction(self):
        from utils.odoo_sync import _extract_model_name

        result = _extract_model_name(
            "Apple iPhone 15 128GB Black",
            ["Apple", "128GB", "Black"],
        )
        assert result == "iPhone 15"

    def test_case_insensitive(self):
        from utils.odoo_sync import _extract_model_name

        result = _extract_model_name(
            "APPLE iPhone 15 PRO 256gb NOIR",
            ["apple", "256GB", "noir"],
        )
        assert result == "iPhone 15 PRO"

    def test_fallback_if_empty(self):
        """If removing all parts leaves an empty string, return the original name."""
        from utils.odoo_sync import _extract_model_name

        result = _extract_model_name("Apple", ["Apple"])
        assert result == "Apple"

    def test_longest_match_first(self):
        """Longest parts are removed first to avoid partial matches."""
        from utils.odoo_sync import _extract_model_name

        result = _extract_model_name(
            "Samsung Galaxy S24 Ultra 512GB",
            ["Samsung", "512GB"],
        )
        assert result == "Galaxy S24 Ultra"

    def test_word_boundary_safety(self):
        """Word boundaries prevent partial matches inside compound words."""
        from utils.odoo_sync import _extract_model_name

        result = _extract_model_name(
            "BlackBerry Key2 Black",
            ["Black"],
        )
        # "Black" should match standalone "Black" not "BlackBerry"
        assert "BlackBerry" in result
        assert result == "BlackBerry Key2"

    def test_empty_parts_ignored(self):
        from utils.odoo_sync import _extract_model_name

        result = _extract_model_name(
            "Apple iPhone 15", ["Apple", "", None],
        )
        assert result == "iPhone 15"

    def test_numeric_parts_preserved(self):
        """Purely numeric parts are not removed — they are likely model numbers."""
        from utils.odoo_sync import _extract_model_name

        result = _extract_model_name(
            "Apple iPhone 12 128GB Purple",
            ["Apple", "12", "128GB", "Purple"],
        )
        # "12" is purely numeric → skipped, model number preserved
        assert result == "iPhone 12"


# ---------------------------------------------------------------------------
# Integration: model extraction in _process_single_product
# ---------------------------------------------------------------------------
class TestModelExtraction:
    """Integration tests for model name extraction during product processing."""

    def test_extraction_with_odoo_attributes(self, app):
        """Model name is extracted when attributes come from Odoo."""
        from utils.odoo_sync import _process_single_product

        # Pre-create references so _find_or_create finds them
        mem = MemoryOption(memory="128GB", tcp_value=0)
        color = Color(color="Black")
        db.session.add_all([mem, color])
        db.session.flush()

        odoo_product = {
            "id": 500,
            "name": "Apple iPhone 15 128GB Black",
            "barcode": "5000000000001",
            "default_code": "IP15-128-BK",
            "list_price": 899.0,
            "product_brand_id": [1, "Apple"],
            "categ_id": [5, "All / Smartphones"],
            "product_template_attribute_value_ids": [10, 20],
        }
        attr_values_cache = {
            10: {"id": 10, "name": "128GB", "attribute_id": [1, "Memory"]},
            20: {"id": 20, "name": "Black", "attribute_id": [2, "Color"]},
        }

        status, _ = _process_single_product(
            odoo_product,
            attr_values_cache=attr_values_cache,
            brand_lookup={},
            color_lookup={"black": color.id},
            memory_lookup={"128gb": mem.id},
            ram_lookup={},
            norme_lookup={},
            type_lookup={},
            internal_by_odoo_id={},
            product_by_ean={},
            product_by_pn={},
        )
        assert status == "created"
        product = Product.query.filter_by(ean="5000000000001").first()
        assert product is not None
        assert product.description == "Apple iPhone 15 128Go Black"
        assert product.model == "iPhone 15"

    def test_extraction_with_fallback(self, app):
        """Model name is extracted when attributes come from name fallback."""
        from utils.odoo_sync import _process_single_product

        brand = Brand(brand="Samsung")
        color = Color(color="Noir")
        mem = MemoryOption(memory="256GB", tcp_value=0)
        db.session.add_all([brand, color, mem])
        db.session.flush()

        odoo_product = {
            "id": 501,
            "name": "Samsung Galaxy S24 256GB Noir",
            "barcode": "5000000000002",
            "default_code": "",
            "list_price": 799.0,
            "product_brand_id": False,
            "categ_id": False,
            "product_template_attribute_value_ids": [],
        }

        status, _ = _process_single_product(
            odoo_product,
            attr_values_cache={},
            brand_lookup={"samsung": brand.id},
            color_lookup={"noir": color.id},
            memory_lookup={"256gb": mem.id},
            ram_lookup={},
            norme_lookup={},
            type_lookup={},
            internal_by_odoo_id={},
            product_by_ean={},
            product_by_pn={},
        )
        assert status == "created"
        product = Product.query.filter_by(ean="5000000000002").first()
        assert product is not None
        assert product.description == "Samsung Galaxy S24 256Go Noir"
        assert product.model == "Galaxy S24"

    def test_numeric_model_number_preserved(self, app):
        """Model number '12' in 'iPhone 12' is not removed or matched as RAM."""
        from utils.odoo_sync import _process_single_product

        ram = RAMOption(ram="12")
        mem = MemoryOption(memory="128GB", tcp_value=0)
        color = Color(color="Purple")
        db.session.add_all([ram, mem, color])
        db.session.flush()

        odoo_product = {
            "id": 502,
            "name": "Apple iPhone 12 128GB Purple",
            "barcode": "5000000000003",
            "default_code": "",
            "list_price": 699.0,
            "product_brand_id": [1, "Apple"],
            "categ_id": False,
            "product_template_attribute_value_ids": [30, 40],
        }
        attr_values_cache = {
            30: {"id": 30, "name": "128GB", "attribute_id": [1, "Memory"]},
            40: {"id": 40, "name": "Purple", "attribute_id": [2, "Color"]},
        }

        status, _ = _process_single_product(
            odoo_product,
            attr_values_cache=attr_values_cache,
            brand_lookup={},
            color_lookup={"purple": color.id},
            memory_lookup={"128gb": mem.id},
            ram_lookup={"12": ram.id},
            norme_lookup={},
            type_lookup={},
            internal_by_odoo_id={},
            product_by_ean={},
            product_by_pn={},
        )
        assert status == "created"
        product = Product.query.filter_by(ean="5000000000003").first()
        assert product is not None
        assert product.model == "iPhone 12"
        assert product.description == "Apple iPhone 12 128Go Purple"
        # RAM should NOT be assigned (no RAM/Storage pattern, fallback skips numeric "12")
        assert product.RAM_id is None

    def test_ram_extracted_from_ram_storage_pattern(self, app):
        """RAM is extracted from the X/YGo pattern in product name."""
        from utils.odoo_sync import _process_single_product

        ram_opt = RAMOption(ram="8 Go")
        db.session.add(ram_opt)
        db.session.flush()

        odoo_product = {
            "id": 504,
            "name": "Xiaomi Redmi Note 15 5G DS 8/256GB Black",
            "barcode": "5000000000004",
            "default_code": "",
            "list_price": 299.0,
            "product_brand_id": [1, "Xiaomi"],
            "categ_id": [5, "All / Smartphones"],
            "product_template_attribute_value_ids": [],
        }

        status, _ = _process_single_product(
            odoo_product,
            attr_values_cache={},
            brand_lookup={},
            color_lookup={},
            memory_lookup={},
            ram_lookup={"8 go": ram_opt.id},
            norme_lookup={},
            type_lookup={},
            internal_by_odoo_id={},
            product_by_ean={},
            product_by_pn={},
        )
        assert status == "created"
        product = Product.query.filter_by(ean="5000000000004").first()
        assert product is not None
        assert product.RAM_id == ram_opt.id
        assert product.description == "Xiaomi Redmi Note 15 5G DS 8/256Go Black"
