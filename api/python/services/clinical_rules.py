"""Deterministic clinical rule engine for the diabetes-risk screener.

Ported from the original Streamlit app (`src/clinical_rules.py`) into a pure-Python
service with no Streamlit dependencies. Every classification is a pure function of
its numeric inputs plus a named measurement type.

Sources
-------
* ADA Standards of Care in Diabetes 2026
* AHA/ACC 2025 hypertension guideline
* ACOG 2024 (gestational)
* WHO / NCEP ATP III lipid categories
"""

from typing import Any, Optional


SEVERITY_ORDER = [
    "normal", "low", "elevated", "prediabetes", "stage1", "high",
    "needs_confirmation", "stage2", "very_high", "diabetes_range", "severe",
    "critical", "emergency",
]
_SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITY_ORDER)}

COLOR = {
    "normal": "green", "low": "orange", "elevated": "yellow", "prediabetes": "yellow",
    "stage1": "orange", "high": "orange", "needs_confirmation": "orange", "stage2": "red",
    "very_high": "red", "diabetes_range": "red", "severe": "red",
    "critical": "red", "emergency": "red",
}


def _severity_rank(sev: str) -> int:
    return _SEVERITY_RANK.get(sev, 0)


def severity_rank(sev: str) -> int:
    """Public helper: numeric rank of a severity label (higher = more urgent)."""
    return _severity_rank(sev)


def _rule(metric, mtype, value, category, severity, status, interpretation,
          is_diagnostic=False, requires_confirmation=True, red_flag=False,
          source=""):
    return {
        "metric": metric,
        "measurement_type": mtype,
        "value": value,
        "category": category,
        "severity": severity,
        "status": status,
        "color": COLOR.get(severity, "green"),
        "interpretation": interpretation,
        "is_diagnostic": is_diagnostic,
        "requires_confirmation": requires_confirmation,
        "red_flag": red_flag,
        "source": source,
    }


def _missing(metric, mtype):
    return _rule(metric, mtype, None, "missing", "normal",
                 "Not provided", "No value was provided.",
                 requires_confirmation=True)


def _invalid(metric, mtype, note="Value could not be interpreted."):
    return _rule(metric, mtype, None, "invalid", "normal", "Invalid", note,
                 requires_confirmation=True)


# ---------------------------------------------------------------------------
# Glucose
# ---------------------------------------------------------------------------
_GLUCOSE_SRC = "ADA Standards of Care in Diabetes 2026"


def _glucose_high_layer(v):
    if v >= 400:
        return ("emergency", "Emergency-level concern",
                "Glucose is extremely high — this is an emergency-level reading "
                "and urgent medical assessment is needed.")
    if v >= 300:
        return ("critical", "Critical / high-risk",
                "Severe hyperglycaemia — high-risk range; seek urgent care.")
    if v > 250:
        return ("very_high", "Very high", "Markedly high glucose.")
    return None


def classify_glucose(value, measurement_type):
    """Classify a glucose value by measurement type.

    measurement_type: 'fasting' | 'hba1c' | 'ogtt2h' | 'random' | 'postmeal2h'
    """
    if value is None:
        return _missing("glucose", measurement_type)
    try:
        v = float(value)
    except (TypeError, ValueError):
        return _invalid("glucose", measurement_type)
    if v < 0 or v > 2000:
        return _invalid("glucose", measurement_type, "Glucose out of plausible range.")

    mt = str(measurement_type).lower()
    if mt == "hba1c":
        return _hba1c(v)
    if mt == "fasting":
        return _fasting(v)
    if mt == "ogtt2h":
        return _ogtt(v)
    if mt in ("random", "postmeal2h"):
        return _random_or_postmeal(v, mt)
    return _invalid("glucose", measurement_type, "Unknown glucose measurement type.")


def _fasting(v):
    if v < 54:
        note = ("Level 2 hypoglycaemia (severe low). <40 mg/dL is an "
                "emergency-level low reading." if v < 40 else
                "Level 2 hypoglycaemia (severe low).")
        return _rule("glucose", "fasting", v, "hypoglycemia", "critical",
                     "Level 2 hypoglycemia (severe low)", note,
                     is_diagnostic=False, requires_confirmation=True,
                     red_flag=True, source=_GLUCOSE_SRC)
    if v < 70:
        return _rule("glucose", "fasting", v, "hypoglycemia", "low",
                     "Level 1 hypoglycemia (low)",
                     "Level 1 hypoglycaemia (low). Treat symptoms; consider "
                     "fast-acting carbohydrate if conscious.",
                     source=_GLUCOSE_SRC)
    if v <= 99:
        return _rule("glucose", "fasting", v, "normal", "normal",
                     "Normal fasting range",
                     "Fasting glucose is within the normal range (70-99 mg/dL).",
                     requires_confirmation=False, source=_GLUCOSE_SRC)
    if v <= 125:
        return _rule("glucose", "fasting", v, "prediabetes", "prediabetes",
                     "Prediabetes range (impaired fasting glucose)",
                     "Fasting 100-125 mg/dL is the ADA prediabetes range "
                     "(impaired fasting glucose).", source=_GLUCOSE_SRC)
    base = _rule("glucose", "fasting", v, "diabetes_range", "diabetes_range",
                 "Diabetes-range (fasting)",
                 "Fasting >=126 mg/dL is in the diabetes range per ADA/WHO. "
                 "Confirmation with a repeat test or another criterion is needed.",
                 is_diagnostic=True, source=_GLUCOSE_SRC)
    return _apply_high_layer(base, v)


def _hba1c(v):
    if v < 5.7:
        return _rule("glucose", "hba1c", v, "normal", "normal",
                     "Normal HbA1c",
                     "HbA1c below 5.7% is normal.", requires_confirmation=False,
                     source=_GLUCOSE_SRC)
    if v < 6.5:
        return _rule("glucose", "hba1c", v, "prediabetes", "prediabetes",
                     "Prediabetes-range HbA1c",
                     "HbA1c 5.7-6.4% is the prediabetes range.",
                     source=_GLUCOSE_SRC)
    return _rule("glucose", "hba1c", v, "diabetes_range", "diabetes_range",
                 "Diabetes-range HbA1c",
                 "HbA1c >=6.5% is in the diabetes range per ADA.",
                 is_diagnostic=True, source=_GLUCOSE_SRC)


def _ogtt(v):
    if v < 140:
        return _rule("glucose", "ogtt2h", v, "normal", "normal",
                     "Normal 2-h OGTT",
                     "2-hour 75-g OGTT below 140 mg/dL is normal.",
                     requires_confirmation=False, source=_GLUCOSE_SRC)
    if v < 200:
        return _rule("glucose", "ogtt2h", v, "prediabetes", "prediabetes",
                     "Prediabetes range (IGT)",
                     "2-hour 75-g OGTT 140-199 mg/dL is impaired glucose "
                     "tolerance (prediabetes).", source=_GLUCOSE_SRC)
    base = _rule("glucose", "ogtt2h", v, "diabetes_range", "diabetes_range",
                 "Diabetes-range 2-h OGTT",
                 "2-hour 75-g OGTT >=200 mg/dL is in the diabetes range per ADA.",
                 is_diagnostic=True, source=_GLUCOSE_SRC)
    return _apply_high_layer(base, v)


