"""Tests for routes/matching.py — LLM matching API endpoints."""

import json
from unittest.mock import patch

import pytest

from models import (
    Brand,
    LabelCache,
    MemoryOption,
    PendingMatch,
    Product,
    Supplier,
    SupplierProductRef,
    SupplierCatalog,
    db,
)


@pytest.fixture()
def supplier():
    s = Supplier(name="Yukatel")
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
def memory():
    m = MemoryOption(memory="256 Go", tcp_value=256)
    db.session.add(m)
    db.session.commit()
    return m


@pytest.fixture()
def product(brand, memory):
    p = Product(model="Galaxy S25 Ultra", brand_id=brand.id, memory_id=memory.id)
    db.session.add(p)
    db.session.commit()
    return p


@pytest.fixture()
def pending_match(supplier):
    pm = PendingMatch(
        supplier_id=supplier.id,
        source_label="SM-S938B 256 BLK",
        extracted_attributes={"brand": "Samsung", "model_family": "Galaxy S25 Ultra"},
        candidates=[{"product_id": 1, "score": 75}],
        status="pending",
    )
    db.session.add(pm)
    db.session.commit()
    return pm


@pytest.fixture()
def cache_entry(supplier, product):
    c = LabelCache(
        supplier_id=supplier.id,
        normalized_label="samsung galaxy s25 ultra",
        product_id=product.id,
        match_score=95,
        match_source="auto",
    )
    db.session.add(c)
    db.session.commit()
    return c


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


class TestMatchingAuth:
    def test_run_requires_auth(self, client):
        rv = client.post("/matching/run")
        assert rv.status_code == 401

    def test_run_requires_admin(self, client, client_headers):
        rv = client.post("/matching/run", headers=client_headers)
        assert rv.status_code == 403

    def test_pending_requires_auth(self, client):
        rv = client.get("/matching/pending")
        assert rv.status_code == 401

    def test_stats_requires_auth(self, client):
        rv = client.get("/matching/stats")
        assert rv.status_code == 401


# ---------------------------------------------------------------------------
# POST /matching/run
# ---------------------------------------------------------------------------


class TestRunMatching:
    @patch("routes.matching.run_matching_job")
    def test_run_global(self, mock_run, client, admin_headers):
        mock_run.return_value = {
            "total_labels": 10,
            "from_cache": 5,
            "llm_calls": 1,
            "auto_matched": 3,
            "pending_review": 1,
            "auto_created": 1,
            "errors": 0,
            "cost_estimate": 0.002,
            "duration_seconds": 2.5,
        }
        rv = client.post("/matching/run", headers=admin_headers)
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["total_labels"] == 10
        mock_run.assert_called_once_with(supplier_id=None, limit=None)

    @patch("routes.matching.run_matching_job")
    def test_run_with_supplier(self, mock_run, client, admin_headers, supplier):
        mock_run.return_value = {"total_labels": 0, "from_cache": 0, "llm_calls": 0,
                                  "auto_matched": 0, "pending_review": 0, "auto_created": 0,
                                  "errors": 0, "cost_estimate": 0, "duration_seconds": 0}
        rv = client.post(
            "/matching/run",
            headers=admin_headers,
            data=json.dumps({"supplier_id": supplier.id}),
        )
        assert rv.status_code == 200
        mock_run.assert_called_once_with(supplier_id=supplier.id, limit=None)

    @patch("routes.matching.run_matching_job")
    def test_run_with_limit(self, mock_run, client, admin_headers):
        mock_run.return_value = {"total_labels": 5, "from_cache": 0, "llm_calls": 1,
                                  "auto_matched": 3, "pending_review": 1, "auto_created": 1,
                                  "errors": 0, "cost_estimate": 0, "duration_seconds": 1,
                                  "remaining": 10}
        rv = client.post(
            "/matching/run",
            headers=admin_headers,
            data=json.dumps({"limit": 50}),
        )
        assert rv.status_code == 200
        mock_run.assert_called_once_with(supplier_id=None, limit=50)
        data = rv.get_json()
        assert data["remaining"] == 10

    def test_run_invalid_supplier(self, client, admin_headers):
        rv = client.post(
            "/matching/run",
            headers=admin_headers,
            data=json.dumps({"supplier_id": 99999}),
        )
        assert rv.status_code == 404


