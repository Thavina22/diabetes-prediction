"""Server-side clinical PDF generation (reportlab).

Adapted from the original Streamlit app's `make_clinical_pdf`, now producing
the PDF from a validated `ScreeningResult` object.
"""

import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def _score_label(score: int) -> str:
    if score >= 85:
        return "Good"
    if score >= 70:
        return "Fair"
    if score >= 50:
        return "Needs attention"
    return "High concern"


def _as_dict(rule):
    """Normalise a ClinicalRule (Pydantic) or plain dict to a dict."""
    if rule is None:
        return None
    if hasattr(rule, "model_dump"):
        return rule.model_dump()
    return dict(rule)


def generate_clinical_pdf(result) -> bytes:
    """Render a one-page clinical screening PDF for a ScreeningResult."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    input_data = result.input
    glucose_rules = [_as_dict(r) for r in result.glucose_rules]
    bp_rule = _as_dict(result.bp_rule)
    bmi_rule = _as_dict(result.bmi_rule)
    lipid_rules = [_as_dict(r) for r in result.lipid_rules]
    ml = result.ml_result
    health_score = result.health_score

    # Header
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, h - 60, "Health Screening Report")
    c.setFont("Helvetica", 10)
    c.drawString(50, h - 80,
                 f"Diabetes Risk Intelligence · Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    c.drawString(50, h - 94, "Screening only — not a diagnosis. Consult a healthcare provider.")

    y = h - 130

    # Health score
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, f"Health Score: {health_score}/100 ({_score_label(health_score)})")
    y -= 25

    # Measurements
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Measurements")
    y -= 18
    c.setFont("Helvetica", 10)

    def draw_row(label, value, unit, status):
        nonlocal y
        c.drawString(60, y, f"{label}:")
        c.drawString(220, y, f"{value} {unit}")
        c.drawString(360, y, str(status)[:40])
        y -= 15

    for r in glucose_rules:
        unit = "%" if r["measurement_type"] == "hba1c" else "mg/dL"
        draw_row(f"Glucose ({r['measurement_type']})", r["value"], unit, r["status"])
    if bp_rule and bp_rule.get("category") != "missing":
        draw_row("Blood pressure", f"{bp_rule['value']}", "mmHg", bp_rule["status"])
    if bmi_rule and bmi_rule.get("category") != "missing":
        draw_row("BMI", f"{bmi_rule['value']}", "kg/m2", bmi_rule["status"])
    for r in lipid_rules:
        draw_row(str(r["measurement_type"]), r["value"], "mg/dL", r["status"])
    if ml and ml.score is not None:
        draw_row("ML Risk", f"{ml.score:.0%}", "", "Elevated" if ml.score >= 0.5 else "Lower")

    y -= 10

    # Red flags / emergency
    if result.emergency_flags:
        c.setFont("Helvetica-Bold", 11)
        c.setFillColorRGB(0.75, 0.22, 0.17)
        c.drawString(50, y, "URGENT — Seek medical attention")
        y -= 16
        c.setFont("Helvetica", 10)
        for f in result.emergency_flags:
            c.drawString(60, y, f"• {f.type} ({f.urgency})")
            y -= 14
        c.setFillColorRGB(0, 0, 0)
        y -= 5

    # Interpretation
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Interpretation")
    y -= 16
    c.setFont("Helvetica", 10)
    for r in glucose_rules:
        if r.get("interpretation"):
            c.drawString(60, y, f"• {r['measurement_type']}: {r['interpretation'][:90]}")
            y -= 14
    if bp_rule and bp_rule.get("interpretation"):
        c.drawString(60, y, f"• BP: {bp_rule['interpretation'][:90]}")
        y -= 14
    if bmi_rule and bmi_rule.get("interpretation"):
        c.drawString(60, y, f"• BMI: {bmi_rule['interpretation'][:90]}")
        y -= 14

    y -= 10

    # Follow-up
    if result.followup_schedule:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, "Follow-up")
        y -= 16
        c.setFont("Helvetica", 10)
        c.drawString(60, y, f"{result.followup_schedule.when}: {result.followup_schedule.text}"[:100])
        y -= 14

    # Disclaimer
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.48, 0.44, 0.41)
    c.drawString(50, 40,
                 "This report is for screening and educational purposes only. It is not a medical diagnosis.")
    c.drawString(50, 28,
                 "Sources: ADA Standards of Care 2026, AHA/ACC BP Guidelines 2025, WHO/IDF consensus.")
    c.setFillColorRGB(0, 0, 0)

    c.save()
    return buf.getvalue()