def _random_or_postmeal(v, mt):
    label = "Random glucose" if mt == "random" else "2-hour post-meal glucose"
    mt_name = "random" if mt == "random" else "postmeal2h"
    if v >= 200:
        interp = (f"{label} >=200 mg/dL is in the diabetes range, but diagnosis "
                  "requires confirmation (random needs classic symptoms; an "
                  "ordinary post-meal reading is NOT a standardised 75-g OGTT).")
        base = _rule("glucose", mt_name, v, "diabetes_range", "diabetes_range",
                     "Diabetes-range", interp, is_diagnostic=False,
                     source=_GLUCOSE_SRC)
        return _apply_high_layer(base, v)
    if v >= 140:
        return _rule("glucose", mt_name, v, "needs_confirmation", "needs_confirmation",
                     "Elevated — needs confirmation",
                     f"{label} 140-199 mg/dL is elevated; a standardised 75-g "
                     "OGTT is needed for a proper interpretation.",
                     source=_GLUCOSE_SRC)
    return _rule("glucose", mt_name, v, "normal", "normal",
                 "Within screening normal",
                 f"{label} below 140 mg/dL is within the screening normal range "
                 "(interpretation of an ordinary meal differs from an OGTT).",
                 requires_confirmation=False, source=_GLUCOSE_SRC)


def _apply_high_layer(rule, v):
    layer = _glucose_high_layer(v)
    if layer is None:
        return rule
    sev, status, interp = layer
    if _severity_rank(sev) > _severity_rank(rule["severity"]):
        rule = dict(rule)
        rule["severity"] = sev
        rule["status"] = status
        rule["interpretation"] = interp
        rule["color"] = COLOR.get(sev, "red")
        rule["red_flag"] = True
    return rule


# ---------------------------------------------------------------------------
# Blood pressure
# ---------------------------------------------------------------------------
_BP_SRC = "AHA/ACC 2025 hypertension guideline"


def _bp_category(sbp, dbp):
    if sbp is not None:
        if sbp > 180:
            return ("severe", "Severe hypertension",
                    "Systolic >180 mmHg is severe hypertension.")
        if sbp >= 140:
            return ("stage2", "Stage 2 hypertension",
                    "Systolic >=140 mmHg is Stage 2 hypertension.")
        if sbp >= 130:
            return ("stage1", "Stage 1 hypertension",
                    "Systolic 130-139 mmHg is Stage 1 hypertension.")
        if sbp >= 120:
            return ("elevated", "Elevated",
                    "Systolic 120-129 mmHg is Elevated.")
        if sbp >= 90:
            return ("normal", "Normal", "Systolic is in the normal range.")
        if sbp < 90:
            return ("low", "Low blood pressure",
                    "Systolic <90 mmHg is low blood pressure (hypotension screening).")
    if dbp is not None:
        if dbp > 120:
            return ("severe", "Severe hypertension",
                    "Diastolic >120 mmHg is severe hypertension.")
        if dbp >= 90:
            return ("stage2", "Stage 2 hypertension",
                    "Diastolic >=90 mmHg is Stage 2 hypertension.")
        if dbp >= 80:
            return ("stage1", "Stage 1 hypertension",
                    "Diastolic 80-89 mmHg is Stage 1 hypertension.")
        if dbp < 60:
            return ("low", "Low blood pressure",
                    "Diastolic <60 mmHg is low blood pressure.")
        return ("normal", "Normal", "Diastolic is in the normal range.")
    return ("normal", "Normal", "No blood-pressure value provided.")


def classify_bp(systolic=None, diastolic=None, symptoms=None):
    """Classify blood pressure using INDEPENDENT SBP and DBP, then OR-logic."""
    if systolic is None and diastolic is None:
        return _missing("blood_pressure", "bp")
    try:
        sbp = float(systolic) if systolic is not None else None
        dbp = float(diastolic) if diastolic is not None else None
    except (TypeError, ValueError):
        return _invalid("blood_pressure", "bp")
    if (sbp is not None and (sbp < 0 or sbp > 400)) or \
       (dbp is not None and (dbp < 0 or dbp > 400)):
        return _invalid("blood_pressure", "bp", "BP out of plausible range.")

    low = (sbp is not None and sbp < 90) or (dbp is not None and dbp < 60)

    s_res = _bp_category(sbp, None) if sbp is not None else None
    d_res = _bp_category(None, dbp) if dbp is not None else None

    candidates = [r for r in (s_res, d_res) if r]
    if not candidates:
        return _rule("blood_pressure", "bp", None, "normal", "normal",
                     "Normal", "Blood pressure within range.",
                     requires_confirmation=False, source=_BP_SRC)
    best = max(candidates, key=lambda r: _severity_rank(r[0]))
    severity, status, interp = best

    if low and severity in ("normal", "elevated"):
        severity, status, interp = (
            "low", "Low blood pressure",
            "One BP component is below the normal low limit "
            f"(SBP {sbp}, DBP {dbp}). Low BP screening flag.")
    red_flag = severity in ("severe", "critical", "emergency")
    rule = _rule("blood_pressure", "bp",
                 f"{sbp}/{dbp}" if (sbp is not None and dbp is not None) else (sbp or dbp),
                 "abnormal" if severity != "normal" else "normal",
                 severity, status, interp,
                 requires_confirmation=(severity in ("stage1", "stage2", "severe")),
                 red_flag=red_flag, source=_BP_SRC)
    if severity == "severe" and symptoms:
        rule = dict(rule)
        rule["severity"] = "emergency"
        rule["status"] = "Hypertensive emergency (with symptoms)"
        rule["interpretation"] = (
            "Very high BP WITH concerning symptoms (e.g. chest pain, breathlessness, "
            "neurological signs, altered mental status) is a hypertensive emergency "
            "— seek emergency care.")
        rule["color"] = COLOR["emergency"]
    return rule


# ---------------------------------------------------------------------------
# BMI
# ---------------------------------------------------------------------------
def compute_bmi(weight_kg=None, height_cm=None):
    """BMI = weight_kg / (height_m ** 2). Adult categories only."""
    if weight_kg is None or height_cm is None:
        return _missing("bmi", "bmi")
    try:
        w = float(weight_kg)
        h_cm = float(height_cm)
    except (TypeError, ValueError):
        return _invalid("bmi", "bmi")
    if w <= 0 or h_cm <= 0 or h_cm < 50 or h_cm > 260 or w > 400:
        return _invalid("bmi", "bmi", "Impossible weight or height.")
    h_m = h_cm / 100.0
    bmi = w / (h_m ** 2)
    if bmi < 18.5:
        cat, sev, status = "underweight", "low", "Underweight"
    elif bmi < 25:
        cat, sev, status = "normal", "normal", "Normal weight"
    elif bmi < 30:
        cat, sev, status = "overweight", "elevated", "Overweight"
    else:
        cat, sev, status = "obese", "high", "Obese"
    return _rule("bmi", "bmi", round(bmi, 1), cat, sev, status,
                 f"BMI {bmi:.1f} — adult category: {status}. BMI is a risk factor, "
                 "not a diagnostic test.", requires_confirmation=False,
                 source="WHO / ADA adult BMI categories")


