"""Rate limiting — fixed-window counter (in-memory fallback, no Redis needed)."""

import asyncio
import uuid

from services import rate_limit


def _key() -> str:
    return f"test-{uuid.uuid4()}"


def test_requests_under_limit_are_allowed():
    allowed, remaining = asyncio.run(rate_limit.check_rate_limit(_key(), limit=3))
    assert allowed is True
    assert remaining == 2


def test_limit_is_enforced():
    key = _key()
    for _ in range(3):
        allowed, _ = asyncio.run(rate_limit.check_rate_limit(key, limit=3))
        assert allowed is True

    allowed, remaining = asyncio.run(rate_limit.check_rate_limit(key, limit=3))
    assert allowed is False
    assert remaining == 0


def test_keys_are_isolated():
    a, b = _key(), _key()
    asyncio.run(rate_limit.check_rate_limit(a, limit=1))
    allowed, _ = asyncio.run(rate_limit.check_rate_limit(b, limit=1))
    assert allowed is True
