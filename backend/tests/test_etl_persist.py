"""Tests for _persist_supplier_catalog (FK safety with pending_matches)."""

from datetime import datetime, timezone

from models import (
    ApiEndpoint,
    ApiFetchJob,
    MappingVersion,
    PendingMatch,
    Supplier,
    SupplierAPI,
    SupplierCatalog,
    db,
)
from utils.etl import _persist_supplier_catalog


def _setup_supplier_with_job():
    """Create a supplier with API, endpoint, mapping, and fetch job."""
    supplier = Supplier(name="TestSupplier")
    db.session.add(supplier)
    db.session.flush()

    api = SupplierAPI(
        supplier_id=supplier.id,
        base_url="https://example.com",
        auth_type="none",
    )
    db.session.add(api)
    db.session.flush()

    endpoint = ApiEndpoint(
        supplier_api_id=api.id,
        name="products",
        path="/products",
        method="GET",
    )
    db.session.add(endpoint)
    db.session.flush()

    mapping = MappingVersion(
        supplier_api_id=api.id,
        version=1,
        is_active=True,
    )
    db.session.add(mapping)
    db.session.flush()

    job = ApiFetchJob(
        supplier_api_id=api.id,
        endpoint_id=endpoint.id,
        mapping_version_id=mapping.id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.session.add(job)
    db.session.flush()

    return supplier, job


def test_persist_clears_pending_match_fk_before_delete():
    """Catalog refresh must not fail when pending_matches reference old catalog rows."""
    supplier, job = _setup_supplier_with_job()

    # Create a catalog entry and a pending_match that references it
    catalog = SupplierCatalog(
        supplier_id=supplier.id,
        ean="1234567890123",
        description="Old product",
    )
    db.session.add(catalog)
    db.session.flush()

    pm = PendingMatch(
        supplier_id=supplier.id,
        temporary_import_id=catalog.id,
        source_label="Test Label",
        extracted_attributes={"brand": "Test"},
        candidates=[],
        status="pending",
    )
    db.session.add(pm)
    db.session.commit()

    assert pm.temporary_import_id == catalog.id

    # Run persist — should NOT raise ForeignKeyViolation
    parsed_records = [
        {
            "ean": "9999999999999",
            "description": "New product",
        }
    ]
    _persist_supplier_catalog(job, supplier.id, parsed_records)
    db.session.commit()

    # pending_match FK should be nullified
    db.session.refresh(pm)
    assert pm.temporary_import_id is None
    assert pm.status == "pending"

    # Old catalog gone, new one inserted
    remaining = SupplierCatalog.query.filter_by(supplier_id=supplier.id).all()
    assert len(remaining) == 1
    assert remaining[0].ean == "9999999999999"


def test_persist_without_pending_matches():
    """Catalog refresh works normally when no pending_matches exist."""
    supplier, job = _setup_supplier_with_job()

    # Create old catalog entries (no pending_matches referencing them)
    for ean in ["1111111111111", "2222222222222"]:
        db.session.add(SupplierCatalog(
            supplier_id=supplier.id,
            ean=ean,
            description=f"Old {ean}",
        ))
    db.session.commit()

    parsed_records = [{"ean": "3333333333333", "description": "New product"}]
    _persist_supplier_catalog(job, supplier.id, parsed_records)
    db.session.commit()

    remaining = SupplierCatalog.query.filter_by(supplier_id=supplier.id).all()
    assert len(remaining) == 1
    assert remaining[0].ean == "3333333333333"
