from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from models.screening import (
    ScreeningInput, ScreeningResult,
    MLResult, FollowupSchedule, EmergencyFlag,
)
from services import clinical_rules as cr
from services.ml_model import predict_risk_with_shap
from db.connection import get_connection, get_transaction, is_db_ready
from db.repositories.users import ensure_user, set_rls_user
from auth.clerk import get_current_user_id

router = APIRouter()


def _build_result(input_data: ScreeningInput, user_id: str) -> ScreeningResult:
    """Run all engines and assemble a ScreeningResult."""
    screening = cr.run_clinical_screening(input_data)
    ml = predict_risk_with_shap(input_data)

    glucose_rules = screening["glucose_rules"]
    bp_rule = screening["bp_rule"]
    bmi_rule = screening["bmi_rule"]
    lipid_rules = screening["lipid_rules"]

    health_score, _ = cr.calculate_health_score(
        glucose_rules, bp_rule, bmi_rule, lipid_rules, ml
    )

    overall_severity = screening["aggregate"]["overall"]["severity"]
    followup = cr.followup_schedule(glucose_rules, bp_rule, overall_severity)

    risk = cr.stratify_risk(
        glucose_rules, bp_rule, bmi_rule, lipid_rules, ml, input_data.age
    )
    category_map = {
        "Low": "low", "Medium": "medium",
        "High": "high", "Very High": "very_high",
    }
    risk_category = category_map.get(risk["level"], "low")

    emergency_flags = cr.emergency_protocols(glucose_rules, bp_rule)

    return ScreeningResult(
        id=uuid4(),
        user_id=user_id,
        created_at=datetime.utcnow(),
        input=input_data,
        glucose_rules=glucose_rules,
        bp_rule=bp_rule,
        bmi_rule=bmi_rule,
        lipid_rules=lipid_rules,
        ml_result=MLResult(**{k: v for k, v in ml.items() if k in MLResult.model_fields}),
        health_score=health_score,
        risk_category=risk_category,
        followup_schedule=FollowupSchedule(**followup),
        emergency_flags=[EmergencyFlag(**f) for f in emergency_flags],
    )


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
        raise HTTPException(status_code=500, detail=f"Screening failed: {str(e)}")


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
