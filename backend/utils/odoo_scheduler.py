"""Periodic scheduler for automatic Odoo synchronization.

Uses threading.Timer to check every 5 minutes if an auto-sync is due.
Activated via ENABLE_ODOO_SCHEDULER=true environment variable.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 300  # 5 minutes


class OdooScheduler:
    """Daemon scheduler that triggers Odoo sync when due."""

    def __init__(self, app):
        self._app = app
        self._timer: threading.Timer | None = None
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        logger.info("Odoo scheduler started (check every %ds)", CHECK_INTERVAL_SECONDS)
        self._schedule_next()

    def stop(self) -> None:
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        logger.info("Odoo scheduler stopped")

    def _schedule_next(self) -> None:
        if not self._running:
            return
        self._timer = threading.Timer(CHECK_INTERVAL_SECONDS, self._tick)
        self._timer.daemon = True
        self._timer.start()

    def _tick(self) -> None:
        if not self._running:
            return
        try:
            self._check_and_run()
        except Exception:
            logger.exception("Error in Odoo scheduler tick")
        finally:
            self._schedule_next()

    def _check_and_run(self) -> None:
        with self._app.app_context():
            from models import OdooConfig, OdooSyncJob, db
            from utils.odoo_sync import run_odoo_sync

            config = OdooConfig.query.first()
            if not config or not config.auto_sync_enabled:
                return

            interval = timedelta(minutes=config.auto_sync_interval_minutes or 1440)
            now = datetime.utcnow()

            if config.last_auto_sync_at and (now - config.last_auto_sync_at) < interval:
                return

            # Check no job is currently running
            running = OdooSyncJob.query.filter_by(status="running").first()
            if running:
                return

            logger.info("Auto-sync triggered")
            job = OdooSyncJob(trigger="auto")
            db.session.add(job)
            config.last_auto_sync_at = now
            db.session.commit()

            run_odoo_sync(job.id)
