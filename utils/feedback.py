"""User feedback capture utilities."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from utils.security import sanitize_text


def save_feedback(
    *,
    message: str,
    contact: str,
    context: dict[str, Any],
    storage_path: str = "data/feedback_reports.jsonl",
) -> dict[str, Any]:
    """Persist a feedback report as a JSON-lines entry."""
    clean_message = sanitize_text(message, max_len=600)
    clean_contact = sanitize_text(contact, max_len=120)
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "message": clean_message,
        "contact": clean_contact,
        "context": context,
    }

    path = Path(storage_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    return payload
