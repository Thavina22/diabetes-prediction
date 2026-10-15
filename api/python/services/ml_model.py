"""ML inference service for the PIMA Gradient Boosting screening model.

The model is a baseline screening model trained on the PIMA Indians Diabetes
Database (768 records, 8 features). It is NOT clinically validated and its
recall is weak (~61%). It is used ONLY to produce a separate "model-estimated
risk score" — never as the source of truth, and never as a diagnosis.
"""

import os
from pathlib import Path
from typing import Any, Optional

import numpy as np
import joblib

from config import get_settings

# Fixed PIMA schema — must match training exactly.
PIMA_FEATURES = [
    "Pregnancies", "Glucose", "BloodPressure", "SkinThickness",
    "Insulin", "BMI", "DiabetesPedigreeFunction", "Age",
]

# In PIMA, 0 for these clinical fields actually means "missing".
_ZERO_MEANS_MISSING = {"Glucose", "BloodPressure", "SkinThickness", "Insulin", "BMI", "Age"}

# Dataset medians used for imputation (PIMA training medians).
_MEDIANS = {
    "Pregnancies": 3.0,
    "Glucose": 117.0,
    "BloodPressure": 72.0,
    "SkinThickness": 23.0,
    "Insulin": 30.5,
    "BMI": 32.0,
    "DiabetesPedigreeFunction": 0.3725,
    "Age": 29.0,
}

_model = None
_explainer = None


def _resolve_model_path() -> Optional[Path]:
    settings = get_settings()
    candidates = [
        Path(settings.MODEL_PATH),
        Path(__file__).resolve().parents[3] / "data" / "processed" / "best_model.joblib",
        Path("data/processed/best_model.joblib"),
        Path("../data/processed/best_model.joblib"),
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def get_model():
    """Lazy-load the joblib model (module-level singleton)."""
    global _model
    if _model is None:
        path = _resolve_model_path()
        if path is None:
            raise FileNotFoundError("ML model file not found (best_model.joblib)")
        _model = joblib.load(path)
    return _model


def _get_explainer():
    """Lazy-load a SHAP TreeExplainer. Returns None if unavailable."""
    global _explainer
    if _explainer is None:
        try:
            import shap

            model = get_model()
            _explainer = shap.TreeExplainer(model)
        except Exception:
            _explainer = False
    return _explainer or None


def _to_pima_vector(input_data: Any) -> tuple[list[float], list[str]]:
    """Map a ScreeningInput-like object to a PIMA feature vector."""
    bmi = None
    if input_data.weight_kg and input_data.height_cm:
        h_m = input_data.height_cm / 100.0
        bmi = input_data.weight_kg / (h_m ** 2)

    raw = {
        "Pregnancies": 1.0 if getattr(input_data, "pregnancy_status", None) in ("gestational", "preexisting") else 0.0,
        "Glucose": input_data.glucose_mg_dl,
        "BloodPressure": input_data.dbp,
        "SkinThickness": None,
        "Insulin": None,
        "BMI": bmi,
        "DiabetesPedigreeFunction": 0.5 if getattr(input_data, "family_history", False) else 0.3,
        "Age": input_data.age,
    }
    return raw


def _prepare(input_data: Any) -> tuple[np.ndarray, list[str], dict]:
    raw = _to_pima_vector(input_data)
    feats, imputed = [], []
    for f in PIMA_FEATURES:
        v = raw.get(f)
        is_missing = v is None or (
            isinstance(v, (int, float)) and f in _ZERO_MEANS_MISSING and float(v) == 0.0
        )
        if is_missing:
            feats.append(float(_MEDIANS.get(f, 0.0)))
            imputed.append(f)
        else:
            feats.append(float(v))
    return np.array(feats, dtype=float).reshape(1, -1), imputed, raw


def _probability(model, x: np.ndarray) -> float:
    proba = model.predict_proba(x)[0]
    if len(proba) == 1:
        return float(proba[0])
    return float(proba[1])


def predict_risk(input_data: Any, threshold: float = 0.5) -> dict:
    """Return the model risk score for a ScreeningInput."""
    model = get_model()
    x, imputed, raw = _prepare(input_data)
    try:
        score = _probability(model, x)
    except Exception as e:
        return {"score": 0.0, "class": 0, "imputed": imputed, "error": str(e)}

    return {
        "score": score,
        "probability": score,
        "risk_score": score,
        "class": int(score >= threshold),
        "threshold": threshold,
        "imputed": imputed,
    }


def predict_risk_with_shap(input_data: Any, threshold: float = 0.5) -> dict:
    """Return the model risk score plus SHAP feature attributions."""
    result = predict_risk(input_data, threshold)

    explainer = _get_explainer()
    if explainer is None:
        return result

    try:
        x, _, _ = _prepare(input_data)
        shap_values = explainer.shap_values(x)
        if isinstance(shap_values, list):
            shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
        values = np.array(shap_values).reshape(-1)
        result["shap_values"] = {
            feat: float(val) for feat, val in zip(PIMA_FEATURES, values)
        }
        base = getattr(explainer, "expected_value", 0.0)
        if isinstance(base, (list, np.ndarray)):
            base = base[1] if len(base) > 1 else base[0]
        result["shap_base_value"] = float(base)
    except Exception:
        pass

    return result
