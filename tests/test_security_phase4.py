"""Phase 4 security and privacy utility tests."""

from __future__ import annotations

from utils.security import InMemoryRateLimiter, hash_password, sanitize_query, sanitize_text, verify_password


def test_sanitize_text_removes_unsafe_chars() -> None:
    dirty = "<script>alert(1)</script>   milk\\n"
    clean = sanitize_text(dirty)
    assert "<" not in clean
    assert ">" not in clean
    assert "script" in clean.lower()


def test_sanitize_query_normalizes_case() -> None:
    assert sanitize_query("  APPLE!!  ") == "apple"


def test_password_hash_and_verify_roundtrip() -> None:
    salt = "abc123salt"
    expected = hash_password("secret-pass", salt)
    assert verify_password("secret-pass", salt, expected) is True
    assert verify_password("wrong", salt, expected) is False


def test_rate_limiter_blocks_excess_requests() -> None:
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    assert limiter.allow("u1").allowed is True
    assert limiter.allow("u1").allowed is True
    third = limiter.allow("u1")
    assert third.allowed is False
    assert third.retry_after_seconds > 0
