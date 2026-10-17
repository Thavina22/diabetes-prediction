"""ML inference — ensemble scoring, calibration, conformal bands and SHAP."""

from models.screening import ScreeningInput

from services import ml_model


def _input(**overrides) -> ScreeningInput:
    base = dict(
        glucose_mg_dl=126,
        sbp=130,
        dbp=85,
        height_cm=175,
        weight_kg=88,
        age=52,
        family_history=True,
    )
    base.update(overrides)
    return ScreeningInput(**base)


def test_predict_risk_output_contract():
    result = ml_model.predict_risk(_input())
    assert 0.0 <= result["score"] <= 1.0
    assert 0.0 <= result["raw_score"] <= 1.0
    assert result["calibrated"] is True
    assert result["model_version"] == "4.0"
    assert result["class"] in (0, 1)


def test_conformal_interval_brackets_score():
    result = ml_model.predict_risk(_input())
    assert result["uncertainty_low"] <= result["score"] <= result["uncertainty_high"]
    assert 0.0 <= result["uncertainty_low"] <= 1.0
    assert 0.0 <= result["uncertainty_high"] <= 1.0


def test_missing_pima_fields_are_imputed():
    # ScreeningInput carries no SkinThickness / Insulin, so both are imputed.
    result = ml_model.predict_risk(_input())
    assert "SkinThickness" in result["imputed"]
    assert "Insulin" in result["imputed"]


def test_threshold_override_is_honoured():
    result = ml_model.predict_risk(_input(), threshold=0.9)
    assert result["threshold"] == 0.9
    assert result["class"] == int(result["score"] >= 0.9)


def test_predict_risk_is_deterministic():
    assert ml_model.predict_risk(_input())["score"] == ml_model.predict_risk(_input())["score"]


def test_shap_values_cover_all_features():
    result = ml_model.predict_risk_with_shap(_input())
    shap_values = result.get("shap_values")
    assert shap_values is not None, "SHAP explainer unavailable"
    assert set(shap_values) == set(ml_model.PIMA_FEATURES)
    assert all(isinstance(v, float) for v in shap_values.values())
