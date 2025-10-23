"""Batch script to trigger supplier API synchronizations on demand."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Sequence

from flask import Flask
from sqlalchemy.orm import joinedload

from app import create_app
from models import ApiEndpoint, ApiFetchJob, MappingVersion, Supplier, SupplierAPI, db
from utils.etl import run_fetch_job


@dataclass(frozen=True)
class SyncTarget:
    """Describe a synchronization to execute."""

    supplier: Supplier
    endpoint: ApiEndpoint
    mapping: MappingVersion


def _select_active_mapping(endpoint: ApiEndpoint) -> MappingVersion | None:
    """Return the most recent active mapping configured for an endpoint."""

    return (
        MappingVersion.query.filter_by(supplier_api_id=endpoint.supplier_api_id, is_active=True)
        .order_by(MappingVersion.version.desc(), MappingVersion.id.desc())
        .first()
    )


def _collect_targets() -> List[SyncTarget]:
    """Retrieve all supplier/endpoints pairs eligible for synchronization."""

    endpoints: Sequence[ApiEndpoint] = (
        ApiEndpoint.query.options(
            joinedload(ApiEndpoint.supplier_api)
            .joinedload(SupplierAPI.supplier),
            joinedload(ApiEndpoint.supplier_api)
            .joinedload(SupplierAPI.mappings)
            .joinedload(MappingVersion.fields),
        )
        .order_by(ApiEndpoint.id.asc())
        .all()
    )

    targets: List[SyncTarget] = []
    for endpoint in endpoints:
        supplier = endpoint.supplier_api.supplier if endpoint.supplier_api else None
        if not supplier:
            logging.warning(
                "Skipping endpoint %s (%s): supplier not found",
                endpoint.id,
                endpoint.name,
            )
            continue

        mapping = _select_active_mapping(endpoint)
        if not mapping:
            logging.warning(
                "Skipping endpoint %s (%s) for supplier %s: no active mapping",
                endpoint.id,
                endpoint.name,
                supplier.name,
            )
            continue

        targets.append(SyncTarget(supplier=supplier, endpoint=endpoint, mapping=mapping))

    return targets


def _execute_target(target: SyncTarget) -> None:
    """Create a fetch job and run the synchronization for the given target."""

    job = ApiFetchJob(
        supplier_api_id=target.endpoint.supplier_api_id,
        endpoint_id=target.endpoint.id,
        mapping_version_id=target.mapping.id,
        status="running",
    )
    db.session.add(job)
    db.session.commit()

    logging.info(
        "Starting synchronization job %s for supplier '%s' (endpoint: %s)",
        job.id,
        target.supplier.name,
        target.endpoint.name,
    )

    try:
        result = run_fetch_job(
            job_id=job.id,
            supplier_id=target.supplier.id,
            endpoint_id=target.endpoint.id,
            mapping_id=target.mapping.id,
        )
    except RuntimeError as exc:  # pragma: no cover - CLI feedback only
        logging.error(
            "Synchronization failed for supplier '%s' (endpoint: %s): %s",
            target.supplier.name,
            target.endpoint.name,
            exc,
        )
        return

    logging.info(
        "Synchronization completed for supplier '%s' (endpoint: %s): %s items parsed",
        target.supplier.name,
        target.endpoint.name,
        result.get("parsed_count"),
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    app: Flask = create_app()
    with app.app_context():
        targets = _collect_targets()
        if not targets:
            logging.info("No suppliers with configured API endpoints were found.")
            return

        for target in targets:
            _execute_target(target)


if __name__ == "__main__":
    main()
