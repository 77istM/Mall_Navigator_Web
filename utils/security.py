"""Security helpers for input sanitization, auth, and rate limiting."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import hashlib
import hmac
import re
import secrets
import time
from typing import Deque

_ALLOWED_TEXT_RE = re.compile(r"[^a-zA-Z0-9 _\-.,'&()/:+]", flags=re.ASCII)


def sanitize_text(value: str, *, max_len: int = 120) -> str:
    """Return a cleaned, bounded text value safe for logs and storage."""
    clipped = str(value or "")[:max_len]
    normalized = " ".join(clipped.replace("\n", " ").replace("\r", " ").split())
    return _ALLOWED_TEXT_RE.sub("", normalized)


def sanitize_query(value: str, *, max_len: int = 80) -> str:
    """Return normalized query text suitable for product search."""
    return sanitize_text(value, max_len=max_len).lower()


def is_valid_product_name(value: str) -> bool:
    """Validate product names after sanitization."""
    clean = sanitize_text(value, max_len=80)
    return 2 <= len(clean) <= 80


def generate_password_salt() -> str:
    """Generate a random hex salt for admin password hashing."""
    return secrets.token_hex(16)


def hash_password(password: str, salt: str, *, iterations: int = 200_000) -> str:
    """Generate a PBKDF2-HMAC-SHA256 hex digest for a password."""
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return digest.hex()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """Constant-time password verification."""
    if not password or not salt or not expected_hash:
        return False
    actual = hash_password(password, salt)
    return hmac.compare_digest(actual, expected_hash.strip().lower())


@dataclass(slots=True)
class RateLimitResult:
    """Result object for a rate-limit check."""

    allowed: bool
    retry_after_seconds: float


class InMemoryRateLimiter:
    """Simple sliding-window limiter for per-session action throttling."""

    def __init__(self, *, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._events: dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> RateLimitResult:
        now = time.monotonic()
        window_start = now - float(self.window_seconds)
        events = self._events[key]

        while events and events[0] < window_start:
            events.popleft()

        if len(events) >= self.max_requests:
            retry_after = max(0.0, self.window_seconds - (now - events[0]))
            return RateLimitResult(allowed=False, retry_after_seconds=retry_after)

        events.append(now)
        return RateLimitResult(allowed=True, retry_after_seconds=0.0)
