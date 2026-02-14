"""Tests for routes/products.py – CRUD products and bulk ops."""

import json
import math
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from models import Brand, Product, ProductCalculation, Supplier, SupplierAPI, ApiEndpoint, MappingVersion, db
from routes.products import _safe_float


@pytest.fixture()
def brand():
    b = Brand(brand="TestBrand")
    db.session.add(b)
    db.session.commit()
    return b


@pytest.fixture()
def sample_product(brand):
    p = Product(
        ean="1234567890123",
        model="TestModel",
        description="Test desc",
        brand_id=brand.id,
    )
    db.session.add(p)
    db.session.commit()
    return p


# ── GET /products ───────────────────────────────────────────────────


def test_list_products(client, admin_headers, sample_product):
    rv = client.get("/products", headers=admin_headers)
    assert rv.status_code == 200
    data = rv.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_list_products_forbidden(client, client_headers):
    rv = client.get("/products", headers=client_headers)
    assert rv.status_code == 403


# ── POST /products ──────────────────────────────────────────────────


def test_create_product(client, admin_headers, brand):
    rv = client.post(
        "/products",
        data=json.dumps({"ean": "9999999999999", "model": "New", "brand_id": brand.id}),
        headers=admin_headers,
    )
    assert rv.status_code == 201
    assert "id" in rv.get_json()


# ── PUT /products/<id> ──────────────────────────────────────────────


def test_update_product(client, admin_headers, sample_product):
    rv = client.put(
        "/products/{0}".format(sample_product.id),
        data=json.dumps({"model": "UpdatedModel"}),
        headers=admin_headers,
    )
    assert rv.status_code == 200
    assert rv.get_json()["status"] == "updated"


# ── DELETE /products/<id> ───────────────────────────────────────────


def test_delete_product(client, admin_headers, sample_product):
    rv = client.delete(
        "/products/{0}".format(sample_product.id),
        headers=admin_headers,
    )
    assert rv.status_code == 200
    assert rv.get_json()["status"] == "deleted"


# ── PUT /products/bulk_update ───────────────────────────────────────


def test_bulk_update(client, admin_headers, sample_product):
    rv = client.put(
        "/products/bulk_update",
        data=json.dumps([{"id": sample_product.id, "model": "Bulk"}]),
        headers=admin_headers,
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert sample_product.id in data["updated"]


def test_bulk_update_invalid_payload(client, admin_headers):
    rv = client.put(
        "/products/bulk_update",
        data=json.dumps("not a list"),
        headers=admin_headers,
    )
    assert rv.status_code == 400


# ── POST /products/bulk_delete ──────────────────────────────────────


def test_bulk_delete(client, admin_headers, sample_product):
    rv = client.post(
        "/products/bulk_delete",
        data=json.dumps({"ids": [sample_product.id]}),
        headers=admin_headers,
    )
    assert rv.status_code == 200
    assert sample_product.id in rv.get_json()["deleted"]


def test_bulk_delete_invalid_payload(client, admin_headers):
    rv = client.post(
        "/products/bulk_delete",
        data=json.dumps({"ids": "not a list"}),
        headers=admin_headers,
    )
    assert rv.status_code == 400


# ── product_price_summary with brandless products ─────────────────


def test_product_price_summary_includes_brandless(client, admin_headers):
    """Products without a brand should still appear in product_price_summary."""
    supplier = Supplier(name="NoBrandSupplier")
    db.session.add(supplier)
    db.session.commit()

    product = Product(model="NoBrandProduct", brand_id=None)
    db.session.add(product)
    db.session.commit()

    calc = ProductCalculation(
        product_id=product.id,
        supplier_id=supplier.id,
        price=100.0,
        tcp=10.0,
        marge4_5=5.0,
        prixht_tcp_marge4_5=115.0,
        prixht_marge4_5=105.0,
        prixht_max=120.0,
        marge=10.0,
        marge_percent=9.09,
        date=datetime.now(timezone.utc),
        stock=5,
    )
    db.session.add(calc)
    db.session.commit()

    rv = client.get("/product_price_summary", headers=admin_headers)
    assert rv.status_code == 200
    data = rv.get_json()
    ids = [item["id"] for item in data]
    assert product.id in ids


# ── _safe_float helper ────────────────────────────────────────────


def test_safe_float_normal():
    assert _safe_float(42.5) == 42.5


def test_safe_float_none():
    assert _safe_float(None) == 0.0


def test_safe_float_nan():
    assert _safe_float(float("nan")) == 0.0


def test_safe_float_inf():
    assert _safe_float(float("inf")) == 0.0
    assert _safe_float(float("-inf")) == 0.0


def test_safe_float_custom_default():
    assert _safe_float(None, default=-1.0) == -1.0


# ── POST /calculate_products error handling ───────────────────────


def test_calculate_products_returns_500_on_error(client, admin_headers):
    with patch(
        "routes.products.recalculate_product_calculations",
        side_effect=RuntimeError("DB connection lost"),
    ):
        rv = client.post("/calculate_products", headers=admin_headers)
        assert rv.status_code == 500
        data = rv.get_json()
        assert "error" in data


def test_safe_float_string_input():
    assert _safe_float("not_a_number") == 0.0


def test_product_price_summary_zero_price(client, admin_headers):
    """Products with zero prices should still appear without errors."""
    supplier = Supplier(name="ZeroSupplier")
    db.session.add(supplier)
    db.session.commit()

    product = Product(model="ZeroProduct", brand_id=None)
    db.session.add(product)
    db.session.commit()

    calc = ProductCalculation(
        product_id=product.id,
        supplier_id=supplier.id,
        price=0.0,
        tcp=0.0,
        marge4_5=0.0,
        prixht_tcp_marge4_5=0.0,
        prixht_marge4_5=0.0,
        prixht_max=0.0,
        marge=0.0,
        marge_percent=0.0,
        date=datetime.now(timezone.utc),
        stock=0,
    )
    db.session.add(calc)
    db.session.commit()

    rv = client.get("/product_price_summary", headers=admin_headers)
    assert rv.status_code == 200
    data = rv.get_json()
    ids = [item["id"] for item in data]
    assert product.id in ids


# ── POST /supplier_catalog/refresh ──────────────────────────────


def test_refresh_supplier_catalog_requires_admin(client, client_headers):
    rv = client.post("/supplier_catalog/refresh", headers=client_headers)
    assert rv.status_code == 403


@patch("routes.products.run_fetch_job")
def test_refresh_supplier_catalog_success(mock_fetch, client, admin_headers):
    """POST /supplier_catalog/refresh should trigger a refresh of all configured suppliers."""
    supplier = Supplier(name="RefreshSupplier")
    db.session.add(supplier)
    db.session.commit()

    api = SupplierAPI(supplier_id=supplier.id, base_url="https://example.com")
    db.session.add(api)
    db.session.commit()

    endpoint = ApiEndpoint(
        supplier_api_id=api.id,
        name="products",
        path="/products",
    )
    db.session.add(endpoint)
    db.session.commit()

    mapping = MappingVersion(
        supplier_api_id=api.id,
        version=1,
        is_active=True,
    )
    db.session.add(mapping)
    db.session.commit()

    mock_fetch.return_value = {"catalog_count": 42}

    rv = client.post("/supplier_catalog/refresh", headers=admin_headers)
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["status"] == "success"
    assert data["total_items"] == 42
    assert "RefreshSupplier" in data["refreshed_suppliers"]
    assert "duration_seconds" in data
    mock_fetch.assert_called_once()
