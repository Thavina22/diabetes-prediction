"""FHIR R4 and CDA export for screening results.

Produces a FHIR R4 Bundle of Observation resources plus a minimal
HL7 CDA R2 document for interoperability with EHR systems.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from xml.sax.saxutils import escape

FHIR_LOINC = {
    "glucose": {"code": "2339-0", "display": "Glucose [Mass/volume] in Blood"},
    "hba1c": {"code": "4548-4", "display": "Hemoglobin A1c/Hemoglobin.total in Blood"},
    "systolic": {"code": "8480-6", "display": "Systolic blood pressure"},
    "diastolic": {"code": "8462-4", "display": "Diastolic blood pressure"},
    "bmi": {"code": "39156-5", "display": "Body mass index (BMI) [Ratio]"},
    "hdl": {"code": "2085-9", "display": "Cholesterol in HDL [Mass/volume] in Serum"},
    "triglycerides": {"code": "2571-8", "display": "Triglycerides [Mass/volume] in Serum"},
}


def _observation(code: str, value: float, unit: str, effective: str, user_id: str) -> dict:
    loinc = FHIR_LOINC.get(code, {"code": code, "display": code})
    return {
        "resourceType": "Observation",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": loinc["code"],
                "display": loinc["display"],
            }]
        },
        "subject": {"reference": f"Patient/{user_id}"},
        "effectiveDateTime": effective,
        "valueQuantity": {"value": value, "unit": unit, "system": "http://unitsofmeasure.org"},
    }


def _bmi(inp: dict) -> float | None:
    height = inp.get("height_cm")
    weight = inp.get("weight_kg")
    if height and weight:
        return round(weight / ((height / 100.0) ** 2), 1)
    return None


def generate_fhir_bundle(result: dict, user_id: str) -> dict:
    """Build a FHIR R4 collection Bundle from a screening result dict.

    Maps the ScreeningInput schema (glucose_mg_dl, sbp, dbp, height_cm,
    weight_kg, hdl_mg_dl, triglycerides_mg_dl) onto LOINC-coded Observations.
    """
    now = datetime.now(timezone.utc).isoformat()
    inp = result.get("input", {}) or {}
    screening_id = str(result.get("id", "screening"))
    entries: list[dict] = []

    def add(code: str, value: Any, unit: str) -> None:
        if value is None:
            return
        entries.append({
            "fullUrl": f"urn:uuid:{uuid4()}",
            "resource": _observation(code, float(value), unit, now, user_id),
        })

    if inp.get("glucose_type") == "hba1c":
        add("hba1c", inp.get("glucose_mg_dl"), "%")
    else:
        add("glucose", inp.get("glucose_mg_dl"), "mg/dL")
    add("systolic", inp.get("sbp"), "mmHg")
    add("diastolic", inp.get("dbp"), "mmHg")
    add("bmi", _bmi(inp), "kg/m2")
    add("hdl", inp.get("hdl_mg_dl"), "mg/dL")
    add("triglycerides", inp.get("triglycerides_mg_dl"), "mg/dL")

    return {
        "resourceType": "Bundle",
        "id": screening_id.replace(".", "-"),
        "type": "collection",
        "timestamp": now,
        "entry": entries,
    }


def generate_cda(result: dict, user_id: str) -> str:
    """Build a minimal HL7 CDA R2 XML document from a screening result dict."""
    now = datetime.now(timezone.utc).isoformat()
    score = result.get("health_score", "")
    risk = escape(str(result.get("risk_category", "")))
    text = (
        f'<paragraph>Health score: {escape(str(score))}. '
        f'Risk category: {risk}.</paragraph>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<ClinicalDocument xmlns="urn:hl7-org:v3">\n'
        '  <typeId root="2.16.840.1.113883.1.3" extension="POCD_HD000040"/>\n'
        f'  <id root="{escape(str(user_id))}"/>\n'
        f'  <effectiveTime value="{now}"/>\n'
        '  <component>\n'
        '    <structuredBody>\n'
        '      <section>\n'
        '        <code code="11450-4" codeSystem="2.16.840.1.113883.6.1"/>\n'
        f'        <text>{text}</text>\n'
        '      </section>\n'
        '    </structuredBody>\n'
        '  </component>\n'
        '</ClinicalDocument>\n'
    )
