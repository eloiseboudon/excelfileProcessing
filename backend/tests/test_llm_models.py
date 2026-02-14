"""Tests for LLM matching models (ModelReference, LabelCache, PendingMatch)."""

import pytest

from models import (
    Brand,
    LabelCache,
    ModelReference,
    PendingMatch,
    Product,
    Supplier,
    TemporaryImport,
    db,
)


@pytest.fixture()
def supplier():
    s = Supplier(name="TestSupplier")
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture()
def brand():
    b = Brand(brand="Samsung")
    db.session.add(b)
    db.session.commit()
    return b


@pytest.fixture()
def product(brand):
    p = Product(model="Galaxy S25 Ultra", brand_id=brand.id)
    db.session.add(p)
    db.session.commit()
    return p


class TestModelReference:
    def test_create(self, brand):
        ref = ModelReference(
            manufacturer_code="SM-S938B",
            commercial_name="Galaxy S25 Ultra",
            brand_id=brand.id,
        )
        db.session.add(ref)
        db.session.commit()

        fetched = ModelReference.query.first()
        assert fetched.manufacturer_code == "SM-S938B"
        assert fetched.commercial_name == "Galaxy S25 Ultra"
        assert fetched.brand_id == brand.id
        assert fetched.created_at is not None

    def test_unique_manufacturer_code(self, brand):
        ref1 = ModelReference(
            manufacturer_code="SM-S938B",
            commercial_name="Galaxy S25 Ultra",
            brand_id=brand.id,
        )
        db.session.add(ref1)
        db.session.commit()

        ref2 = ModelReference(
            manufacturer_code="SM-S938B",
            commercial_name="Duplicate",
            brand_id=brand.id,
        )
        db.session.add(ref2)
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()

    def test_brand_relationship(self, brand):
        ref = ModelReference(
            manufacturer_code="S938B",
            commercial_name="Galaxy S25 Ultra",
            brand_id=brand.id,
        )
        db.session.add(ref)
        db.session.commit()

        assert ref.brand.brand == "Samsung"
        assert ref in brand.model_references


class TestLabelCache:
    def test_create(self, supplier, product):
        cache = LabelCache(
            supplier_id=supplier.id,
            normalized_label="samsung galaxy s25 ultra 256go noir",
            product_id=product.id,
            match_score=95,
            match_source="auto",
            extracted_attributes={"brand": "Samsung", "model_family": "Galaxy S25 Ultra"},
        )
        db.session.add(cache)
        db.session.commit()

        fetched = LabelCache.query.first()
        assert fetched.normalized_label == "samsung galaxy s25 ultra 256go noir"
        assert fetched.match_score == 95
        assert fetched.match_source == "auto"
        assert fetched.extracted_attributes["brand"] == "Samsung"
        assert fetched.created_at is not None
        assert fetched.last_used_at is not None

    def test_unique_constraint(self, supplier):
        c1 = LabelCache(
            supplier_id=supplier.id,
            normalized_label="test label",
            match_source="auto",
        )
        db.session.add(c1)
        db.session.commit()

        c2 = LabelCache(
            supplier_id=supplier.id,
            normalized_label="test label",
            match_source="llm",
        )
        db.session.add(c2)
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()

    def test_different_suppliers_same_label(self, supplier):
        s2 = Supplier(name="OtherSupplier")
        db.session.add(s2)
        db.session.commit()

        c1 = LabelCache(
            supplier_id=supplier.id,
            normalized_label="same label",
            match_source="auto",
        )
        c2 = LabelCache(
            supplier_id=s2.id,
            normalized_label="same label",
            match_source="auto",
        )
        db.session.add_all([c1, c2])
        db.session.commit()

        assert LabelCache.query.count() == 2

    def test_relationships(self, supplier, product):
        cache = LabelCache(
            supplier_id=supplier.id,
            normalized_label="test",
            product_id=product.id,
            match_source="llm",
        )
        db.session.add(cache)
        db.session.commit()

        assert cache.supplier.name == "TestSupplier"
        assert cache.product.model == "Galaxy S25 Ultra"


class TestPendingMatch:
    def test_create(self, supplier):
        pm = PendingMatch(
            supplier_id=supplier.id,
            source_label="SM-S938B BLK 256",
            extracted_attributes={"brand": "Samsung", "model_family": "Galaxy S25 Ultra"},
            candidates=[{"product_id": 1, "score": 75}],
        )
        db.session.add(pm)
        db.session.commit()

        fetched = PendingMatch.query.first()
        assert fetched.source_label == "SM-S938B BLK 256"
        assert fetched.status == "pending"
        assert fetched.resolved_product_id is None
        assert fetched.resolved_at is None
        assert len(fetched.candidates) == 1

    def test_status_transitions(self, supplier, product):
        pm = PendingMatch(
            supplier_id=supplier.id,
            source_label="test",
            extracted_attributes={},
            candidates=[],
        )
        db.session.add(pm)
        db.session.commit()

        assert pm.status == "pending"

        from datetime import datetime, timezone

        pm.status = "validated"
        pm.resolved_product_id = product.id
        pm.resolved_at = datetime.now(timezone.utc)
        db.session.commit()

        fetched = PendingMatch.query.first()
        assert fetched.status == "validated"
        assert fetched.resolved_product_id == product.id
        assert fetched.resolved_at is not None

    def test_with_temporary_import(self, supplier):
        ti = TemporaryImport(
            description="Test Import",
            quantity=1,
            selling_price=100.0,
            supplier_id=supplier.id,
        )
        db.session.add(ti)
        db.session.commit()

        pm = PendingMatch(
            supplier_id=supplier.id,
            temporary_import_id=ti.id,
            source_label="Test Import",
            extracted_attributes={},
            candidates=[],
        )
        db.session.add(pm)
        db.session.commit()

        assert pm.temporary_import_id == ti.id


class TestProductRegion:
    def test_product_region(self):
        p = Product(model="iPhone 16 US", region="US")
        db.session.add(p)
        db.session.commit()

        fetched = Product.query.first()
        assert fetched.region == "US"

    def test_product_region_null(self):
        p = Product(model="iPhone 16")
        db.session.add(p)
        db.session.commit()

        fetched = Product.query.first()
        assert fetched.region is None

    def test_temporary_import_region(self, supplier):
        ti = TemporaryImport(
            description="Test",
            quantity=1,
            selling_price=100.0,
            supplier_id=supplier.id,
            region="IN",
        )
        db.session.add(ti)
        db.session.commit()

        fetched = TemporaryImport.query.first()
        assert fetched.region == "IN"
