"""User repository — syncs Clerk identities into the local `users` table."""

from contextlib import asynccontextmanager

import asyncpg

from db.connection import get_connection, get_transaction, is_db_ready


async def ensure_user(conn: asyncpg.Connection, clerk_id: str, email: str | None = None) -> str:
    """Return the internal users.id for a Clerk subject, creating if needed.

    Rows are created lazily so that API calls work even before the Clerk
    webhook has synced the user.
    """
    row = await conn.fetchrow(
        "SELECT id FROM users WHERE clerk_id = $1",
        clerk_id,
    )
    if row:
        return row["id"]

    row = await conn.fetchrow(
        """
        INSERT INTO users (clerk_id, email)
        VALUES ($1, $2)
        ON CONFLICT (clerk_id) DO UPDATE SET updated_at = now()
        RETURNING id
        """,
        clerk_id,
        email or f"{clerk_id}@placeholder.local",
    )
    return row["id"]


async def set_rls_user(conn: asyncpg.Connection, user_id: str) -> None:
    """Set the row-level-security session variable for the current transaction."""
    await conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(user_id))


@asynccontextmanager
async def user_connection(clerk_id: str):
    """Yield (conn, internal_user_id) with RLS scoped to the user."""
    async with get_connection() as conn:
        internal_id = await ensure_user(conn, clerk_id)
        await set_rls_user(conn, internal_id)
        yield conn, internal_id


@asynccontextmanager
async def user_transaction(clerk_id: str):
    """Yield (conn, internal_user_id) inside a transaction with RLS scoped."""
    async with get_transaction() as conn:
        internal_id = await ensure_user(conn, clerk_id)
        await set_rls_user(conn, internal_id)
        yield conn, internal_id


@asynccontextmanager
async def rls_connection(internal_id: str):
    """Read-only connection scoped to an already-resolved internal user id."""
    async with get_connection() as conn:
        await set_rls_user(conn, internal_id)
        yield conn


@asynccontextmanager
async def rls_transaction(internal_id: str):
    """Transaction scoped to an already-resolved internal user id."""
    async with get_transaction() as conn:
        await set_rls_user(conn, internal_id)
        yield conn


async def sync_user_from_clerk(
    clerk_id: str,
    email: str | None = None,
    full_name: str | None = None,
    avatar_url: str | None = None,
) -> str | None:
    """Upsert a user row from a Clerk webhook event."""
    if not is_db_ready():
        return None
    async with get_transaction() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO users (clerk_id, email, full_name, avatar_url)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (clerk_id) DO UPDATE SET
                email = EXCLUDED.email,
                full_name = EXCLUDED.full_name,
                avatar_url = EXCLUDED.avatar_url,
                updated_at = now()
            RETURNING id
            """,
            clerk_id,
            email or f"{clerk_id}@placeholder.local",
            full_name,
            avatar_url,
        )
        return row["id"]


async def delete_user_by_clerk_id(clerk_id: str) -> None:
    """Remove a user (and cascaded rows) when Clerk reports deletion."""
    if not is_db_ready():
        return
    async with get_transaction() as conn:
        await conn.execute("DELETE FROM users WHERE clerk_id = $1", clerk_id)
