from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from models.screening import ScreeningInput
from services.clinical_rules import run_clinical_screening
from services.ml_model import predict_risk
from services.pdf_generator import generate_clinical_pdf
from auth.clerk import get_current_user_id

router = APIRouter()


@router.post("/export/pdf")
async def export_pdf(
    input_data: ScreeningInput,
    user_id: str = Depends(get_current_user_id),
):
    """Generate clinical PDF for a screening input (without storing)."""
    try:
        clinical_result = run_clinical_screening(input_data)
        ml_result = predict_risk(input_data)

        from services.clinical_rules import calculate_health_score
        health_score, deductions = calculate_health_score(
            clinical_result["glucose_rules"],
            clinical_result["bp_rule"],
            clinical_result["bmi_rule"],
            clinical_result["lipid_rules"],
            ml_result,
        )

        # Build a minimal result object for PDF
        from datetime import datetime
        from uuid import UUID
        from models.screening import ScreeningResult, MLResult, ClinicalRule, FollowupSchedule, EmergencyFlag

        result = ScreeningResult(
            id=UUID(int=0),
            user_id=user_id,
            created_at=datetime.utcnow(),
            input=input_data,
            glucose_rules=clinical_result["glucose_rules"],
            bp_rule=clinical_result["bp_rule"],
            bmi_rule=clinical_result["bmi_rule"],
            lipid_rules=clinical_result["lipid_rules"],
            ml_result=MLResult(**ml_result),
            health_score=health_score,
            risk_category="low",  # Will be computed
            followup_schedule=FollowupSchedule(timeframe="1 year", reason="Routine", tests=[]),
            emergency_flags=[],
        )

        pdf_bytes = generate_clinical_pdf(result)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=diabetes_screening_report.pdf"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")