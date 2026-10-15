"""User repository — syncs Clerk identities into the local `users` table."""

import asyncpg


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