# ---------------------------------------------------------------------------
# Lipids
# ---------------------------------------------------------------------------
_LIPID_SRC = "AHA / NCEP ATP III lipid categories"


def classify_lipids(total=None, ldl=None, hdl=None, trig=None, nonhdl=None):
    """Return a list of structured lipid classifications (kept independent)."""
    out = []
    if ldl is not None:
        try:
            ldl = float(ldl)
        except (TypeError, ValueError):
            ldl = None
        if ldl is not None:
            sev = "high" if ldl >= 160 else ("elevated" if ldl >= 130 else "normal")
            out.append(_rule("ldl_c", "lipid", ldl, "ldl", sev,
                             f"LDL-C {sev}", f"LDL-C {ldl:.0f} mg/dL.",
                             source=_LIPID_SRC))
    if hdl is not None:
        try:
            hdl = float(hdl)
        except (TypeError, ValueError):
            hdl = None
        if hdl is not None:
            sev = "low" if hdl < 40 else "normal"
            out.append(_rule("hdl_c", "lipid", hdl, "hdl", sev,
                             f"HDL-C {sev}", f"HDL-C {hdl:.0f} mg/dL "
                             f"({'low' if sev == 'low' else 'normal'}).",
                             source=_LIPID_SRC))
    if trig is not None:
        try:
            trig = float(trig)
        except (TypeError, ValueError):
            trig = None
        if trig is not None:
            sev = "high" if trig >= 200 else ("elevated" if trig >= 150 else "normal")
            out.append(_rule("triglycerides", "lipid", trig, "trig", sev,
                             f"Triglycerides {sev}", f"Triglycerides {trig:.0f} mg/dL.",
                             source=_LIPID_SRC))
    if nonhdl is not None:
        try:
            nonhdl = float(nonhdl)
        except (TypeError, ValueError):
            nonhdl = None
        if nonhdl is not None:
            sev = "high" if nonhdl >= 190 else "normal"
            out.append(_rule("non_hdl", "lipid", nonhdl, "nonhdl", sev,
                             f"Non-HDL-C {sev}", f"Non-HDL-C {nonhdl:.0f} mg/dL.",
                             source=_LIPID_SRC))
    if total is not None:
        try:
            total = float(total)
        except (TypeError, ValueError):
            total = None
        if total is not None:
            sev = "high" if total >= 240 else ("elevated" if total >= 200 else "normal")
            out.append(_rule("total_cholesterol", "lipid", total, "chol", sev,
                             f"Total cholesterol {sev}", f"Total cholesterol "
                             f"{total:.0f} mg/dL.", source=_LIPID_SRC))
    return out


# ---------------------------------------------------------------------------
# Red-flag engine
# ---------------------------------------------------------------------------
def red_flag_engine(glucose_rules=None, bp_rule=None, symptoms=None):
    """Identify urgent safety concerns. Symptoms make a high number an emergency."""
    flags = []
    symptoms = [s for s in (symptoms or []) if s]
    for r in (glucose_rules or []):
        if r.get("red_flag"):
            flags.append({
                "area": "glucose", "severity": r["severity"],
                "message": r["interpretation"],
                "symptomatic": bool(symptoms),
            })
    if bp_rule and bp_rule.get("red_flag"):
        msg = bp_rule["interpretation"]
        if bp_rule["severity"] == "emergency":
            msg = ("VERY HIGH BLOOD PRESSURE WITH CONCERNING SYMPTOMS — "
                   "hypertensive emergency. Seek emergency care now.")
        flags.append({
            "area": "blood_pressure", "severity": bp_rule["severity"],
            "message": msg, "symptomatic": bp_rule["severity"] == "emergency",
        })
    return flags


# ---------------------------------------------------------------------------
# Evidence aggregation
# ---------------------------------------------------------------------------
def aggregate_evidence(glucose_rules=None, bp_rule=None, bmi_rule=None,
                       lipid_rules=None, findrisc=None, ml=None):
    """Build the structured screening summary with severity-priority ordering."""
    components = []
    for r in (glucose_rules or []):
        components.append(("glucose", r))
    if bp_rule:
        components.append(("blood_pressure", bp_rule))
    if bmi_rule:
        components.append(("bmi", bmi_rule))
    for r in (lipid_rules or []):
        components.append(("lipid", r))

    rank = max((_severity_rank(r["severity"]) for _, r in components), default=0)
    overall_sev = SEVERITY_ORDER[rank] if rank < len(SEVERITY_ORDER) else "emergency"
    status_map = {
        "normal": "Normal / low risk", "low": "Low / monitor",
        "elevated": "Elevated risk", "prediabetes": "Elevated risk",
        "stage1": "Elevated risk", "high": "High risk",
        "needs_confirmation": "Needs confirmation",
        "stage2": "High risk", "very_high": "High risk",
        "diabetes_range": "Diabetes-range finding",
        "severe": "Severe abnormality", "critical": "Critical abnormality",
        "emergency": "EMERGENCY / RED FLAG",
    }
    flags = red_flag_engine(glucose_rules, bp_rule)
    return {
        "components": components,
        "overall": {
            "screening_status": status_map.get(overall_sev, "Elevated risk"),
            "severity": overall_sev,
            "requires_confirmation": any(
                r.get("requires_confirmation") for _, r in components),
        },
        "red_flags": flags,
        "findrisc": findrisc,
        "ml": ml,
    }


# ---------------------------------------------------------------------------
# A1C <-> average glucose
# ---------------------------------------------------------------------------
def a1c_to_avg_glucose(a1c_percent):
    """eAG = 28.7 x A1C - 46.7 (ADA/Nathan et al. 2008)."""
    try:
        a1c = float(a1c_percent)
    except (TypeError, ValueError):
        return None
    if a1c < 3.0 or a1c > 20.0:
        return None
    return round(28.7 * a1c - 46.7, 1)


def avg_glucose_to_a1c(eag_mg_dl):
    try:
        eag = float(eag_mg_dl)
    except (TypeError, ValueError):
        return None
    if eag < 40 or eag > 500:
        return None
    return round((eag + 46.7) / 28.7, 1)


