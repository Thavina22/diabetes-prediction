"""Phase 4 model artifacts: soft-voting ensemble, sigmoid calibration, and
split-conformal prediction intervals.

Reuses the Phase 1 preprocessing (data/processed/*.npy are already scaled).

Outputs (in data/processed/):
  ensemble_model.joblib  soft-voting ensemble (LR + SVM + RF + GB + XGBoost)
  calibrator.joblib      CalibratedClassifierCV(sigmoid) wrapping the ensemble
  ensemble_meta.json     metrics, tuned threshold, conformal q, feature list

Run:  python scripts/train_ensemble.py
"""

import json
import os
import time

import joblib
import numpy as np
import xgboost as xgb
from sklearn.ensemble import (
    GradientBoostingClassifier,
    RandomForestClassifier,
    VotingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import cross_val_predict
from sklearn.svm import SVC

PROCESSED = os.path.join("data", "processed")
FEATURES = [
    "Pregnancies", "Glucose", "BloodPressure", "SkinThickness",
    "Insulin", "BMI", "DiabetesPedigreeFunction", "Age",
]
ALPHA = 0.10  # -> 90% prediction interval
SEED = 42


def load_data():
    def arr(name):
        return np.load(os.path.join(PROCESSED, name))

    return arr("X_train.npy"), arr("X_test.npy"), arr("y_train.npy"), arr("y_test.npy")


def make_ensemble(y_train) -> VotingClassifier:
    neg, pos = int((y_train == 0).sum()), int((y_train == 1).sum())
    return VotingClassifier(
        estimators=[
            ("lr", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)),
            ("svm", SVC(C=1, kernel="rbf", class_weight="balanced", probability=True, random_state=SEED)),
            ("rf", RandomForestClassifier(n_estimators=200, max_depth=10, class_weight="balanced", random_state=SEED)),
            ("gb", GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=3, random_state=SEED)),
            ("xgb", xgb.XGBClassifier(
                n_estimators=200, max_depth=3, learning_rate=0.05,
                subsample=0.8, colsample_bytree=0.8,
                scale_pos_weight=neg / max(pos, 1),
                eval_metric="logloss", random_state=SEED, n_jobs=-1,
            )),
        ],
        voting="soft",
        n_jobs=-1,
    )


def scores_at_threshold(proba, y_true, threshold):
    preds = (proba >= threshold).astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, preds)),
        "precision": float(precision_score(y_true, preds, zero_division=0)),
        "recall": float(recall_score(y_true, preds, zero_division=0)),
        "f1": float(f1_score(y_true, preds, zero_division=0)),
        "auc": float(roc_auc_score(y_true, proba)),
        "threshold": float(threshold),
    }


def tune_threshold(proba, y_true):
    best_t, best_f1 = 0.5, -1.0
    for t in np.arange(0.20, 0.81, 0.01):
        f1 = f1_score(y_true, (proba >= t).astype(int), zero_division=0)
        if f1 > best_f1:
            best_t, best_f1 = float(t), float(f1)
    return best_t, best_f1


def main():
    t0 = time.time()
    X_train, X_test, y_train, y_test = load_data()
    print(f"train={X_train.shape} test={X_test.shape}")

    # --- baseline (current shipped model: tuned Gradient Boosting) -----------
    gb = GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=3, random_state=SEED)
    gb.fit(X_train, y_train)
    gb_metrics = scores_at_threshold(gb.predict_proba(X_test)[:, 1], y_test, 0.5)
    print(f"GB baseline      F1={gb_metrics['f1']:.4f} AUC={gb_metrics['auc']:.4f}")

    # --- ensemble (soft voting) ---------------------------------------------
    ensemble = make_ensemble(y_train)
    ensemble.fit(X_train, y_train)

    # --- calibration (Platt scaling) ----------------------------------------
    # A compact 1-D logistic fit on out-of-fold ensemble probabilities maps the
    # raw score to a calibrated probability without shipping 5 refit ensembles.
    oof_ens = cross_val_predict(ensemble, X_train, y_train, cv=5, method="predict_proba")[:, 1]
    platt = LogisticRegression(max_iter=2000, random_state=SEED)
    platt.fit(oof_ens.reshape(-1, 1), y_train)

    oof_cal = platt.predict_proba(oof_ens.reshape(-1, 1))[:, 1]
    threshold, _ = tune_threshold(oof_cal, y_train)

    ens_proba_test = ensemble.predict_proba(X_test)[:, 1]
    cal_proba_test = platt.predict_proba(ens_proba_test.reshape(-1, 1))[:, 1]
    ens_metrics = scores_at_threshold(ens_proba_test, y_test, threshold)
    cal_metrics = scores_at_threshold(cal_proba_test, y_test, threshold)
    print(f"Ensemble         F1={ens_metrics['f1']:.4f} AUC={ens_metrics['auc']:.4f} (thr={threshold:.2f})")
    print(f"Calibrated       F1={cal_metrics['f1']:.4f} AUC={cal_metrics['auc']:.4f}")

    # --- split-conformal interval -------------------------------------------
    nonconformity = np.abs(y_train - oof_cal)
    q_hat = float(np.quantile(nonconformity, 1 - ALPHA))
    coverage = float(np.mean(np.abs(y_test - cal_proba_test) <= q_hat))
    print(f"Conformal q={q_hat:.4f} alpha={ALPHA} test coverage={coverage:.3f}")

    # --- persist ------------------------------------------------------------
    joblib.dump(ensemble, os.path.join(PROCESSED, "ensemble_model.joblib"))
    joblib.dump(platt, os.path.join(PROCESSED, "calibrator.joblib"))

    meta = {
        "version": "4.0",
        "features": FEATURES,
        "calibration": "platt_logistic",
        "threshold": threshold,
        "conformal_q": q_hat,
        "conformal_alpha": ALPHA,
        "conformal_coverage_test": coverage,
        "metrics": {
            "gradient_boosting": gb_metrics,
            "ensemble": ens_metrics,
            "calibrated": cal_metrics,
        },
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(os.path.join(PROCESSED, "ensemble_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"Saved artifacts to {PROCESSED} in {time.time() - t0:.1f}s")
    print(f"ensemble_f1_ge_gb={cal_metrics['f1'] >= gb_metrics['f1']}")


if __name__ == "__main__":
    main()
