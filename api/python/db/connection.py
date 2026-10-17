import logging
from contextlib import asynccontextmanager

import asyncpg

from config import get_settings

log = logging.getLogger("dri.db")

_pool: asyncpg.Pool | None = None


async def init_db() -> None:
    """Create the connection pool. Degrades gracefully when no DB is configured."""
    global _pool
    settings = get_settings()
    if not settings.DATABASE_URL:
        log.warning("DATABASE_URL not set — running without persistence (stateless mode)")
        _pool = None
        return
    try:
        _pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=1,
            max_size=10,
            command_timeout=60,
        )
        async with _pool.acquire() as conn:
            await conn.execute("SELECT 1")
    except Exception as e:  # pragma: no cover - environment dependent
        log.warning("Database unavailable (%s) — running without persistence", e)
        _pool = None


async def close_db() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def is_db_ready() -> bool:
    return _pool is not None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db() first.")
    return _pool


@asynccontextmanager
async def get_connection():
    pool = get_pool()
    async with pool.acquire() as conn:
        yield conn


@asynccontextmanager
async def get_transaction():
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            yield conn
