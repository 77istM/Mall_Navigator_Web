"""Monitoring helpers: logging, error tracking, and performance events."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(log_file: str = "data/app.log") -> None:
    """Configure root logging once with both file and console handlers."""
    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(logging.INFO)
    formatter = logging.Formatter(_LOG_FORMAT)

    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    root.addHandler(file_handler)
    root.addHandler(stream_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)


def setup_sentry(dsn: str | None) -> bool:
    """Initialize Sentry if configured; returns True when active."""
    if not dsn:
        return False
    try:
        sentry_sdk = importlib.import_module("sentry_sdk")

        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=0.1,
            send_default_pii=False,
        )
        return True
    except Exception:
        logging.getLogger(__name__).exception("Failed to initialize Sentry")
        return False


def log_event(logger: logging.Logger, *, event: str, level: int = logging.INFO, **fields: Any) -> None:
    """Emit a structured JSON log event."""
    payload: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
    }
    payload.update(fields)
    logger.log(level, json.dumps(payload, ensure_ascii=True, default=str))
