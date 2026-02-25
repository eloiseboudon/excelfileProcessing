"""Scheduler for the nightly pipeline.

Checks every minute whether the configured run time has been reached,
then fires run_nightly_pipeline() in a background thread.
Activated via ENABLE_NIGHTLY_SCHEDULER=true environment variable.
"""

from __future__ import annotations

import logging
import threading
from datetime import date, datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60  # check every minute


class NightlyScheduler:
    """Daemon scheduler that triggers the nightly pipeline at a configured time."""

    def __init__(self, app):
        self._app = app
        self._timer: Optional[threading.Timer] = None
        self._running = False
        self._last_run_date: Optional[date] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        logger.info(
            "Nightly scheduler started (check every %ds)", CHECK_INTERVAL_SECONDS
        )
        self._schedule_next()

    def stop(self) -> None:
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        logger.info("Nightly scheduler stopped")

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
            logger.exception("Error in nightly scheduler tick")
        finally:
            self._schedule_next()

    def _check_and_run(self) -> None:
        with self._app.app_context():
            from models import NightlyConfig

            config = NightlyConfig.query.first()
            if not config or not config.enabled:
                return

            now = datetime.now(timezone.utc)
            today = now.date()

            # Already ran today
            if self._last_run_date == today:
                return

            if now.hour != config.run_hour or now.minute != config.run_minute:
                return

            self._last_run_date = today
            logger.info(
                "Nightly pipeline triggered at %02d:%02d UTC",
                config.run_hour,
                config.run_minute,
            )
            thread = threading.Thread(target=self._run_pipeline, daemon=True)
            thread.start()

    def _run_pipeline(self) -> None:
        with self._app.app_context():
            from utils.nightly_pipeline import run_nightly_pipeline

            try:
                run_nightly_pipeline()
            except Exception:
                logger.exception("Nightly pipeline raised an uncaught exception")
