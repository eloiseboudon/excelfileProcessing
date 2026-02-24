"""Tests for _persist_supplier_catalog and _sync_prices_from_catalog."""

from datetime import datetime, timezone

from models import (
    ApiEndpoint,
    ApiFetchJob,
    Brand,
    LabelCache,
    MemoryOption,
    MappingVersion,
    PendingMatch,
    Product,
    ProductCalculation,
    Supplier,
    SupplierAPI,
    SupplierCatalog,
    db,
)
from utils.etl import _persist_supplier_catalog, _sync_prices_from_catalog


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


# ---------------------------------------------------------------------------
# Tests: seen_eans removed — two entries with different EANs for same label
# ---------------------------------------------------------------------------


def test_two_eans_same_product_both_kept():
    """Two entries with different EANs and same label must both be persisted."""
    supplier, job = _setup_supplier_with_job()

    parsed_records = [
        {"ean": "1111111111111", "description": "Samsung Galaxy S25 128Go Noir", "selling_price": 700},
        {"ean": "2222222222222", "description": "Samsung Galaxy S25 128Go Noir", "selling_price": 680},
    ]
    _persist_supplier_catalog(job, supplier.id, parsed_records)
    db.session.commit()

    rows = SupplierCatalog.query.filter_by(supplier_id=supplier.id).all()
    # Both entries must be stored — seen_eans no longer discards the second one
    assert len(rows) == 2
    eans = {r.ean for r in rows}
    assert "1111111111111" in eans
    assert "2222222222222" in eans


# ---------------------------------------------------------------------------
# Tests: _sync_prices_from_catalog — label-based price sync
# ---------------------------------------------------------------------------


def _make_product(supplier):
    """Create a minimal Product with a MemoryOption for TCP calculation."""
    brand = Brand(brand=f"Brand-{supplier.id}")
    db.session.add(brand)
    db.session.flush()

    memory = MemoryOption(memory="128 Go", tcp_value=128)
    db.session.add(memory)
    db.session.flush()

    product = Product(model="Test Phone 128Go", brand_id=brand.id, memory_id=memory.id)
    db.session.add(product)
    db.session.flush()
    return product


def test_price_sync_uses_label_not_ean():
    """_sync_prices_from_catalog updates ProductCalculation via LabelCache even when EAN is absent."""
    supplier, _ = _setup_supplier_with_job()
    product = _make_product(supplier)

    # Catalog entry without EAN
    db.session.add(SupplierCatalog(
        supplier_id=supplier.id,
        description="Test Phone 128Go",
        selling_price=500.0,
        quantity=10,
    ))

    # LabelCache entry linking the label to the product
    db.session.add(LabelCache(
        supplier_id=supplier.id,
        normalized_label="test phone 128go",
        product_id=product.id,
        match_score=95,
        match_source="auto",
    ))
    db.session.commit()

    result = _sync_prices_from_catalog(supplier.id)
    db.session.commit()

    assert result["synced"] == 1
    calc = ProductCalculation.query.filter_by(
        product_id=product.id, supplier_id=supplier.id
    ).first()
    assert calc is not None
    assert calc.price == 500.0
    assert calc.stock == 10


def test_price_sync_best_price_when_multiple_entries():
    """When two catalog entries map to the same product, best price (min) and total stock are used."""
    supplier, _ = _setup_supplier_with_job()
    product = _make_product(supplier)

    normalized = "test phone 128go"
    db.session.add(SupplierCatalog(
        supplier_id=supplier.id,
        description="Test Phone 128Go",
        ean="1111111111111",
        selling_price=1000.0,
        quantity=5,
    ))
    db.session.add(SupplierCatalog(
        supplier_id=supplier.id,
        description="Test Phone 128Go",
        ean="2222222222222",
        selling_price=950.0,
        quantity=3,
    ))
    db.session.add(LabelCache(
        supplier_id=supplier.id,
        normalized_label=normalized,
        product_id=product.id,
        match_score=95,
        match_source="auto",
    ))
    db.session.commit()

    result = _sync_prices_from_catalog(supplier.id)
    db.session.commit()

    assert result["synced"] == 1
    calc = ProductCalculation.query.filter_by(
        product_id=product.id, supplier_id=supplier.id
    ).first()
    assert calc is not None
    assert calc.price == 950.0   # best (min) price
    assert calc.stock == 8       # total stock


def test_price_sync_unmatched_entries_reported():
    """Catalog entries with no LabelCache match are reported as api_missing_products."""
    supplier, _ = _setup_supplier_with_job()

    db.session.add(SupplierCatalog(
        supplier_id=supplier.id,
        description="Unknown Product XYZ",
        selling_price=200.0,
        quantity=1,
    ))
    db.session.commit()

    result = _sync_prices_from_catalog(supplier.id)

    assert result["synced"] == 0
    assert len(result["api_missing_products"]) == 1
    assert result["api_missing_products"][0]["description"] == "Unknown Product XYZ"
