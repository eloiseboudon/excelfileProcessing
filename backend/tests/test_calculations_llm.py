"""Tests for LabelCache fallback in recalculate_product_calculations()."""

import pytest

from models import (
    Brand,
    LabelCache,
    MemoryOption,
    Product,
    ProductCalculation,
    Supplier,
    SupplierCatalog,
    db,
)
from utils.calculations import recalculate_product_calculations


@pytest.fixture()
def supplier():
    s = Supplier(name="TestSupplier")
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture()
def brand():
    b = Brand(brand="Apple")
    db.session.add(b)
    db.session.commit()
    return b


@pytest.fixture()
def memory():
    m = MemoryOption(memory="128 Go", tcp_value=10)
    db.session.add(m)
    db.session.commit()
    return m


@pytest.fixture()
def product(brand, memory):
    p = Product(
        model="iPhone 15",
        brand_id=brand.id,
        memory_id=memory.id,
        ean="9999999999999",
    )
    db.session.add(p)
    db.session.commit()
    return p


def test_recalculate_uses_label_cache(supplier, product):
    """A SupplierCatalog with no EAN/model match should be matched via LabelCache."""
    temp = SupplierCatalog(
        description="Apple iPhone 15 128Go Noir",
        selling_price=500.0,
        quantity=3,
        supplier_id=supplier.id,
    )
    db.session.add(temp)

    cache = LabelCache(
        supplier_id=supplier.id,
        normalized_label="apple iphone 15 128go noir",
        product_id=product.id,
        match_score=92,
        match_source="auto",
    )
    db.session.add(cache)
    db.session.commit()

    recalculate_product_calculations()

    calc = ProductCalculation.query.filter_by(product_id=product.id).first()
    assert calc is not None
    assert calc.price == 500.0
    assert calc.supplier_id == supplier.id


def test_recalculate_ean_priority_over_cache(supplier, product, brand, memory):
    """EAN matching takes priority over LabelCache."""
    other_product = Product(
        model="iPhone 15 Pro",
        brand_id=brand.id,
        memory_id=memory.id,
    )
    db.session.add(other_product)
    db.session.commit()

    temp = SupplierCatalog(
        description="Apple iPhone 15 128Go Noir",
        ean="9999999999999",
        selling_price=600.0,
        quantity=1,
        supplier_id=supplier.id,
    )
    db.session.add(temp)

    # Cache points to other_product, but EAN matches product
    cache = LabelCache(
        supplier_id=supplier.id,
        normalized_label="apple iphone 15 128go noir",
        product_id=other_product.id,
        match_score=90,
        match_source="auto",
    )
    db.session.add(cache)
    db.session.commit()

    recalculate_product_calculations()

    calc = ProductCalculation.query.filter_by(product_id=product.id).first()
    assert calc is not None, "EAN match should produce a calculation for the EAN product"
    assert calc.price == 600.0

    other_calc = ProductCalculation.query.filter_by(product_id=other_product.id).first()
    assert other_calc is None, "Cache product should NOT get a calculation (EAN won)"


def test_recalculate_handles_product_without_memory(supplier, brand):
    """Product without memory relation should not crash."""
    p = Product(
        model="Test Phone No Memory",
        brand_id=brand.id,
        memory_id=None,
        ean="1111111111111",
    )
    db.session.add(p)
    db.session.commit()

    temp = SupplierCatalog(
        description="Test Phone",
        ean="1111111111111",
        selling_price=300.0,
        quantity=1,
        supplier_id=supplier.id,
    )
    db.session.add(temp)
    db.session.commit()

    recalculate_product_calculations()

    calc = ProductCalculation.query.filter_by(product_id=p.id).first()
    assert calc is not None
    assert calc.price == 300.0


def test_recalculate_continues_on_error(supplier, brand, memory):
    """If one product errors during calc, others should still be processed."""
    p1 = Product(
        model="Good Product",
        brand_id=brand.id,
        memory_id=memory.id,
        ean="2222222222222",
    )
    p2 = Product(
        model="Another Good Product",
        brand_id=brand.id,
        memory_id=memory.id,
        ean="3333333333333",
    )
    db.session.add_all([p1, p2])
    db.session.commit()

    temp1 = SupplierCatalog(
        description="Good Product",
        ean="2222222222222",
        selling_price=200.0,
        quantity=1,
        supplier_id=supplier.id,
    )
    temp2 = SupplierCatalog(
        description="Another Good Product",
        ean="3333333333333",
        selling_price=400.0,
        quantity=2,
        supplier_id=supplier.id,
    )
    db.session.add_all([temp1, temp2])
    db.session.commit()

    recalculate_product_calculations()

    calcs = ProductCalculation.query.all()
    assert len(calcs) == 2


def test_recalculate_ignores_cache_without_product(supplier):
    """LabelCache entries without product_id should be ignored."""
    temp = SupplierCatalog(
        description="Unknown gadget XYZ",
        selling_price=100.0,
        quantity=1,
        supplier_id=supplier.id,
    )
    db.session.add(temp)

    cache = LabelCache(
        supplier_id=supplier.id,
        normalized_label="unknown gadget xyz",
        product_id=None,
        match_score=0,
        match_source="auto",
    )
    db.session.add(cache)
    db.session.commit()

    recalculate_product_calculations()

    assert ProductCalculation.query.count() == 0
