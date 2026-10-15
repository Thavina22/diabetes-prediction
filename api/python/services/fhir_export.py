"""FHIR R4 and CDA export for screening results.

Produces a FHIR R4 Bundle of Observation resources plus a minimal
HL7 CDA R2 document for interoperability with EHR systems.
"""

from datetime import datetime, timezone
from typing import Any
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


def generate_fhir_bundle(result: dict, user_id: str) -> dict:
    """Build a FHIR R4 collection Bundle from a screening result dict."""
    now = datetime.now(timezone.utc).isoformat()
    inp = result.get("input", {})
    entries = []

    field_map = {
        "glucose": ("glucose", "mg/dL"),
        "hba1c": ("hba1c", "%"),
        "systolic_bp": ("systolic", "mmHg"),
        "diastolic_bp": ("diastolic", "mmHg"),
        "bmi": ("bmi", "kg/m2"),
        "hdl": ("hdl", "mg/dL"),
        "triglycerides": ("triglycerides", "mg/dL"),
    }
    for field, (code, unit) in field_map.items():
        value = inp.get(field)
        if value is not None:
            entries.append({
                "fullUrl": f"urn:uuid:{code}-{user_id}",
                "resource": _observation(code, value, unit, now, user_id),
            })

    return {
        "resourceType": "Bundle",
        "id": str(result.get("id", "screening")),
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
