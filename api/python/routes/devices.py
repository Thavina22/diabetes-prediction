from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from models.user import (
    DeviceConnectionCreate,
    DeviceConnectionUpdate,
    DeviceConnectionResponse,
    MedicationCreate,
    MedicationResponse,
)
from db.connection import is_db_ready
from db.repositories.users import user_connection, user_transaction
from auth.clerk import get_current_user_id
from services.device_sync import sync_apple_health, sync_google_fit, sync_cgm

router = APIRouter()


def _require_db() -> None:
    if not is_db_ready():
        raise HTTPException(status_code=503, detail="Persistence not configured")


# Device connections
@router.get("/devices", response_model=list[DeviceConnectionResponse])
async def list_devices(user_id: str = Depends(get_current_user_id)):
    """List user's connected devices."""
    if not is_db_ready():
        return []
    async with user_connection(user_id) as (conn, internal_id):
        rows = await conn.fetch(
            """
            SELECT * FROM device_connections
            WHERE user_id = $1 AND is_active = true
            ORDER BY created_at DESC
            """,
            internal_id,
        )
        return [DeviceConnectionResponse.model_validate(dict(row)) for row in rows]


@router.post("/devices", response_model=DeviceConnectionResponse, status_code=status.HTTP_201_CREATED)
async def connect_device(
    device: DeviceConnectionCreate,
    user_id: str = Depends(get_current_user_id),
):
    """Connect a new device."""
    _require_db()
    async with user_transaction(user_id) as (conn, internal_id):
        row = await conn.fetchrow(
            """
            INSERT INTO device_connections (user_id, provider, access_token_encrypted, refresh_token_encrypted, token_expires_at)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id, provider) DO UPDATE SET
                access_token_encrypted = EXCLUDED.access_token_encrypted,
                refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
                token_expires_at = EXCLUDED.token_expires_at,
                is_active = true
            RETURNING *
            """,
            internal_id,
            device.provider,
            device.access_token_encrypted,
            device.refresh_token_encrypted,
            device.token_expires_at,
        )
        return DeviceConnectionResponse.model_validate(dict(row))


@router.patch("/devices/{device_id}", response_model=DeviceConnectionResponse)
async def update_device(
    device_id: UUID,
    device: DeviceConnectionUpdate,
    user_id: str = Depends(get_current_user_id),
):
    """Update device connection."""
    _require_db()
    async with user_transaction(user_id) as (conn, internal_id):
        row = await conn.fetchrow(
            """
            UPDATE device_connections
            SET access_token_encrypted = COALESCE($1, access_token_encrypted),
                refresh_token_encrypted = COALESCE($2, refresh_token_encrypted),
                token_expires_at = COALESCE($3, token_expires_at),
                last_sync_at = COALESCE($4, last_sync_at),
                is_active = COALESCE($5, is_active)
            WHERE id = $6 AND user_id = $7
            RETURNING *
            """,
            device.access_token_encrypted,
            device.refresh_token_encrypted,
            device.token_expires_at,
            device.last_sync_at,
            device.is_active,
            device_id,
            internal_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Device not found")
        return DeviceConnectionResponse.model_validate(dict(row))


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_device(
    device_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    """Disconnect a device."""
    _require_db()
    async with user_transaction(user_id) as (conn, internal_id):
        result = await conn.execute(
            "DELETE FROM device_connections WHERE id = $1 AND user_id = $2",
            device_id,
            internal_id,
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Device not found")


@router.post("/devices/{device_id}/sync")
async def sync_device(
    device_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    """Trigger manual sync for a device."""
    _require_db()
    async with user_connection(user_id) as (conn, internal_id):
        row = await conn.fetchrow(
            "SELECT * FROM device_connections WHERE id = $1 AND user_id = $2",
            device_id,
            internal_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Device not found")
        provider = row["provider"]

    if provider == "apple_health":
        result = await sync_apple_health(dict(row))
    elif provider == "google_fit":
        result = await sync_google_fit(dict(row))
    elif provider in ("dexcom", "libre"):
        result = await sync_cgm(dict(row))
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    async with user_transaction(user_id) as (conn, _):
        await conn.execute(
            "UPDATE device_connections SET last_sync_at = $1 WHERE id = $2",
            datetime.utcnow(),
            device_id,
        )

    return {"status": "success", "synced_records": result.get("count", 0)}


# Medications
@router.get("/medications", response_model=list[MedicationResponse])
async def list_medications(user_id: str = Depends(get_current_user_id)):
    if not is_db_ready():
        return []
    async with user_connection(user_id) as (conn, internal_id):
        rows = await conn.fetch(
            "SELECT * FROM medications WHERE user_id = $1 ORDER BY created_at DESC",
            internal_id,
        )
        return [MedicationResponse.model_validate(dict(row)) for row in rows]


@router.post("/medications", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
async def add_medication(
    medication: MedicationCreate,
    user_id: str = Depends(get_current_user_id),
):
    _require_db()
    async with user_transaction(user_id) as (conn, internal_id):
        row = await conn.fetchrow(
            """
            INSERT INTO medications (user_id, name, dosage, frequency, started_at, ended_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            internal_id,
            medication.name,
            medication.dosage,
            medication.frequency,
            medication.started_at,
            medication.ended_at,
        )
        return MedicationResponse.model_validate(dict(row))


@router.delete("/medications/{med_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication(
    med_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    _require_db()
    async with user_transaction(user_id) as (conn, internal_id):
        result = await conn.execute(
            "DELETE FROM medications WHERE id = $1 AND user_id = $2",
            med_id,
            internal_id,
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Medication not found")
