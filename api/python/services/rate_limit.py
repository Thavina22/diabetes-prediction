"""Fixed-window rate limiting (Task 4.4).

Uses Upstash Redis over its REST API when configured, otherwise an in-process
fallback. Both implement the same fixed-window (60s) counter.
"""

import logging
import time
from collections import defaultdict, deque

import httpx

from config import get_settings

log = logging.getLogger(__name__)
WINDOW_SECONDS = 60

_memory: dict[str, deque[float]] = defaultdict(deque)


def _memory_check(key: str, limit: int) -> tuple[bool, int]:
    now = time.monotonic()
    bucket = _memory[key]
    while bucket and now - bucket[0] > WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= limit:
        return False, 0
    bucket.append(now)
    return True, max(0, limit - len(bucket))


async def _upstash_check(key: str, limit: int, url: str, token: str) -> tuple[bool, int]:
    endpoint = url.rstrip("/")
    headers = {"Authorization": f"Bearer {token}"}
    window_id = int(time.time()) // WINDOW_SECONDS
    redis_key = f"dri:rl:{key}:{window_id}"
    async with httpx.AsyncClient(timeout=2.0) as client:
        res = await client.post(endpoint, headers=headers, json=["INCR", redis_key])
        res.raise_for_status()
        count = int(res.json()["result"])
        if count == 1:
            await client.post(endpoint, headers=headers, json=["EXPIRE", redis_key, WINDOW_SECONDS])
    return count <= limit, max(0, limit - count)


async def check_rate_limit(key: str, limit: int) -> tuple[bool, int]:
    """Return (allowed, remaining) for the current window."""
    settings = get_settings()
    if settings.UPSTASH_REDIS_REST_URL and settings.UPSTASH_REDIS_REST_TOKEN:
        try:
            return await _upstash_check(
                key, limit, settings.UPSTASH_REDIS_REST_URL, settings.UPSTASH_REDIS_REST_TOKEN
            )
        except Exception as exc:  # noqa: BLE001 - never fail open on infra error? log and fall through
            log.warning("Upstash rate limit unavailable (%s); using in-memory fallback", exc)
    return _memory_check(key, limit)
