from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID


class ScreeningInput(BaseModel):
    glucose_mg_dl: Optional[float] = Field(None, ge=0, le=1000)
    glucose_type: Literal["fasting", "postprandial", "random", "hba1c", "ogtt"] = "fasting"
    sbp: Optional[int] = Field(None, ge=0, le=300)
    dbp: Optional[int] = Field(None, ge=0, le=200)
    height_cm: Optional[float] = Field(None, ge=30, le=300)
    weight_kg: Optional[float] = Field(None, ge=1, le=500)
    ldl_mg_dl: Optional[float] = Field(None, ge=0, le=500)
    hdl_mg_dl: Optional[float] = Field(None, ge=0, le=200)
    triglycerides_mg_dl: Optional[float] = Field(None, ge=0, le=2000)
    age: Optional[int] = Field(None, ge=0, le=150)
    sex: Optional[Literal["M", "F"]] = None
    family_history: bool = False
    medications: List[str] = Field(default_factory=list)
    comorbidities: List[str] = Field(default_factory=list)
    pregnancy_status: Optional[Literal["none", "gestational", "preexisting"]] = None
    unit_preference: Literal["mg_dL", "mmol_L"] = "mg_dL"

    @field_validator("dbp")
    @classmethod
    def dbp_less_than_sbp(cls, v, info):
        if v is not None and info.data.get("sbp") is not None and v >= info.data["sbp"]:
            raise ValueError("DBP must be less than SBP")
        return v


class ClinicalRule(BaseModel):
    metric: str
    measurement_type: str
    value: Optional[float | str] = None
    category: str
    severity: str
    status: str
    color: str = "green"
    interpretation: str
    is_diagnostic: bool = False
    requires_confirmation: bool = True
    red_flag: bool = False
    source: str = ""


class MLResult(BaseModel):
    score: float
    probability: Optional[float] = None
    risk_score: Optional[float] = None
    shap_values: Optional[dict] = None
    uncertainty_low: Optional[float] = None
    uncertainty_high: Optional[float] = None


class FollowupSchedule(BaseModel):
    when: str
    text: str
    color: str = "green"
    icon: str = "check"


class EmergencyFlag(BaseModel):
    type: str
    urgency: str
    color: str = "red"
    action: List[str] = Field(default_factory=list)


class SHAPExplanation(BaseModel):
    features: List[str]
    values: List[float]
    base_value: float


class ScreeningResult(BaseModel):
    id: UUID
    user_id: str
    created_at: datetime
    input: ScreeningInput
    glucose_rules: List[ClinicalRule]
    bp_rule: ClinicalRule
    bmi_rule: ClinicalRule
    lipid_rules: List[ClinicalRule]
    ml_result: MLResult
    health_score: int
    risk_category: Literal["low", "medium", "high", "very_high"]
    followup_schedule: FollowupSchedule
    emergency_flags: List[EmergencyFlag]
    shap_explanation: Optional[SHAPExplanation] = None


class ScreeningCreateResponse(BaseModel):
    id: UUID
    health_score: int
    risk_category: str
    message: str