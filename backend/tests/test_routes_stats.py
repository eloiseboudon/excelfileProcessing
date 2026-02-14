"""Tests for routes/stats.py – supplier catalog statistics."""

from datetime import datetime, timezone

import pytest
from models import ProductCalculation, Supplier, SupplierCatalog, Product, Brand, db


@pytest.fixture()
def supplier():
    s = Supplier(name="SupplierA")
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture()
def supplier_b():
    s = Supplier(name="SupplierB")
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture()
def catalog_items(supplier, supplier_b):
    items = [
        SupplierCatalog(ean="111", selling_price=100.0, supplier_id=supplier.id, quantity=1),
        SupplierCatalog(ean="222", selling_price=200.0, supplier_id=supplier.id, quantity=2),
        SupplierCatalog(ean="333", selling_price=150.0, supplier_id=supplier_b.id, quantity=1),
    ]
    db.session.add_all(items)
    db.session.commit()
    return items


@pytest.fixture()
def product_calcs(supplier, supplier_b):
    brand = Brand(brand="TestBrand")
    db.session.add(brand)
    db.session.flush()
    p = Product(ean="111", model="Phone", brand_id=brand.id)
    db.session.add(p)
    db.session.flush()
    calcs = [
        ProductCalculation(
            product_id=p.id, supplier_id=supplier.id,
            price=100.0, tcp=10.0, marge4_5=4.5,
            prixht_tcp_marge4_5=110.0, prixht_marge4_5=105.0, prixht_max=120.0,
            date=datetime(2025, 1, 6, tzinfo=timezone.utc),  # week 2
        ),
        ProductCalculation(
            product_id=p.id, supplier_id=supplier.id,
            price=110.0, tcp=10.0, marge4_5=4.5,
            prixht_tcp_marge4_5=120.0, prixht_marge4_5=115.0, prixht_max=130.0,
            date=datetime(2025, 1, 13, tzinfo=timezone.utc),  # week 3
        ),
        ProductCalculation(
            product_id=p.id, supplier_id=supplier_b.id,
            price=95.0, tcp=10.0, marge4_5=4.5,
            prixht_tcp_marge4_5=105.0, prixht_marge4_5=100.0, prixht_max=115.0,
            date=datetime(2025, 1, 6, tzinfo=timezone.utc),  # week 2
        ),
    ]
    db.session.add_all(calcs)
    db.session.commit()
    return calcs


# ── supplier_avg_price ──────────────────────────────────────────


def test_supplier_avg_price(client, admin_headers, catalog_items):
    rv = client.get("/supplier_avg_price", headers=admin_headers)
    assert rv.status_code == 200
    data = rv.get_json()
    assert len(data) == 2
    by_name = {d["supplier"]: d["avg_price"] for d in data}
    assert by_name["SupplierA"] == 150.0
    assert by_name["SupplierB"] == 150.0


def test_supplier_avg_price_forbidden(client, client_headers):
    rv = client.get("/supplier_avg_price", headers=client_headers)
    assert rv.status_code == 403


# ── supplier_product_count ──────────────────────────────────────


def test_supplier_product_count(client, admin_headers, catalog_items):
    rv = client.get("/supplier_product_count", headers=admin_headers)
    assert rv.status_code == 200
    data = rv.get_json()
    by_name = {d["supplier"]: d["count"] for d in data}
    assert by_name["SupplierA"] == 2
    assert by_name["SupplierB"] == 1


# ── supplier_price_distribution ─────────────────────────────────


def test_supplier_price_distribution(client, admin_headers, catalog_items):
    rv = client.get("/supplier_price_distribution", headers=admin_headers)
    assert rv.status_code == 200
    data = rv.get_json()
    by_name = {d["supplier"]: d["prices"] for d in data}
    assert sorted(by_name["SupplierA"]) == [100.0, 200.0]
    assert by_name["SupplierB"] == [150.0]


# ── supplier_price_evolution ────────────────────────────────────


def test_supplier_price_evolution(client, admin_headers, product_calcs):
    rv = client.get("/supplier_price_evolution", headers=admin_headers)
    assert rv.status_code == 200
    data = rv.get_json()
    assert len(data) >= 2
    suppliers_in_data = {d["supplier"] for d in data}
    assert "SupplierA" in suppliers_in_data
    assert "SupplierB" in suppliers_in_data


def test_supplier_price_evolution_with_model(client, admin_headers, product_calcs):
    rv = client.get(
        "/supplier_price_evolution?model=Phone", headers=admin_headers
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert len(data) >= 1
    suppliers_in_data = {d["supplier"] for d in data}
    assert "SupplierA" in suppliers_in_data


def test_supplier_price_evolution_empty(client, admin_headers):
    rv = client.get("/supplier_price_evolution", headers=admin_headers)
    assert rv.status_code == 200
    assert rv.get_json() == []
