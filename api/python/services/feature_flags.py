"""Feature flags with deterministic percentage rollout (Task 4.6).

Defaults live in code so the API works without a database; rows in the
`feature_flags` table override them when present.
"""

import hashlib

from db.connection import get_connection, is_db_ready

DEFAULT_FLAGS: dict[str, dict] = {
    "ensemble_model": {"description": "Soft-voting ensemble scoring with calibration", "enabled": True, "rollout_percentage": 100},
    "pdf_export": {"description": "Client and server-side PDF reports", "enabled": True, "rollout_percentage": 100},
    "fhir_export": {"description": "FHIR R4 / CDA interoperability export", "enabled": True, "rollout_percentage": 100},
    "device_sync": {"description": "Connected device data sync", "enabled": True, "rollout_percentage": 100},
    "third_party_api": {"description": "API-key access for third parties", "enabled": False, "rollout_percentage": 0},
    "ai_assistant": {"description": "Conversational risk explanation", "enabled": False, "rollout_percentage": 0},
}


def _bucket(user_id: str) -> int:
    """Stable 0-99 bucket for a user, so rollouts are consistent."""
    return int(hashlib.sha256(user_id.encode()).hexdigest(), 16) % 100


def evaluate(flag: dict, user_id: str | None = None) -> bool:
    if not flag.get("enabled"):
        return False
    percentage = int(flag.get("rollout_percentage", 0))
    if percentage >= 100 or not user_id:
        return True
    return _bucket(user_id) < percentage


async def get_all_flags() -> list[dict]:
    """Return the effective flag set (code defaults overridden by the DB)."""
    flags = {key: dict(value) for key, value in DEFAULT_FLAGS.items()}

    if is_db_ready():
        try:
            async with get_connection() as conn:
                rows = await conn.fetch(
                    "SELECT key, description, enabled, rollout_percentage FROM feature_flags"
                )
            for row in rows:
                current = flags.get(row["key"], {})
                flags[row["key"]] = {
                    "description": row["description"] or current.get("description", ""),
                    "enabled": bool(row["enabled"]),
                    "rollout_percentage": int(row["rollout_percentage"] or 0),
                }
        except Exception:
            pass  # fall back to code defaults

    return [{"key": key, **value} for key, value in flags.items()]
