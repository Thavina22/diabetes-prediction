"""Clinical rules engine — thresholds and safety logic (ADA 2026 / AHA-ACC 2025)."""

from models.screening import ScreeningInput

from services import clinical_rules as cr

# --- glucose ---------------------------------------------------------------


def test_fasting_glucose_bands():
    assert cr.classify_glucose(90, "fasting")["category"] == "normal"
    assert cr.classify_glucose(110, "fasting")["category"] == "prediabetes"
    assert cr.classify_glucose(140, "fasting")["category"] == "diabetes_range"


def test_hypoglycemia_flags():
    low = cr.classify_glucose(60, "fasting")
    assert low["severity"] == "low"

    severe = cr.classify_glucose(45, "fasting")
    assert severe["severity"] == "critical"
    assert severe["red_flag"] is True


def test_hba1c_bands():
    assert cr.classify_glucose(5.5, "hba1c")["category"] == "normal"
    assert cr.classify_glucose(6.0, "hba1c")["category"] == "prediabetes"
    assert cr.classify_glucose(7.0, "hba1c")["category"] == "diabetes_range"


def test_glucose_missing_and_invalid():
    assert cr.classify_glucose(None, "fasting")["category"] == "missing"
    assert cr.classify_glucose(5000, "fasting")["category"] == "invalid"
    assert cr.classify_glucose("abc", "fasting")["category"] == "invalid"


# --- blood pressure --------------------------------------------------------


def test_bp_categories():
    assert cr.classify_bp(118, 76)["severity"] == "normal"
    assert cr.classify_bp(132, 84)["severity"] == "stage1"
    assert cr.classify_bp(150, 95)["severity"] == "stage2"
    assert cr.classify_bp(185, 100)["severity"] == "severe"


def test_bp_or_logic_uses_worse_component():
    # SBP normal, DBP stage2 -> overall stage2.
    assert cr.classify_bp(110, 95)["severity"] == "stage2"


def test_bp_low_and_missing():
    assert cr.classify_bp(85, 55)["severity"] == "low"
    assert cr.classify_bp(None, None)["category"] == "missing"


def test_bp_emergency_with_symptoms():
    rule = cr.classify_bp(185, 100, symptoms=True)
    assert rule["severity"] == "emergency"


# --- BMI -------------------------------------------------------------------


def test_compute_bmi_categories():
    normal = cr.compute_bmi(70, 175)
    assert 18.5 <= normal["value"] < 25
    assert normal["category"] == "normal"

    assert cr.compute_bmi(95, 175)["category"] == "obese"
    assert cr.compute_bmi(50, 175)["category"] == "underweight"


def test_compute_bmi_missing_and_impossible():
    assert cr.compute_bmi(None, 175)["category"] == "missing"
    assert cr.compute_bmi(70, 10)["category"] == "invalid"


# --- lipids ----------------------------------------------------------------


def test_lipid_classifications_are_independent():
    rules = cr.classify_lipids(ldl=170, hdl=35, trig=260)
    severities = {r["metric"]: r["severity"] for r in rules}
    assert len(rules) == 3, "each provided lipid should yield its own rule"
    assert severities["ldl_c"] == "high"
    assert severities["hdl_c"] == "low"
    assert severities["triglycerides"] == "high"


def test_lipid_normal_values():
    severities = {r["metric"]: r["severity"] for r in cr.classify_lipids(ldl=90, hdl=60, trig=100)}
    assert set(severities.values()) == {"normal"}


# --- full screening --------------------------------------------------------


def test_run_clinical_screening_shape(normal_input: ScreeningInput):
    result = cr.run_clinical_screening(normal_input)
    assert set(result) >= {
        "glucose_rules",
        "bp_rule",
        "bmi_rule",
        "lipid_rules",
        "aggregate",
    }
    assert result["aggregate"]["overall"]["severity"] in {"normal", "low", "elevated", "high"}


def test_emergency_protocols_triggered_by_very_high_glucose():
    rules = [cr.classify_glucose(450, "fasting")]
    flags = cr.emergency_protocols(rules, cr.classify_bp(120, 80))
    assert flags, "expected an emergency flag for glucose 450 mg/dL"
