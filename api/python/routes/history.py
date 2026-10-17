import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from models.screening import ScreeningResult
from db.connection import is_db_ready
from db.repositories.users import user_connection
from auth.clerk import get_current_user_id

router = APIRouter()


@router.get("/history")
async def list_screenings(
    limit: int = 20,
    offset: int = 0,
    risk_category: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
):
    """List user's screening history with pagination."""
    if not is_db_ready():
        return {"screenings": [], "total": 0, "limit": limit, "offset": offset}

    async with user_connection(user_id) as (conn, internal_id):
        query = """
            SELECT id, health_score, risk_category, created_at
            FROM screenings
            WHERE user_id = $1
        """
        params = [internal_id]
        param_idx = 2

        if risk_category:
            query += f" AND risk_category = ${param_idx}"
            params.append(risk_category)
            param_idx += 1

        query += f" ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
        params.extend([limit, offset])

        rows = await conn.fetch(query, *params)

        total_query = "SELECT COUNT(*) FROM screenings WHERE user_id = $1"
        if risk_category:
            total_query += " AND risk_category = $2"
            total = await conn.fetchval(total_query, internal_id, risk_category)
        else:
            total = await conn.fetchval(total_query, internal_id)

        return {
            "screenings": [dict(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@router.get("/history/{screening_id}", response_model=ScreeningResult)
async def get_screening_detail(
    screening_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    """Get detailed screening result."""
    if not is_db_ready():
        raise HTTPException(status_code=503, detail="Persistence not configured")
    async with user_connection(user_id) as (conn, internal_id):
        row = await conn.fetchrow(
            "SELECT * FROM screenings WHERE id = $1 AND user_id = $2",
            screening_id, internal_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Screening not found")
        return ScreeningResult.model_validate_json(row["result_json"])


@router.get("/history/{screening_id}/export")
async def export_screening(
    screening_id: UUID,
    format: str = "pdf",
    user_id: str = Depends(get_current_user_id),
):
    """Export screening as PDF, FHIR, or CDA."""
    if not is_db_ready():
        raise HTTPException(status_code=503, detail="Persistence not configured")

    async with user_connection(user_id) as (conn, internal_id):
        row = await conn.fetchrow(
            "SELECT * FROM screenings WHERE id = $1 AND user_id = $2",
            screening_id, internal_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Screening not found")

        result = ScreeningResult.model_validate_json(row["result_json"])
        payload = result.model_dump(mode="json")

        if format == "pdf":
            from services.pdf_generator import generate_clinical_pdf
            pdf_bytes = generate_clinical_pdf(result)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=screening_{screening_id}.pdf"},
            )
        if format == "fhir":
            from services.fhir_export import generate_fhir_bundle
            bundle = generate_fhir_bundle(payload, user_id)
            return Response(
                content=json.dumps(bundle),
                media_type="application/fhir+json",
                headers={"Content-Disposition": f"attachment; filename=screening_{screening_id}.fhir.json"},
            )
        if format == "cda":
            from services.fhir_export import generate_cda
            cda_xml = generate_cda(payload, user_id)
            return Response(
                content=cda_xml,
                media_type="application/xml",
                headers={"Content-Disposition": f"attachment; filename=screening_{screening_id}.cda.xml"},
            )
        raise HTTPException(status_code=400, detail="Invalid format. Use: pdf, fhir, or cda")
