from fastapi import APIRouter, Depends

from models.screening import ScreeningInput
from services import clinical_rules as cr
from services.ml_model import predict_risk
from auth.clerk import get_current_user_id

router = APIRouter()


@router.post("/health-score")
async def calculate_health_score_endpoint(
    input_data: ScreeningInput,
    user_id: str = Depends(get_current_user_id),
):
    """Calculate health score and risk level without storing."""
    screening = cr.run_clinical_screening(input_data)
    ml = predict_risk(input_data)

    health_score, deductions = cr.calculate_health_score(
        screening["glucose_rules"], screening["bp_rule"],
        screening["bmi_rule"], screening["lipid_rules"], ml,
    )
    risk = cr.stratify_risk(
        screening["glucose_rules"], screening["bp_rule"],
        screening["bmi_rule"], screening["lipid_rules"], ml, input_data.age,
    )

    return {
        "health_score": health_score,
        "risk_level": risk["level"],
        "risk_score": risk["score"],
        "deductions": deductions,
        "factors": risk["factors"],
    }
