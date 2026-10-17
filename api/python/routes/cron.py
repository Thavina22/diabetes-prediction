"""Background device sync (Task 3.6).

Invoked by Vercel Cron (`vercel.json`) with
`Authorization: Bearer $CRON_SECRET`, or manually for a single user via the
/devices/{id}/sync endpoint.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from config import get_settings
from db.connection import get_transaction, is_db_ready
from services.device_sync import sync_apple_health, sync_google_fit, sync_cgm

logger = logging.getLogger(__name__)
router = APIRouter()

_SYNCERS = {
    "apple_health": sync_apple_health,
    "google_fit": sync_google_fit,
    "dexcom": sync_cgm,
    "libre": sync_cgm,
}


def _authorized(request: Request) -> None:
    settings = get_settings()
    if not settings.CRON_SECRET:
        return
    if request.headers.get("authorization") != f"Bearer {settings.CRON_SECRET}":
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/cron/sync-devices")
@router.post("/cron/sync-devices")
async def sync_all_devices(request: Request):
    _authorized(request)

    if not is_db_ready():
        return {"status": "skipped", "reason": "persistence not configured"}

    async with get_transaction() as conn:
        rows = await conn.fetch(
            "SELECT * FROM device_connections WHERE is_active = true"
        )

    synced, failed = 0, 0
    for row in rows:
        device = dict(row)
        syncer = _SYNCERS.get(device["provider"])
        if not syncer:
            continue
        try:
            await syncer(device)
            async with get_transaction() as conn:
                await conn.execute(
                    "UPDATE device_connections SET last_sync_at = $1 WHERE id = $2",
                    datetime.utcnow(),
                    device["id"],
                )
            synced += 1
        except Exception:  # noqa: BLE001 - keep the cron run going
            logger.exception("Device sync failed for %s", device.get("id"))
            failed += 1

    return {"status": "ok", "synced": synced, "failed": failed}
