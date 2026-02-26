"""Centralised logging configuration for the AJT Pro backend."""

import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path


class _JSONFormatter(logging.Formatter):
    """Emit one JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def configure_logging(app):
    """Set up rotating file handler (JSON) and console handler."""
    log_dir = Path(app.root_path) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    # --- console handler (human-readable) — always available ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
    )

    # --- file handler (JSON, 10 MB, 5 backups) — best effort ---
    file_handler = None
    try:
        file_handler = RotatingFileHandler(
            str(log_dir / "app.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(_JSONFormatter())
    except PermissionError:
        logging.warning(
            "Cannot write to %s — file logging disabled, using console only.",
            log_dir / "app.log",
        )

    # apply to the root logger so every library benefits
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(console_handler)
    if file_handler:
        root.addHandler(file_handler)

    # also configure Flask's own logger
    app.logger.setLevel(level)
    app.logger.addHandler(console_handler)
    if file_handler:
        app.logger.addHandler(file_handler)
