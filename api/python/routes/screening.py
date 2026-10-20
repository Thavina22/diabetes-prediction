from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from models.screening import ScreeningInput, ScreeningResult
from services.screening_engine import build_result as _build_result
from db.connection import get_connection, get_transaction, is_db_ready
from db.repositories.users import ensure_user, set_rls_user
from auth.clerk import get_current_user_id
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/screening", response_model=ScreeningResult, status_code=status.HTTP_201_CREATED)
async def create_screening(
    input_data: ScreeningInput,
    user_id: str = Depends(get_current_user_id),
):
    """Run full clinical screening and store the result.

    When a database is configured the result is persisted; otherwise the
    computed result is returned statelessly (development mode).
    """
    try:
        result = _build_result(input_data, user_id)

        if is_db_ready():
            async with get_transaction() as conn:
                internal_id = await ensure_user(conn, user_id)
                await set_rls_user(conn, internal_id)
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

        return result
    except HTTPException:
    raise
except Exception as e:
    logger.exception("Screening failed")
    raise HTTPException(
        status_code=500,
        detail=f"Screening failed: {str(e)}"
    )


@router.get("/screening/{screening_id}", response_model=ScreeningResult)
async def get_screening(
    screening_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    """Get a specific screening result."""
    if not is_db_ready():
        raise HTTPException(status_code=503, detail="Persistence not configured")
    async with get_connection() as conn:
        internal_id = await ensure_user(conn, user_id)
        row = await conn.fetchrow(
            "SELECT * FROM screenings WHERE id = $1 AND user_id = $2",
            screening_id, internal_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Screening not found")
        return ScreeningResult.model_validate_json(row["result_json"])
