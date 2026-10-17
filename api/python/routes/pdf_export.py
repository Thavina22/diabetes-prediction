import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from models.screening import ScreeningInput
from services.screening_engine import build_result
from services.pdf_generator import generate_clinical_pdf
from auth.clerk import get_current_user_id

router = APIRouter()


def _result(input_data: ScreeningInput, user_id: str):
    try:
        return build_result(input_data, user_id)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Screening failed: {str(e)}") from e


@router.post("/export/pdf")
async def export_pdf(
    input_data: ScreeningInput,
    user_id: str = Depends(get_current_user_id),
):
    """Generate a clinical PDF for a screening input (without storing it)."""
    result = _result(input_data, user_id)
    try:
        pdf_bytes = generate_clinical_pdf(result)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}") from e
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=diabetes_screening_report.pdf"},
    )


@router.post("/export/fhir")
async def export_fhir(
    input_data: ScreeningInput,
    user_id: str = Depends(get_current_user_id),
):
    """Generate a FHIR R4 Bundle for a screening input (without storing it)."""
    from services.fhir_export import generate_fhir_bundle

    result = _result(input_data, user_id)
    payload = result.model_dump(mode="json")
    bundle = generate_fhir_bundle(payload, user_id)
    return Response(
        content=json.dumps(bundle),
        media_type="application/fhir+json",
        headers={"Content-Disposition": "attachment; filename=screening.fhir.json"},
    )


@router.post("/export/cda")
async def export_cda(
    input_data: ScreeningInput,
    user_id: str = Depends(get_current_user_id),
):
    """Generate an HL7 CDA R2 document for a screening input (without storing it)."""
    from services.fhir_export import generate_cda

    result = _result(input_data, user_id)
    payload = result.model_dump(mode="json")
    cda_xml = generate_cda(payload, user_id)
    return Response(
        content=cda_xml,
        media_type="application/xml",
        headers={"Content-Disposition": "attachment; filename=screening.cda.xml"},
    )
