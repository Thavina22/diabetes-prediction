"""Device provider uniqueness + hardened RLS policies

Revision ID: 002
Revises: 001
Create Date: 2026-10-15

Adds the (user_id, provider) uniqueness that the devices upsert relies on,
and rewrites the row-level-security policies so that:
  * writes are validated with an explicit WITH CHECK, and
  * the session variable is read with missing_ok so an unset value yields a
    NULL comparison instead of raising "unrecognized configuration parameter".
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

TABLES = ["screenings", "device_connections", "medications", "audit_logs", "api_keys"]

# Owner-bypassable expression: returns NULL (no rows) when the setting is unset.
CURRENT_USER = "NULLIF(current_setting('app.current_user_id', true), '')::uuid"


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_device_connections_user_provider",
        "device_connections",
        ["user_id", "provider"],
    )

    for table in TABLES:
        op.execute(f'DROP POLICY IF EXISTS "Users see own {table}" ON {table};')
        op.execute(
            f"""
            CREATE POLICY "Users see own {table}" ON {table}
            USING ({CURRENT_USER} IS NOT NULL AND user_id = {CURRENT_USER})
            WITH CHECK ({CURRENT_USER} IS NOT NULL AND user_id = {CURRENT_USER});
            """
        )


def downgrade() -> None:
    for table in TABLES:
        op.execute(f'DROP POLICY IF EXISTS "Users see own {table}" ON {table};')
        op.execute(
            f"""
            CREATE POLICY "Users see own {table}" ON {table}
            USING (user_id = current_setting('app.current_user_id')::uuid);
            """
        )

    op.drop_constraint(
        "uq_device_connections_user_provider",
        "device_connections",
        type_="unique",
    )
