"""Exporters — FHIR R4 Bundle, HL7 CDA, and the reportlab PDF."""

from models.screening import ScreeningInput

from services.fhir_export import FHIR_LOINC, generate_cda, generate_fhir_bundle
from services.pdf_generator import generate_clinical_pdf
from services.screening_engine import build_result

EXPECTED_CODES = {
    "glucose": "2339-0",
    "systolic": "8480-6",
    "diastolic": "8462-4",
    "bmi": "39156-5",
    "hdl": "2085-9",
    "triglycerides": "2571-8",
}


def _payload(input_data: ScreeningInput) -> dict:
    return build_result(input_data, "export-user").model_dump(mode="json")


def _codes(bundle: dict) -> set[str]:
    return {entry["resource"]["code"]["coding"][0]["code"] for entry in bundle["entry"]}


def test_fhir_bundle_maps_every_provided_field(high_risk_input: ScreeningInput):
    bundle = generate_fhir_bundle(_payload(high_risk_input), "export-user")
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert {FHIR_LOINC[name]["code"] for name in EXPECTED_CODES} <= _codes(bundle)


def test_fhir_uses_hba1c_code_when_glucose_type_is_hba1c():
    input_data = ScreeningInput(glucose_mg_dl=6.8, glucose_type="hba1c", age=50, sbp=120, dbp=80)
    bundle = generate_fhir_bundle(_payload(input_data), "u")
    codes = _codes(bundle)
    assert FHIR_LOINC["hba1c"]["code"] in codes
    assert FHIR_LOINC["glucose"]["code"] not in codes


def test_fhir_skips_absent_measurements():
    input_data = ScreeningInput(glucose_mg_dl=None, sbp=None, dbp=None, age=40)
    bundle = generate_fhir_bundle(_payload(input_data), "u")
    assert bundle["entry"] == []


def test_fhir_bmi_is_computed():
    input_data = ScreeningInput(glucose_mg_dl=95, height_cm=175, weight_kg=70, age=40)
    bundle = generate_fhir_bundle(_payload(input_data), "u")
    bmi = [e for e in bundle["entry"] if e["resource"]["code"]["coding"][0]["code"] == "39156-5"]
    assert len(bmi) == 1
    assert 22.0 <= bmi[0]["resource"]["valueQuantity"]["value"] <= 23.0


def test_cda_is_wellformed_xml(normal_input: ScreeningInput):
    xml = generate_cda(_payload(normal_input), "u")
    assert xml.startswith("<?xml")
    assert "ClinicalDocument" in xml
    assert xml.rstrip().endswith("</ClinicalDocument>")
    import xml.etree.ElementTree as ET

    ET.fromstring(xml)  # raises if malformed


def test_pdf_returns_pdf_bytes(high_risk_input: ScreeningInput):
    result = build_result(high_risk_input, "u")
    pdf = generate_clinical_pdf(result)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
