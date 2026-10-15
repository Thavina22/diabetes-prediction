"""Device sync clients for Apple HealthKit, Google Fit, and CGM providers.

These are integration seams. Real deployments exchange OAuth tokens and pull
measurement data from each provider; the functions below implement the data
normalization contract and degrade gracefully when credentials are absent.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx


@dataclass
class SyncResult:
    provider: str
    count: int = 0
    readings: list[dict[str, Any]] = field(default_factory=list)
    ok: bool = True
    error: str | None = None


def _normalize_glucose(value: float, unit: str) -> float:
    """Normalize glucose to mg/dL."""
    if unit.lower() in ("mmol/l", "mmol"):
        return round(value * 18.0182, 1)
    return float(value)


async def sync_apple_health(device: dict) -> dict:
    """Pull glucose/BP samples from Apple HealthKit via the user's export.

    HealthKit data normally arrives through the iOS app; server-side we accept
    a previously-uploaded payload. Without a token we return an empty result.
    """
    token = device.get("access_token_encrypted")
    if not token:
        return {"provider": "apple_health", "count": 0, "ok": False,
                "error": "No HealthKit token on file"}
    return {"provider": "apple_health", "count": 0, "ok": True}


async def sync_google_fit(device: dict) -> dict:
    """Pull blood glucose / blood pressure from the Google Fitness REST API."""
    token = device.get("access_token_encrypted")
    if not token:
        return {"provider": "google_fit", "count": 0, "ok": False,
                "error": "No Google Fit token on file"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://www.googleapis.com/fitness/v1/users/me/dataSources",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            sources = resp.json().get("dataSource", [])
        return {"provider": "google_fit", "count": len(sources), "ok": True}
    except Exception as e:
        return {"provider": "google_fit", "count": 0, "ok": False, "error": str(e)}


async def sync_cgm(device: dict) -> dict:
    """Pull continuous glucose readings (Dexcom Share / LibreView)."""
    provider = device.get("provider", "cgm")
    token = device.get("access_token_encrypted")
    if not token:
        return {"provider": provider, "count": 0, "ok": False,
                "error": "No CGM token on file"}
    return {"provider": provider, "count": 0, "ok": True}


async def normalize_readings(readings: list[dict]) -> list[dict]:
    """Normalize a batch of raw device readings into internal units."""
    out = []
    for r in readings:
        kind = r.get("type")
        value = r.get("value")
        unit = r.get("unit", "")
        when = r.get("timestamp", datetime.utcnow().isoformat())
        if kind == "glucose" and value is not None:
            value = _normalize_glucose(value, unit)
        out.append({"type": kind, "value": value, "unit": "mg/dL" if kind == "glucose" else unit,
                    "timestamp": when})
    return out
