"""Screening engine — assembles a full ScreeningResult from a ScreeningInput.

Shared by the main screening route, the stateless export routes, and the
third-party API-key screening endpoint so all three produce identical output.
"""

from datetime import datetime
from uuid import uuid4

from models.screening import (
    ScreeningInput,
    ScreeningResult,
    MLResult,
    FollowupSchedule,
    EmergencyFlag,
)
from services import clinical_rules as cr
from services.ml_model import predict_risk_with_shap

RISK_CATEGORY_MAP = {
    "Low": "low",
    "Medium": "medium",
    "High": "high",
    "Very High": "very_high",
}


def build_result(input_data: ScreeningInput, user_id: str) -> ScreeningResult:
    """Run the clinical + ML engines and assemble a ScreeningResult."""
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

    risk = cr.stratify_risk(glucose_rules, bp_rule, bmi_rule, lipid_rules, ml, input_data.age)
    risk_category = RISK_CATEGORY_MAP.get(risk["level"], "low")

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