# ---------------------------------------------------------------------------
# GET /matching/pending
# ---------------------------------------------------------------------------


class TestListPending:
    def test_list_empty(self, client, admin_headers):
        rv = client.get("/matching/pending", headers=admin_headers)
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_with_results(self, client, admin_headers, pending_match):
        rv = client.get("/matching/pending", headers=admin_headers)
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["total"] == 1
        assert data["items"][0]["source_label"] == "SM-S938B 256 BLK"

    def test_filter_by_supplier(self, client, admin_headers, pending_match, supplier):
        rv = client.get(
            f"/matching/pending?supplier_id={supplier.id}",
            headers=admin_headers,
        )
        data = rv.get_json()
        assert data["total"] == 1

        rv = client.get(
            "/matching/pending?supplier_id=99999",
            headers=admin_headers,
        )
        data = rv.get_json()
        assert data["total"] == 0


# ---------------------------------------------------------------------------
# POST /matching/validate
# ---------------------------------------------------------------------------


class TestValidateMatch:
    def test_validate_success(self, client, admin_headers, pending_match, product):
        rv = client.post(
            "/matching/validate",
            headers=admin_headers,
            data=json.dumps({
                "pending_match_id": pending_match.id,
                "product_id": product.id,
            }),
        )
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["status"] == "validated"

        pm = db.session.get(PendingMatch, pending_match.id)
        assert pm.status == "validated"
        assert pm.resolved_product_id == product.id

    def test_validate_missing_params(self, client, admin_headers):
        rv = client.post(
            "/matching/validate",
            headers=admin_headers,
            data=json.dumps({}),
        )
        assert rv.status_code == 400

    def test_validate_not_found(self, client, admin_headers, product):
        rv = client.post(
            "/matching/validate",
            headers=admin_headers,
            data=json.dumps({"pending_match_id": 99999, "product_id": product.id}),
        )
        assert rv.status_code == 404

    def test_validate_already_processed(self, client, admin_headers, pending_match, product):
        pending_match.status = "validated"
        db.session.commit()

        rv = client.post(
            "/matching/validate",
            headers=admin_headers,
            data=json.dumps({
                "pending_match_id": pending_match.id,
                "product_id": product.id,
            }),
        )
        assert rv.status_code == 400

    def test_validate_copies_identifiers(self, client, admin_headers, product, supplier):
        """Validate should copy ean/part_number from SupplierCatalog to SupplierProductRef."""
        temp = SupplierCatalog(
            description="SM-S938B 256 BLK",
            ean="1112223334445",
            part_number="SM-S938B",
            selling_price=700.0,
            supplier_id=supplier.id,
        )
        db.session.add(temp)
        db.session.commit()

        pm = PendingMatch(
            supplier_id=supplier.id,
            temporary_import_id=temp.id,
            source_label="SM-S938B 256 BLK",
            extracted_attributes={"brand": "Samsung"},
            candidates=[{"product_id": product.id, "score": 80}],
            status="pending",
        )
        db.session.add(pm)
        db.session.commit()

        rv = client.post(
            "/matching/validate",
            headers=admin_headers,
            data=json.dumps({
                "pending_match_id": pm.id,
                "product_id": product.id,
            }),
        )
        assert rv.status_code == 200

        ref = SupplierProductRef.query.filter_by(
            supplier_id=supplier.id, product_id=product.id
        ).first()
        assert ref is not None
        assert ref.ean == "1112223334445"
        assert ref.part_number == "SM-S938B"

    def test_validate_creates_cache(self, client, admin_headers, pending_match, product):
        rv = client.post(
            "/matching/validate",
            headers=admin_headers,
            data=json.dumps({
                "pending_match_id": pending_match.id,
                "product_id": product.id,
            }),
        )
        assert rv.status_code == 200

        cache = LabelCache.query.filter_by(
            supplier_id=pending_match.supplier_id
        ).first()
        assert cache is not None
        assert cache.match_source == "manual"
        assert cache.product_id == product.id


