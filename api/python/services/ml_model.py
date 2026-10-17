"""ML inference service for the PIMA diabetes screening model (Phase 4).

Pipeline
  raw ScreeningInput
    -> PIMA feature vector (with median imputation)
    -> StandardScaler            (MUST match training)
    -> soft-voting ensemble      (LR + SVM + RF + GB + XGBoost)
    -> Platt sigmoid calibration -> calibrated probability
    -> split-conformal interval  -> uncertainty_low/high (90%)

The Gradient Boosting model is retained purely as the SHAP explainer (tree
attributions are cheap and stable).

This is a baseline screening model trained on the PIMA Indians Diabetes
Database (768 records, 8 features). It is NOT clinically validated and is used
ONLY to produce a separate "model-estimated risk score" — never a diagnosis.

Artifacts (data/processed/): ensemble_model.joblib, calibrator.joblib,
scaler.joblib, best_model.joblib, ensemble_meta.json. Every stage degrades
gracefully if its artifact is missing.
"""

import json
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
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

_model = None          # Gradient Boosting — SHAP explainer only
_ensemble = None       # soft-voting ensemble — scoring
_calibrator = None     # Platt sigmoid
_scaler = None
_explainer = None
_meta: Optional[dict] = None

_MISSING = object()


def _artifact_dir() -> Optional[Path]:
    settings = get_settings()
    candidates = [
        Path(settings.MODEL_PATH),
        Path(__file__).resolve().parents[3] / "data" / "processed" / "best_model.joblib",
        Path("data/processed/best_model.joblib"),
        Path("../data/processed/best_model.joblib"),
    ]
    for c in candidates:
        if c.is_file():
            return c.parent
    return None


def _load_artifact(filename: str):
    """Load a joblib artifact from the model directory, or return None."""
    directory = _artifact_dir()
    if directory is None:
        return None
    path = directory / filename
    if not path.is_file():
        return None
    try:
        return joblib.load(path)
    except Exception:
        return None


def get_model():
    """Lazy-load the Gradient Boosting model (SHAP explainer)."""
    global _model
    if _model is None:
        _model = _load_artifact("best_model.joblib")
        if _model is None:
            raise FileNotFoundError("ML model file not found (best_model.joblib)")
    return _model


def _get_ensemble():
    global _ensemble
    if _ensemble is None:
        _ensemble = _load_artifact("ensemble_model.joblib") or _MISSING
    return None if _ensemble is _MISSING else _ensemble


def _get_calibrator():
    global _calibrator
    if _calibrator is None:
        _calibrator = _load_artifact("calibrator.joblib") or _MISSING
    return None if _calibrator is _MISSING else _calibrator


def _get_scaler():
    global _scaler
    if _scaler is None:
        _scaler = _load_artifact("scaler.joblib") or _MISSING
    return None if _scaler is _MISSING else _scaler


def _get_meta() -> dict:
    global _meta
    if _meta is None:
        directory = _artifact_dir()
        meta = {}
        if directory is not None:
            path = directory / "ensemble_meta.json"
            if path.is_file():
                try:
                    meta = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    meta = {}
        _meta = meta
    return _meta


def _get_explainer():
    """Lazy-load a SHAP TreeExplainer for the GB model. Returns None if unavailable."""
    global _explainer
    if _explainer is None:
        try:
            import shap

            _explainer = shap.TreeExplainer(get_model())
        except Exception:
            _explainer = False
    return _explainer or None


def _to_pima_vector(input_data: Any) -> dict:
    """Map a ScreeningInput-like object to PIMA feature values (raw units)."""
    bmi = None
    if getattr(input_data, "weight_kg", None) and getattr(input_data, "height_cm", None):
        h_m = input_data.height_cm / 100.0
        bmi = input_data.weight_kg / (h_m ** 2)

    return {
        "Pregnancies": 1.0 if getattr(input_data, "pregnancy_status", None) in ("gestational", "preexisting") else 0.0,
        "Glucose": input_data.glucose_mg_dl,
        "BloodPressure": input_data.dbp,
        "SkinThickness": None,
        "Insulin": None,
        "BMI": bmi,
        "DiabetesPedigreeFunction": 0.5 if getattr(input_data, "family_history", False) else 0.3,
        "Age": input_data.age,
    }


def _prepare(input_data: Any) -> tuple[np.ndarray, list[str], dict]:
    """Impute missing values, then scale to match the training distribution."""
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

    x = np.array(feats, dtype=float).reshape(1, -1)
    scaler = _get_scaler()
    if scaler is not None:
        try:
            # Pass a labelled frame so the scaler (fit with feature names) is happy.
            x = scaler.transform(pd.DataFrame(x, columns=PIMA_FEATURES))
        except Exception:
            pass  # fall back to raw features rather than failing inference
    return x, imputed, raw


def _positive_proba(model, x: np.ndarray) -> float:
    proba = np.asarray(model.predict_proba(x)[0]).reshape(-1)
    return float(proba[-1])


def predict_risk(input_data: Any, threshold: Optional[float] = None) -> dict:
    """Return the model risk score, calibrated probability, and conformal interval."""
    meta = _get_meta()
    if threshold is None:
        threshold = float(meta.get("threshold", 0.5))

    x, imputed, raw = _prepare(input_data)
    scorer = _get_ensemble() or get_model()

    try:
        raw_score = _positive_proba(scorer, x)
    except Exception as e:
        return {
            "score": 0.0, "class": 0, "imputed": imputed, "error": str(e),
            "threshold": threshold,
        }

    score = raw_score
    calibrated = False
    calibrator = _get_calibrator()
    if calibrator is not None:
        try:
            score = _positive_proba(calibrator, np.array([[raw_score]], dtype=float))
            calibrated = True
        except Exception:
            score = raw_score

    q = meta.get("conformal_q")
    low = max(0.0, score - float(q)) if q is not None else None
    high = min(1.0, score + float(q)) if q is not None else None

    return {
        "score": score,
        "probability": score,
        "risk_score": score,
        "raw_score": raw_score,
        "calibrated": calibrated,
        "class": int(score >= threshold),
        "threshold": threshold,
        "uncertainty_low": low,
        "uncertainty_high": high,
        "model_version": meta.get("version", "legacy"),
        "imputed": imputed,
    }


def predict_risk_with_shap(input_data: Any, threshold: Optional[float] = None) -> dict:
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
        result["shap_values"] = {feat: float(val) for feat, val in zip(PIMA_FEATURES, values)}
        base = getattr(explainer, "expected_value", 0.0)
        if isinstance(base, (list, np.ndarray)):
            base = base[1] if len(base) > 1 else base[0]
        result["shap_base_value"] = float(base)
    except Exception:
        pass

    return result
