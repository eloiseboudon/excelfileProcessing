"""Tests for routes/products.py – CRUD products and bulk ops."""

import json
from datetime import datetime, timezone

import pytest
from models import Brand, Product, ProductCalculation, Supplier, db


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
