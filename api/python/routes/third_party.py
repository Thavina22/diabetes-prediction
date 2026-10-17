from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from models.api_key import (
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyResponse,
    ApiKeyUpdate,
    generate_api_key,
    verify_api_key,
)
from models.screening import ScreeningInput
from db.connection import get_connection, is_db_ready
from db.repositories.users import rls_connection, rls_transaction, user_connection, user_transaction
from auth.clerk import get_current_user_id
from services.rate_limit import check_rate_limit
from services.screening_engine import build_result

router = APIRouter()

VALID_SCOPES = {"screening:read", "screening:write", "history:read", "export:read"}


def _require_db() -> None:
    if not is_db_ready():
        raise HTTPException(status_code=503, detail="Persistence not configured")


# --- API-key authentication -------------------------------------------------

async def verify_api_key_auth(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    _require_db()

    api_key = authorization[7:]
    key_prefix = api_key[:12]

    async with get_connection() as conn:
        row = await conn.fetchrow("SELECT * FROM api_keys WHERE key_prefix = $1", key_prefix)
        if not row or not verify_api_key(api_key, row["key_hash"]):
            raise HTTPException(status_code=401, detail="Invalid API key")
        if row["expires_at"] and row["expires_at"].replace(tzinfo=None) < datetime.utcnow():
            raise HTTPException(status_code=401, detail="API key expired")

        allowed, remaining = await check_rate_limit(f"key:{row['id']}", int(row["rate_limit_rpm"]))
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60", "X-RateLimit-Remaining": "0"},
            )

        await conn.execute(
            "UPDATE api_keys SET last_used_at = $1 WHERE id = $2", datetime.utcnow(), row["id"]
        )

    data = dict(row)
    request.state.api_key = data
    request.state.rate_limit_remaining = remaining
    return data


def require_scope(scope: str):
    """Dependency factory enforcing a scope on an API-key-authenticated route."""

    async def _check(api_key: dict = Depends(verify_api_key_auth)) -> dict:
        if scope not in (api_key.get("scopes") or []):
            raise HTTPException(
                status_code=403, detail=f"API key missing required scope: {scope}"
            )
        return api_key

    return _check


# --- User-facing API key management ----------------------------------------

@router.get("/third-party/api-keys", response_model=List[ApiKeyResponse])
async def list_api_keys(user_id: str = Depends(get_current_user_id)):
    if not is_db_ready():
        return []
    async with user_connection(user_id) as (conn, internal_id):
        rows = await conn.fetch(
            """
            SELECT id, name, key_prefix, scopes, rate_limit_rpm, last_used_at, expires_at, created_at
            FROM api_keys WHERE user_id = $1 ORDER BY created_at DESC
            """,
            internal_id,
        )
        return [ApiKeyResponse.model_validate(dict(row)) for row in rows]


@router.post("/third-party/api-keys", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    api_key: ApiKeyCreate,
    user_id: str = Depends(get_current_user_id),
):
    _require_db()
    invalid = set(api_key.scopes) - VALID_SCOPES
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown scopes: {sorted(invalid)}")

    full_key, key_prefix, key_hash = generate_api_key()
    async with user_transaction(user_id) as (conn, internal_id):
        row = await conn.fetchrow(
            """
            INSERT INTO api_keys (user_id, name, key_hash, key_prefix, scopes, rate_limit_rpm, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, name, key_prefix, scopes, rate_limit_rpm, expires_at, created_at
            """,
            internal_id,
            api_key.name,
            key_hash,
            key_prefix,
            api_key.scopes,
            api_key.rate_limit_rpm,
            api_key.expires_at,
        )
        return ApiKeyCreateResponse(
            id=row["id"],
            name=row["name"],
            key=full_key,  # full key returned exactly once
            key_prefix=row["key_prefix"],
            scopes=list(row["scopes"]),
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
    _require_db()
    if api_key.scopes is not None:
        invalid = set(api_key.scopes) - VALID_SCOPES
        if invalid:
            raise HTTPException(status_code=400, detail=f"Unknown scopes: {sorted(invalid)}")

    async with user_transaction(user_id) as (conn, internal_id):
        row = await conn.fetchrow(
            """
            UPDATE api_keys
            SET name = COALESCE($1, name),
                scopes = COALESCE($2, scopes),
                rate_limit_rpm = COALESCE($3, rate_limit_rpm),
                expires_at = COALESCE($4, expires_at)
            WHERE id = $5 AND user_id = $6
            RETURNING id, name, key_prefix, scopes, rate_limit_rpm, last_used_at, expires_at, created_at
            """,
            api_key.name,
            api_key.scopes,
            api_key.rate_limit_rpm,
            api_key.expires_at,
            key_id,
            internal_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="API key not found")
        return ApiKeyResponse.model_validate(dict(row))


@router.delete("/third-party/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    _require_db()
    async with user_transaction(user_id) as (conn, internal_id):
        result = await conn.execute(
            "DELETE FROM api_keys WHERE id = $1 AND user_id = $2", key_id, internal_id
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="API key not found")


# --- Third-party endpoints --------------------------------------------------

@router.post("/third-party/screening", status_code=status.HTTP_201_CREATED)
async def third_party_screening(
    input_data: ScreeningInput,
    request: Request,
    api_key: dict = Depends(require_scope("screening:write")),
):
    """Run a screening on behalf of the API key owner."""
    internal_id = api_key["user_id"]
    result = build_result(input_data, str(internal_id))

    try:
        async with rls_transaction(internal_id) as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO screenings (user_id, input_json, result_json, health_score, risk_category)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, created_at
                """,
                internal_id,
                input_data.model_dump_json(),
                result.model_dump_json(),
                result.health_score,
                result.risk_category,
            )
            result.id = row["id"]
            result.created_at = row["created_at"]
    except Exception:  # noqa: BLE001 - still return the computed result if persistence fails
        pass

    return {
        "id": str(result.id),
        "user_id": str(result.user_id),
        "created_at": result.created_at,
        "health_score": result.health_score,
        "risk_category": result.risk_category,
        "ml_result": result.ml_result,
        "rate_limit_remaining": request.state.rate_limit_remaining,
    }


@router.get("/third-party/history")
async def third_party_history(
    limit: int = 20,
    offset: int = 0,
    api_key: dict = Depends(require_scope("history:read")),
):
    async with rls_connection(api_key["user_id"]) as conn:
        rows = await conn.fetch(
            """
            SELECT id, health_score, risk_category, created_at
            FROM screenings WHERE user_id = $1
            ORDER BY created_at DESC LIMIT $2 OFFSET $3
            """,
            api_key["user_id"],
            limit,
            offset,
        )
        return {"screenings": [dict(row) for row in rows]}