def a1c_converter(a1c=None, eag=None):
    if a1c is not None:
        result = a1c_to_avg_glucose(a1c)
        return {"a1c": a1c, "avg_glucose_mg_dl": result,
                "interpretation": f"A1C {a1c}% ≈ {result} mg/dL average" if result else "Invalid input"}
    if eag is not None:
        result = avg_glucose_to_a1c(eag)
        return {"a1c": result, "avg_glucose_mg_dl": eag,
                "interpretation": f"{eag} mg/dL average ≈ A1C {result}%" if result else "Invalid input"}
    return None


# ---------------------------------------------------------------------------
# Risk stratification
# ---------------------------------------------------------------------------
def stratify_risk(glucose_rules, bp_rule, bmi_rule, lipid_rules, ml=None, age=None):
    """Classify overall risk into Low / Medium / High / Very High."""
    score = 0
    factors = []

    if glucose_rules:
        worst = max(glucose_rules, key=lambda r: severity_rank(r["severity"]))
        g_scores = {
            "normal": 0, "low": 5, "elevated": 10, "prediabetes": 20,
            "stage1": 25, "high": 30, "stage2": 35, "very_high": 40,
            "diabetes_range": 40, "severe": 40, "critical": 40, "emergency": 40,
        }
        s = g_scores.get(worst["severity"], 0)
        score += s
        if s >= 20:
            factors.append(f"Glucose ({worst['status']})")

    if bp_rule:
        bp_scores = {
            "normal": 0, "elevated": 5, "stage1": 10, "stage2": 20,
            "severe": 30, "emergency": 30, "low": 5,
        }
        s = bp_scores.get(bp_rule["severity"], 0)
        score += s
        if s >= 10:
            factors.append(f"Blood pressure ({bp_rule['status']})")

    if bmi_rule and bmi_rule["category"] != "missing":
        bmi_scores = {"normal": 0, "overweight": 5, "obese": 15, "underweight": 5}
        s = bmi_scores.get(bmi_rule.get("category", ""), 0)
        score += s
        if s >= 5:
            factors.append(f"BMI ({bmi_rule['status']})")

    if lipid_rules:
        worst_lipid = max(lipid_rules, key=lambda r: severity_rank(r["severity"]))
        lipid_scores = {"normal": 0, "elevated": 5, "high": 15, "low": 5}
        s = lipid_scores.get(worst_lipid["severity"], 0)
        score += s
        if s >= 5:
            factors.append(f"Lipids ({worst_lipid['status']})")

    if age and age > 45:
        age_pts = min(10, (age - 45) // 5 * 2)
        score += age_pts
        if age_pts >= 4:
            factors.append(f"Age ({age})")

    if ml and ml.get("score", 0) >= 0.5:
        ml_pts = min(5, int((ml["score"] - 0.5) * 10))
        score += ml_pts

    if score <= 15:
        level, color = "Low", "green"
    elif score <= 35:
        level, color = "Medium", "yellow"
    elif score <= 60:
        level, color = "High", "orange"
    else:
        level, color = "Very High", "red"

    return {
        "score": score, "level": level, "color": color,
        "factors": factors,
        "interpretation": f"Overall risk: {level} ({score}/100 points)",
    }


# ---------------------------------------------------------------------------
# Follow-up schedule
# ---------------------------------------------------------------------------
def followup_schedule(glucose_rules, bp_rule, overall_severity="normal"):
    if overall_severity in ("emergency", "critical", "severe"):
        return {"when": "Immediate", "text": "Seek medical attention now. Do not wait.",
                "color": "red", "icon": "alert"}
    if overall_severity in ("diabetes_range", "very_high"):
        return {"when": "Within 1-2 weeks",
                "text": "Confirm with a fasting glucose or HbA1c test. See a doctor.",
                "color": "orange", "icon": "warning"}

    has_prediabetes = False
    has_abnormal_bp = False
    if glucose_rules:
        for r in glucose_rules:
            if r["severity"] in ("prediabetes", "elevated", "needs_confirmation"):
                has_prediabetes = True
    if bp_rule and bp_rule["severity"] in ("stage1", "stage2"):
        has_abnormal_bp = True

    if has_prediabetes or has_abnormal_bp:
        return {"when": "3-6 months",
                "text": "Recheck fasting glucose/HbA1c. Lifestyle changes recommended.",
                "color": "yellow", "icon": "clipboard"}

    return {"when": "12 months",
            "text": "Annual screening recommended. Maintain healthy habits.",
            "color": "green", "icon": "check"}


# ---------------------------------------------------------------------------
# Emergency protocols
# ---------------------------------------------------------------------------
def emergency_protocols(glucose_rules, bp_rule, symptoms=None):
    protocols = []
    symptoms = symptoms or []

    if glucose_rules:
        for r in glucose_rules:
            val = r.get("value")
            if val is None:
                continue
            if val < 54:
                protocols.append({
                    "type": "Hypoglycemia (severe)", "urgency": "EMERGENCY", "color": "red",
                    "action": [
                        "If conscious: consume 15-20g fast-acting glucose (juice, glucose tablets)",
                        "Recheck in 15 minutes",
                        "If unconscious or unable to swallow: call emergency services immediately",
                        "Do NOT leave the person alone",
                    ],
                })
            elif val < 70:
                protocols.append({
                    "type": "Hypoglycemia (Level 1)", "urgency": "Urgent", "color": "orange",
                    "action": [
                        "Consume 15g fast-acting carbohydrate",
                        "Recheck glucose in 15 minutes",
                        "If symptoms persist, seek medical advice",
                    ],
                })
            elif val > 400:
                protocols.append({
                    "type": "Severe Hyperglycemia", "urgency": "EMERGENCY", "color": "red",
                    "action": [
                        "Seek emergency medical care immediately",
                        "Risk of diabetic ketoacidosis (DKA) or hyperosmolar syndrome",
                        "Do NOT exercise — it can worsen the condition",
                        "Drink water (if able to swallow)",
                    ],
                })
            elif val > 300:
                protocols.append({
                    "type": "Hyperglycemia (critical)", "urgency": "Urgent", "color": "orange",
                    "action": [
                        "Contact your doctor or seek urgent care",
                        "Check for ketones if diabetic",
                        "Stay hydrated — drink water",
                        "Avoid exercise until glucose normalizes",
                    ],
                })

    if bp_rule and bp_rule["severity"] in ("severe", "emergency"):
        protocols.append({
            "type": "Hypertensive Crisis",
            "urgency": "EMERGENCY" if bp_rule["severity"] == "emergency" else "Urgent",
            "color": "red" if bp_rule["severity"] == "emergency" else "orange",
            "action": [
                "Seek emergency medical care immediately",
                "Do NOT take extra blood pressure medication unless directed",
                "Sit upright and try to remain calm",
                "If chest pain, shortness of breath, or vision changes: call emergency services",
            ],
        })

    return protocols


# ---------------------------------------------------------------------------
# Family history
# ---------------------------------------------------------------------------
def family_history_risk(has_parent_diabetes=False, has_sibling_diabetes=False,
                        parent_diagnosed_age=None):
    risk_points = 0
    factors = []
    if has_parent_diabetes:
        risk_points += 30
        factors.append("Parent with diabetes")
    if has_sibling_diabetes:
        risk_points += 20
        factors.append("Sibling with diabetes")
    if parent_diagnosed_age and parent_diagnosed_age < 50:
        risk_points += 10
        factors.append(f"Parent diagnosed before age {parent_diagnosed_age} (early onset)")

    if risk_points == 0:
        level, color = "No family history reported", "green"
    elif risk_points <= 25:
        level, color = "Moderate family risk", "yellow"
    elif risk_points <= 40:
        level, color = "High family risk", "orange"
    else:
        level, color = "Very high family risk", "red"

    return {"points": risk_points, "level": level, "color": color, "factors": factors,
            "interpretation": f"Family history: {level}" if factors else "No family diabetes history reported"}


# ---------------------------------------------------------------------------
# Complication risks
# ---------------------------------------------------------------------------
def complication_risks(glucose_rules, bp_rule, bmi_rule, lipid_rules, age=None, smoking=False):
    risks = {}

    cvd_score = 0
    if bp_rule and bp_rule["severity"] in ("stage1", "stage2", "severe", "emergency"):
        cvd_score += 30
    if lipid_rules:
        for r in lipid_rules:
            if r["measurement_type"] == "ldl_c" and r["severity"] == "high":
                cvd_score += 20
            if r["measurement_type"] == "hdl_c" and r["severity"] == "low":
                cvd_score += 15
            if r["measurement_type"] == "triglycerides" and r["severity"] == "high":
                cvd_score += 10
    if glucose_rules:
        worst = max(glucose_rules, key=lambda r: severity_rank(r["severity"]))
        if worst["severity"] in ("diabetes_range", "very_high", "severe"):
            cvd_score += 25
        elif worst["severity"] in ("prediabetes", "elevated"):
            cvd_score += 10
    if age and age > 55:
        cvd_score += 10
    if smoking:
        cvd_score += 15
    risks["cardiovascular"] = {
        "score": min(100, cvd_score),
        "level": "High" if cvd_score >= 50 else ("Moderate" if cvd_score >= 25 else "Low"),
        "description": "Risk of heart disease, stroke, peripheral artery disease",
    }

    neuro_score = 0
    if glucose_rules:
        worst = max(glucose_rules, key=lambda r: severity_rank(r["severity"]))
        if worst["severity"] in ("diabetes_range", "very_high", "severe"):
            neuro_score += 60
        elif worst["severity"] in ("prediabetes", "elevated"):
            neuro_score += 20
    if bp_rule and bp_rule["severity"] in ("stage2", "severe"):
        neuro_score += 20
    risks["neuropathy"] = {
        "score": min(100, neuro_score),
        "level": "High" if neuro_score >= 50 else ("Moderate" if neuro_score >= 25 else "Low"),
        "description": "Risk of nerve damage (tingling, numbness, pain)",
    }

    nephro_score = 0
    if glucose_rules:
        worst = max(glucose_rules, key=lambda r: severity_rank(r["severity"]))
        if worst["severity"] in ("diabetes_range", "very_high"):
            nephro_score += 50
        elif worst["severity"] in ("prediabetes",):
            nephro_score += 15
    if bp_rule and bp_rule["severity"] in ("stage2", "severe"):
        nephro_score += 30
    risks["nephropathy"] = {
        "score": min(100, nephro_score),
        "level": "High" if nephro_score >= 50 else ("Moderate" if nephro_score >= 25 else "Low"),
        "description": "Risk of kidney damage (nephropathy)",
    }

    retino_score = 0
    if glucose_rules:
        worst = max(glucose_rules, key=lambda r: severity_rank(r["severity"]))
        if worst["severity"] in ("diabetes_range", "very_high"):
            retino_score += 55
        elif worst["severity"] in ("prediabetes",):
            retino_score += 10
    if bp_rule and bp_rule["severity"] in ("stage2", "severe"):
        retino_score += 25
    risks["retinopathy"] = {
        "score": min(100, retino_score),
        "level": "High" if retino_score >= 50 else ("Moderate" if retino_score >= 25 else "Low"),
        "description": "Risk of eye damage (diabetic retinopathy)",
    }

    return risks


# ---------------------------------------------------------------------------
# Lifestyle recommendations
# ---------------------------------------------------------------------------
def lifestyle_recommendations(glucose_rules, bp_rule, bmi_rule, lipid_rules, health_score=100):
    tips = []

    if glucose_rules:
        worst = max(glucose_rules, key=lambda r: severity_rank(r["severity"]))
        if worst["severity"] in ("prediabetes", "elevated"):
            tips.append({"category": "Diet", "priority": "high",
                         "tip": "Reduce refined carbs and sugary drinks. Choose whole grains, vegetables, and lean proteins.",
                         "source": "ADA 2026"})
            tips.append({"category": "Activity", "priority": "high",
                         "tip": "150 minutes/week of moderate exercise (brisk walking, cycling). Even 10-minute walks help.",
                         "source": "ADA 2026"})
        elif worst["severity"] in ("diabetes_range", "very_high"):
            tips.append({"category": "Diet", "priority": "urgent",
                         "tip": "See a dietitian for a meal plan. Count carbohydrates. Avoid sugary foods entirely.",
                         "source": "ADA 2026"})
            tips.append({"category": "Activity", "priority": "high",
                         "tip": "Exercise regularly but avoid intense activity if glucose >300 mg/dL.",
                         "source": "ADA 2026"})

    if bp_rule and bp_rule["severity"] in ("stage1", "stage2", "severe"):
        tips.append({"category": "Diet", "priority": "high",
                     "tip": "DASH diet: reduce sodium to <2300mg/day. Eat more fruits, vegetables, whole grains.",
                     "source": "AHA/ACC 2025"})
        tips.append({"category": "Lifestyle", "priority": "high",
                     "tip": "Limit alcohol to 1 drink/day (women) or 2 drinks/day (men). Quit smoking if applicable.",
                     "source": "AHA/ACC 2025"})

    if bmi_rule:
        if bmi_rule.get("category") == "overweight":
            tips.append({"category": "Weight", "priority": "medium",
                         "tip": "Losing 5-10% of body weight can significantly reduce diabetes risk.",
                         "source": "ADA 2026"})
        elif bmi_rule.get("category") == "obese":
            tips.append({"category": "Weight", "priority": "high",
                         "tip": "Weight loss of 5-10% is recommended. Consider structured program or medical guidance.",
                         "source": "ADA 2026"})

    if lipid_rules:
        for r in lipid_rules:
            if r["measurement_type"] == "ldl_c" and r["severity"] == "high":
                tips.append({"category": "Diet", "priority": "medium",
                             "tip": "Reduce saturated fat. Increase fiber (oats, beans, nuts). Consider fish twice weekly.",
                             "source": "AHA"})
            if r["measurement_type"] == "triglycerides" and r["severity"] == "high":
                tips.append({"category": "Diet", "priority": "medium",
                             "tip": "Reduce sugar and refined carbs. Limit alcohol. Increase omega-3 fatty acids.",
                             "source": "AHA"})

    tips.append({"category": "Sleep", "priority": "medium",
                 "tip": "Aim for 7-8 hours of quality sleep. Poor sleep worsens insulin resistance.",
                 "source": "ADA 2026"})
    tips.append({"category": "Stress", "priority": "low",
                 "tip": "Practice stress management (deep breathing, meditation). Chronic stress raises cortisol and glucose.",
                 "source": "ADA 2026"})

    return tips


# ---------------------------------------------------------------------------
# Medication impacts
# ---------------------------------------------------------------------------
MEDICATION_IMPACTS = {
    "prednisone": {"effect": "Raises blood glucose", "severity": "high",
                   "advice": "Monitor glucose closely. May need temporary insulin adjustment."},
    "dexamethasone": {"effect": "Raises blood glucose significantly", "severity": "high",
                      "advice": "Can cause steroid-induced hyperglycemia. Monitor frequently."},
    "metformin": {"effect": "Lowers blood glucose", "severity": "normal",
                  "advice": "Common first-line diabetes medication. Take with food to reduce GI side effects."},
    "insulin": {"effect": "Lowers blood glucose", "severity": "normal",
                "advice": "Monitor for hypoglycemia. Always carry fast-acting glucose."},
    "lisinopril": {"effect": "Lowers blood pressure, may affect potassium", "severity": "normal",
                   "advice": "ACE inhibitor. Monitor kidney function and potassium levels."},
    "amlodipine": {"effect": "Lowers blood pressure", "severity": "normal",
                   "advice": "Calcium channel blocker. May cause ankle swelling."},
    "atorvastatin": {"effect": "Lowers LDL cholesterol", "severity": "normal",
                     "advice": "Statin. Monitor liver function. Report unexplained muscle pain."},
    "aspirin": {"effect": "Blood thinner", "severity": "normal",
                "advice": "Low-dose aspirin for cardiovascular protection. Risk of bleeding."},
    "ibuprofen": {"effect": "May raise blood pressure, affect kidneys", "severity": "moderate",
                  "advice": "NSAID — use sparingly if you have hypertension or kidney concerns."},
    "naproxen": {"effect": "May raise blood pressure, affect kidneys", "severity": "moderate",
                 "advice": "NSAID — use sparingly if you have hypertension or kidney concerns."},
    "hydrochlorothiazide": {"effect": "Lowers blood pressure, may raise glucose", "severity": "moderate",
                            "advice": "Thiazide diuretic. May slightly raise blood sugar. Monitor glucose."},
    "glipizide": {"effect": "Lowers blood glucose", "severity": "normal",
                  "advice": "Sulfonylurea. Risk of hypoglycemia. Take before meals."},
    "jardiance": {"effect": "Lowers blood glucose and BP", "severity": "normal",
                  "advice": "SGLT2 inhibitor. May cause UTIs. Stay hydrated."},
    "ozempic": {"effect": "Lowers blood glucose, promotes weight loss", "severity": "normal",
                "advice": "GLP-1 agonist. May cause nausea. Inject weekly."},
}


def check_medication_impacts(medications):
    results = []
    for med in medications:
        med_lower = med.lower().strip()
        if med_lower in MEDICATION_IMPACTS:
            info = MEDICATION_IMPACTS[med_lower]
            results.append({"medication": med, **info})
        else:
            results.append({"medication": med, "effect": "Unknown", "severity": "unknown",
                            "advice": "No interaction data available. Consult your pharmacist."})
    return results


# ---------------------------------------------------------------------------
# Comorbidity assessment
# ---------------------------------------------------------------------------
def comorbidity_assessment(has_diabetes=False, has_hypertension=False, has_obesity=False,
                           has_dyslipidemia=False, has_ckd=False, has_heart_disease=False):
    conditions = []
    if has_diabetes:
        conditions.append("Diabetes")
    if has_hypertension:
        conditions.append("Hypertension")
    if has_obesity:
        conditions.append("Obesity")
    if has_dyslipidemia:
        conditions.append("Dyslipidemia")
    if has_ckd:
        conditions.append("Chronic Kidney Disease")
    if has_heart_disease:
        conditions.append("Heart Disease")

    n = len(conditions)
    if n == 0:
        return {"count": 0, "level": "No comorbidities", "color": "green",
                "multiplier": 1.0, "conditions": [], "interpretation": "No reported comorbidities."}

    multiplier = 1.0
    if has_diabetes and has_hypertension:
        multiplier = 2.0
    if has_diabetes and has_heart_disease:
        multiplier = 2.5
    if has_diabetes and has_ckd:
        multiplier = 2.5
    if n >= 3:
        multiplier = 3.0

    if multiplier >= 2.5:
        level, color = "Very high combined risk", "red"
    elif multiplier >= 2.0:
        level, color = "High combined risk", "orange"
    elif n >= 1:
        level, color = "Moderate combined risk", "yellow"
    else:
        level, color = "Low risk", "green"

    return {"count": n, "level": level, "color": color, "multiplier": multiplier,
            "conditions": conditions,
            "interpretation": f"{n} comorbid condition(s): {', '.join(conditions)}. Risk multiplier: {multiplier}x"}


# ---------------------------------------------------------------------------
# What-if simulator
# ---------------------------------------------------------------------------
def whatif_simulate(baseline_glucose=None, baseline_bp_sbp=None, baseline_bmi=None,
                    target_glucose=None, target_bp_sbp=None, target_bmi=None):
    changes = []

    if baseline_glucose is not None and target_glucose is not None:
        base_rule = classify_glucose(baseline_glucose, "fasting")
        target_rule = classify_glucose(target_glucose, "fasting")
        diff = severity_rank(base_rule["severity"]) - severity_rank(target_rule["severity"])
        changes.append({
            "metric": "Fasting Glucose",
            "from": f"{baseline_glucose} mg/dL", "to": f"{target_glucose} mg/dL",
            "from_status": base_rule["status"], "to_status": target_rule["status"],
            "improved": diff > 0, "same": diff == 0,
            "impact": "Significant improvement" if diff >= 2 else ("Moderate improvement" if diff > 0 else ("Worsened" if diff < 0 else "No change")),
        })

    if baseline_bp_sbp is not None and target_bp_sbp is not None:
        base_rule = classify_bp(baseline_bp_sbp, None)
        target_rule = classify_bp(target_bp_sbp, None)
        diff = severity_rank(base_rule["severity"]) - severity_rank(target_rule["severity"])
        changes.append({
            "metric": "Blood Pressure (SBP)",
            "from": f"{baseline_bp_sbp} mmHg", "to": f"{target_bp_sbp} mmHg",
            "from_status": base_rule["status"], "to_status": target_rule["status"],
            "improved": diff > 0, "same": diff == 0,
            "impact": "Significant improvement" if diff >= 2 else ("Moderate improvement" if diff > 0 else ("Worsened" if diff < 0 else "No change")),
        })

    if baseline_bmi is not None and target_bmi is not None:
        base_rule = compute_bmi(baseline_bmi, 170)
        target_weight = target_bmi * (1.7 ** 2)
        target_rule = compute_bmi(target_weight, 170)
        changes.append({
            "metric": "BMI",
            "from": f"{baseline_bmi:.1f}", "to": f"{target_bmi:.1f}",
            "from_status": base_rule["status"], "to_status": target_rule["status"],
            "improved": severity_rank(base_rule["severity"]) > severity_rank(target_rule["severity"]),
            "same": base_rule["severity"] == target_rule["severity"],
            "impact": "Risk reduction" if severity_rank(base_rule["severity"]) > severity_rank(target_rule["severity"]) else "No change",
        })

    return changes


# ---------------------------------------------------------------------------
# Gestational diabetes
# ---------------------------------------------------------------------------
GESTATIONAL_THRESHOLDS = {
    "fasting": {"normal": (0, 92), "elevated": (92, 126), "diabetes": (126, 999)},
    "1h_postmeal": {"normal": (0, 140), "elevated": (140, 180), "diabetes": (180, 999)},
    "2h_postmeal": {"normal": (0, 120), "elevated": (120, 153), "diabetes": (153, 999)},
}


def classify_gestational_glucose(value, measurement_type):
    if value is None:
        return _missing("glucose", f"gestational_{measurement_type}")
    try:
        v = float(value)
    except (TypeError, ValueError):
        return _invalid("glucose", f"gestational_{measurement_type}")

    thresholds = GESTATIONAL_THRESHOLDS.get(measurement_type)
    if not thresholds:
        return _invalid("glucose", f"gestational_{measurement_type}", "Unknown measurement type.")

    if v < thresholds["normal"][1]:
        return _rule("glucose", f"gestational_{measurement_type}", v, "normal", "normal",
                     "Normal for pregnancy",
                     f"Gestational glucose {v:.0f} mg/dL is within target for pregnancy.",
                     source="ACOG 2024")
    if v < thresholds["diabetes"][0]:
        return _rule("glucose", f"gestational_{measurement_type}", v, "gestational_diabetes", "elevated",
                     "Gestational diabetes range",
                     f"Gestational glucose {v:.0f} mg/dL exceeds pregnancy target. Diagnosis requires OGTT.",
                     source="ACOG 2024")
    return _rule("glucose", f"gestational_{measurement_type}", v, "pregestational_diabetes", "high",
                 "Pre-existing diabetes range",
                 f"Glucose {v:.0f} mg/dL suggests possible pre-existing diabetes. Further testing needed.",
                 source="ACOG 2024")


# ---------------------------------------------------------------------------
# Pediatric / elderly adjustments
# ---------------------------------------------------------------------------
def pediatric_adjustments(age, has_type2_risk_factors=False):
    if age is None:
        return {"applicable": False}
    try:
        age = int(age)
    except (TypeError, ValueError):
        return {"applicable": False}
    if age >= 18:
        return {"applicable": False}

    notes = []
    if age < 10:
        notes.append("Type 2 diabetes is rare under age 10. Type 1 is more common in children.")
    if has_type2_risk_factors:
        notes.append("Screening recommended due to risk factors (obesity, family history, race/ethnicity).")

    return {
        "applicable": True, "age": age, "notes": notes,
        "interpretation": f"Pediatric patient (age {age}). " + " ".join(notes) if notes else f"Pediatric patient (age {age}).",
        "source": "ADA 2026 — Pediatric screening guidelines",
    }


def elderly_adjustments(age, comorbidities=None):
    if age is None:
        return {"applicable": False}
    try:
        age = int(age)
    except (TypeError, ValueError):
        return {"applicable": False}
    if age <= 65:
        return {"applicable": False}

    comorbidities = comorbidities or []
    frail = "frail" in [c.lower() for c in comorbidities]

    targets = {
        "fasting_glucose": "90-150 mg/dL" if frail else "80-130 mg/dL",
        "hba1c": "<8.5%" if frail else "<8.0%",
        "bp_systolic": "<150 mmHg" if frail else "<140 mmHg",
    }

    notes = ["Frail elderly: relax targets to avoid hypoglycemia risk." if frail
             else "Healthy elderly: slightly relaxed targets compared to younger adults."]

    return {"applicable": True, "age": age, "targets": targets, "notes": notes, "frail": frail,
            "interpretation": f"Elderly patient (age {age}). " + " ".join(notes),
            "source": "ADA 2026 — Older adults guidelines"}


# ---------------------------------------------------------------------------
# Report comparison
# ---------------------------------------------------------------------------
def compare_reports(current, previous):
    comparisons = []
    metrics = [
        ("fasting_glucose", "Fasting Glucose", "mg/dL"),
        ("postmeal_glucose", "Post-meal Glucose", "mg/dL"),
        ("hba1c", "HbA1c", "%"),
        ("sbp", "Systolic BP", "mmHg"),
        ("dbp", "Diastolic BP", "mmHg"),
        ("bmi", "BMI", "kg/m²"),
        ("ldl", "LDL-C", "mg/dL"),
        ("hdl", "HDL-C", "mg/dL"),
        ("triglycerides", "Triglycerides", "mg/dL"),
    ]

    for key, label, unit in metrics:
        cur = current.get(key)
        prev = previous.get(key)
        if cur is not None and prev is not None:
            diff = cur - prev
            pct = (diff / prev * 100) if prev != 0 else 0
            lower_better = key in ("fasting_glucose", "postmeal_glucose", "hba1c",
                                   "sbp", "dbp", "bmi", "ldl", "triglycerides")
            improved = (diff < 0) if lower_better else (diff > 0)
            comparisons.append({
                "metric": label, "unit": unit, "current": cur, "previous": prev,
                "change": round(diff, 1), "pct_change": round(pct, 1),
                "improved": improved,
                "summary": f"{label}: {prev} → {cur} ({'↓' if diff < 0 else '↑'}{abs(pct):.1f}%)",
            })

    improved_count = sum(1 for c in comparisons if c["improved"])
    total = len(comparisons)

    return {"comparisons": comparisons, "improved": improved_count, "total": total,
            "summary": f"{improved_count}/{total} metrics improved" if total > 0 else "No comparable data"}


# ---------------------------------------------------------------------------
# Risk factor breakdown
# ---------------------------------------------------------------------------
def risk_factor_breakdown(glucose_rules, bp_rule, bmi_rule, lipid_rules, ml=None,
                          family_history=None, age=None):
    factors = []

    if glucose_rules:
        worst = max(glucose_rules, key=lambda r: severity_rank(r["severity"]))
        contrib = {"fasting": 0, "elevated": 15, "prediabetes": 25, "stage1": 30,
                   "high": 35, "stage2": 40, "very_high": 45, "diabetes_range": 50,
                   "severe": 50, "critical": 50, "emergency": 50}
        pts = contrib.get(worst["severity"], 0)
        factors.append({"factor": "Glucose", "contribution": pts, "status": worst["status"],
                        "detail": f"{worst['measurement_type']}: {worst['value']}"})

    if bp_rule:
        bp_contrib = {"normal": 0, "elevated": 10, "stage1": 20, "stage2": 30,
                      "severe": 40, "emergency": 40, "low": 10}
        pts = bp_contrib.get(bp_rule["severity"], 0)
        factors.append({"factor": "Blood Pressure", "contribution": pts, "status": bp_rule["status"],
                        "detail": f"BP: {bp_rule['value']}"})

    if bmi_rule and bmi_rule["category"] != "missing":
        bmi_contrib = {"normal": 0, "overweight": 15, "obese": 30, "underweight": 10}
        pts = bmi_contrib.get(bmi_rule.get("category", ""), 0)
        factors.append({"factor": "BMI", "contribution": pts, "status": bmi_rule["status"],
                        "detail": f"BMI: {bmi_rule['value']}"})

    if lipid_rules:
        worst = max(lipid_rules, key=lambda r: severity_rank(r["severity"]))
        lipid_contrib = {"normal": 0, "elevated": 10, "high": 20, "low": 10}
        pts = lipid_contrib.get(worst["severity"], 0)
        factors.append({"factor": "Lipids", "contribution": pts, "status": worst["status"],
                        "detail": f"{worst['measurement_type']}: {worst['value']}"})

    if age and age > 45:
        pts = min(15, (age - 45) // 5 * 3)
        factors.append({"factor": "Age", "contribution": pts, "status": f"Age {age}",
                        "detail": "Age-related risk increase"})

    if family_history and family_history.get("points", 0) > 0:
        pts = min(20, family_history["points"] // 2)
        factors.append({"factor": "Family History", "contribution": pts,
                        "status": family_history.get("level", ""),
                        "detail": "; ".join(family_history.get("factors", []))})

    if ml and ml.get("score", 0) >= 0.5:
        pts = min(10, int((ml["score"] - 0.5) * 20))
        factors.append({"factor": "ML Model", "contribution": pts,
                        "status": f"Risk: {ml['score']:.0%}",
                        "detail": "PIMA Gradient Boosting prediction"})

    factors.sort(key=lambda f: f["contribution"], reverse=True)
    total = sum(f["contribution"] for f in factors)

    return {"factors": factors, "total": total,
            "summary": f"Top risk factor: {factors[0]['factor']} ({factors[0]['contribution']} pts)" if factors else "No risk factors identified"}


# ---------------------------------------------------------------------------
# Health score (0-100)
# ---------------------------------------------------------------------------
g_deductions = {
    "emergency": 35, "critical": 35, "severe": 30, "high": 25,
    "stage2": 25, "stage1": 15, "moderate": 15, "elevated": 10,
    "low": 15, "normal": 0, "prediabetes": 15, "needs_confirmation": 10,
    "very_high": 35, "diabetes_range": 30,
}
bp_deductions = {
    "emergency": 25, "critical": 25, "severe": 25, "stage2": 20,
    "stage1": 10, "elevated": 5, "low": 10, "normal": 0,
}
bmi_deductions = {
    "obese_class3": 20, "obese_class2": 18, "obese_class1": 14,
    "obese": 14, "overweight": 8, "normal": 0, "underweight": 10,
}
lipid_deductions = {"high": 15, "moderate": 10, "borderline": 5, "normal": 0, "elevated": 10, "low": 5}


def calculate_health_score(glucose_rules, bp_rule, bmi_rule, lipid_rules, ml=None):
    """Calculate a 0-100 health score. Higher = healthier."""
    score = 100
    deductions = []

    if glucose_rules:
        worst_g = max(glucose_rules, key=lambda r: severity_rank(r["severity"]))
        d = g_deductions.get(worst_g["severity"], 0)
        score -= d
        if d > 0:
            deductions.append(f"Glucose: -{d}")

    if bp_rule:
        d = bp_deductions.get(bp_rule["severity"], 0)
        score -= d
        if d > 0:
            deductions.append(f"BP: -{d}")

    if bmi_rule and bmi_rule.get("category") != "missing":
        d = bmi_deductions.get(bmi_rule.get("category", ""), 0)
        score -= d
        if d > 0:
            deductions.append(f"BMI: -{d}")

    if lipid_rules:
        worst_lipid = max(lipid_rules, key=lambda r: severity_rank(r["severity"]))
        d = lipid_deductions.get(worst_lipid["severity"], 0)
        score -= d
        if d > 0:
            deductions.append(f"Lipids: -{d}")

    if ml and ml.get("score", 0) >= 0.5:
        ml_d = min(5, int((ml["score"] - 0.5) * 10))
        score -= ml_d
        if ml_d > 0:
            deductions.append(f"ML risk: -{ml_d}")

    score = max(0, min(100, score))
    return score, deductions


# ---------------------------------------------------------------------------
# Screening orchestrator (used by the FastAPI route)
# ---------------------------------------------------------------------------
_GLUCOSE_TYPE_MAP = {
    "fasting": "fasting",
    "hba1c": "hba1c",
    "ogtt": "ogtt2h",
    "random": "random",
    "postprandial": "postmeal2h",
}


def run_clinical_screening(input_data: Any) -> dict:
    """Run the full clinical screening for a ScreeningInput-like object.

    Returns a dict with glucose_rules, bp_rule, bmi_rule, lipid_rules,
    aggregate, and risk breakdown fields.
    """
    glucose_type = _GLUCOSE_TYPE_MAP.get(input_data.glucose_type, "fasting")

    glucose_rules = []
    if input_data.glucose_mg_dl is not None:
        glucose_rules.append(classify_glucose(input_data.glucose_mg_dl, glucose_type))

    bp_rule = classify_bp(input_data.sbp, input_data.dbp)
    bmi_rule = compute_bmi(input_data.weight_kg, input_data.height_cm)
    lipid_rules = classify_lipids(
        ldl=input_data.ldl_mg_dl,
        hdl=input_data.hdl_mg_dl,
        trig=input_data.triglycerides_mg_dl,
    )

    aggregate = aggregate_evidence(
        glucose_rules=glucose_rules,
        bp_rule=bp_rule,
        bmi_rule=bmi_rule,
        lipid_rules=lipid_rules,
    )

    breakdown = risk_factor_breakdown(
        glucose_rules=glucose_rules,
        bp_rule=bp_rule,
        bmi_rule=bmi_rule,
        lipid_rules=lipid_rules,
        age=input_data.age,
    )

    return {
        "glucose_rules": glucose_rules,
        "bp_rule": bp_rule,
        "bmi_rule": bmi_rule,
        "lipid_rules": lipid_rules,
        "aggregate": aggregate,
        "risk_breakdown": breakdown,
    }