# ---------------------------------------------------------------------------
# POST /matching/reject
# ---------------------------------------------------------------------------


class TestRejectMatch:
    def test_reject_simple(self, client, admin_headers, pending_match):
        rv = client.post(
            "/matching/reject",
            headers=admin_headers,
            data=json.dumps({"pending_match_id": pending_match.id}),
        )
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["status"] == "rejected"

    def test_reject_with_create(self, client, admin_headers, pending_match, brand):
        rv = client.post(
            "/matching/reject",
            headers=admin_headers,
            data=json.dumps({
                "pending_match_id": pending_match.id,
                "create_product": True,
            }),
        )
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["status"] == "created"

        pm = db.session.get(PendingMatch, pending_match.id)
        assert pm.resolved_product_id is not None

    def test_reject_create_copies_identifiers(self, client, admin_headers, supplier, brand):
        """Reject+create should copy ean/part_number from SupplierCatalog to SupplierProductRef."""
        temp = SupplierCatalog(
            description="SM-S938B 256 BLK",
            ean="5556667778880",
            part_number="SM-S938B",
            selling_price=700.0,
            supplier_id=supplier.id,
        )
        db.session.add(temp)
        db.session.commit()

        pm = PendingMatch(
            supplier_id=supplier.id,
            temporary_import_id=temp.id,
            source_label="SM-S938B 256 BLK",
            extracted_attributes={"brand": "Samsung", "model_family": "Galaxy S25 Ultra"},
            candidates=[],
            status="pending",
        )
        db.session.add(pm)
        db.session.commit()

        rv = client.post(
            "/matching/reject",
            headers=admin_headers,
            data=json.dumps({
                "pending_match_id": pm.id,
                "create_product": True,
            }),
        )
        assert rv.status_code == 200

        pm_updated = db.session.get(PendingMatch, pm.id)
        ref = SupplierProductRef.query.filter_by(
            supplier_id=supplier.id, product_id=pm_updated.resolved_product_id
        ).first()
        assert ref is not None
        assert ref.ean == "5556667778880"
        assert ref.part_number == "SM-S938B"

    def test_reject_not_found(self, client, admin_headers):
        rv = client.post(
            "/matching/reject",
            headers=admin_headers,
            data=json.dumps({"pending_match_id": 99999}),
        )
        assert rv.status_code == 404


# ---------------------------------------------------------------------------
# GET /matching/stats
# ---------------------------------------------------------------------------


class TestMatchingStats:
    def test_stats_empty(self, client, admin_headers):
        rv = client.get("/matching/stats", headers=admin_headers)
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["total_cached"] == 0
        assert data["total_pending"] == 0

    def test_stats_with_data(self, client, admin_headers, cache_entry, pending_match):
        rv = client.get("/matching/stats", headers=admin_headers)
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["total_cached"] == 1
        assert data["total_pending"] == 1
        assert data["cache_hit_rate"] == 50.0


# ---------------------------------------------------------------------------
# GET /matching/cache & DELETE /matching/cache/<id>
# ---------------------------------------------------------------------------


class TestCacheEndpoints:
    def test_list_cache(self, client, admin_headers, cache_entry):
        rv = client.get("/matching/cache", headers=admin_headers)
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["total"] == 1
        assert data["items"][0]["normalized_label"] == "samsung galaxy s25 ultra"

    def test_delete_cache(self, client, admin_headers, cache_entry):
        rv = client.delete(
            f"/matching/cache/{cache_entry.id}",
            headers=admin_headers,
        )
        assert rv.status_code == 204
        assert LabelCache.query.count() == 0

    def test_delete_cache_not_found(self, client, admin_headers):
        rv = client.delete("/matching/cache/99999", headers=admin_headers)
        assert rv.status_code == 404
