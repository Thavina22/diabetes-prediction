from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import hashlib

from models.api_key import ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse, ApiKeyCreateResponse, generate_api_key, verify_api_key
from db.connection import get_connection, get_transaction
from auth.clerk import get_current_user_id, get_current_user_id_from_api_key

router = APIRouter()


# User-facing API key management
@router.get("/third-party/api-keys", response_model=List[ApiKeyResponse])
async def list_api_keys(user_id: str = Depends(get_current_user_id)):
    async with get_connection() as conn:
        rows = await conn.fetch("""
            SELECT id, name, key_prefix, scopes, rate_limit_rpm, last_used_at, expires_at, created_at
            FROM api_keys WHERE user_id = $1 ORDER BY created_at DESC
        """, user_id)
        return [ApiKeyResponse.model_validate(dict(row)) for row in rows]


@router.post("/third-party/api-keys", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    api_key: ApiKeyCreate,
    user_id: str = Depends(get_current_user_id),
):
    full_key, key_prefix, key_hash = generate_api_key()
    async with get_transaction() as conn:
        row = await conn.fetchrow("""
            INSERT INTO api_keys (user_id, name, key_hash, key_prefix, scopes, rate_limit_rpm, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, name, key_prefix, scopes, rate_limit_rpm, expires_at, created_at
        """, user_id, api_key.name, key_hash, key_prefix, api_key.scopes, api_key.rate_limit_rpm, api_key.expires_at)
        return ApiKeyCreateResponse(
            id=row["id"],
            name=row["name"],
            key=full_key,  # Only returned once!
            key_prefix=row["key_prefix"],
            scopes=row["scopes"],
            rate_limit_rpm=row["rate_limit_rpm"],
            expires_at=row["expires_at"],
            created_at=row["created_at"],
        )


@router.patch("/third-party/api-keys/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    key_id: UUID,
    api_key: ApiKeyUpdate,
    user_id: str = Depends(get_current_user_id),
):
    async with get_transaction() as conn:
        row = await conn.fetchrow("""
            UPDATE api_keys
            SET name = COALESCE($1, name),
                scopes = COALESCE($2, scopes),
                rate_limit_rpm = COALESCE($3, rate_limit_rpm),
                expires_at = COALESCE($4, expires_at)
            WHERE id = $5 AND user_id = $6
            RETURNING id, name, key_prefix, scopes, rate_limit_rpm, last_used_at, expires_at, created_at
        """, api_key.name, api_key.scopes, api_key.rate_limit_rpm, api_key.expires_at, key_id, user_id)
        if not row:
            raise HTTPException(status_code=404, detail="API key not found")
        return ApiKeyResponse.model_validate(dict(row))


@router.delete("/third-party/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    async with get_transaction() as conn:
        result = await conn.execute("""
            DELETE FROM api_keys WHERE id = $1 AND user_id = $2
        """, key_id, user_id)
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="API key not found")


# API key authentication dependency
async def verify_api_key_auth(
    request: Request,
    authorization: Optional[str] = Header(None),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    api_key = authorization[7:]  # Remove "Bearer "
    key_prefix = api_key[:12]

    async with get_connection() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM api_keys WHERE key_prefix = $1
        """, key_prefix)

        if not row:
            raise HTTPException(status_code=401, detail="Invalid API key")

        if not verify_api_key(api_key, row["key_hash"]):
            raise HTTPException(status_code=401, detail="Invalid API key")

        if row["expires_at"] and row["expires_at"] < datetime.utcnow():
            raise HTTPException(status_code=401, detail="API key expired")

        # Check rate limit (simplified - in production use Redis)
        # TODO: Implement Upstash Redis rate limiting

        # Update last_used_at
        await conn.execute("""
            UPDATE api_keys SET last_used_at = $1 WHERE id = $2
        """, datetime.utcnow(), row["id"])

        # Set user_id in request state for RLS
        request.state.user_id = str(row["user_id"])

        return row


# Third-party screening endpoint
@router.post("/third-party/screening")
async def third_party_screening(
    request: Request,
    # input_data would come from body - simplified for now
    api_key_data: dict = Depends(verify_api_key_auth),
):
    user_id = request.state.user_id
    # Run screening for the API key's user
    # This would use the same logic as the regular screening endpoint
    return {"status": "ok", "message": "Screening endpoint for API keys - to be implemented"}


@router.get("/third-party/history")
async def third_party_history(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    api_key_data: dict = Depends(verify_api_key_auth),
):
    user_id = request.state.user_id
    async with get_connection() as conn:
        rows = await conn.fetch("""
            SELECT id, health_score, risk_category, created_at
            FROM screenings WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3
        """, user_id, limit, offset)
        return {"screenings": [dict(row) for row in rows]}