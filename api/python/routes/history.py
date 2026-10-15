from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from uuid import UUID

from models.screening import ScreeningResult
from db.connection import get_connection
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
    async with get_connection() as conn:
        query = """
            SELECT id, health_score, risk_category, created_at
            FROM screenings
            WHERE user_id = $1
        """
        params = [user_id]
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
            total = await conn.fetchval(total_query, user_id, risk_category)
        else:
            total = await conn.fetchval(total_query, user_id)

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
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM screenings WHERE id = $1 AND user_id = $2
        """, screening_id, user_id)

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
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM screenings WHERE id = $1 AND user_id = $2
        """, screening_id, user_id)

        if not row:
            raise HTTPException(status_code=404, detail="Screening not found")

        result = ScreeningResult.model_validate_json(row["result_json"])

        if format == "pdf":
            from services.pdf_generator import generate_clinical_pdf
            pdf_bytes = generate_clinical_pdf(result)
            from fastapi.responses import Response
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=screening_{screening_id}.pdf"}
            )
        elif format == "fhir":
            from services.fhir_export import generate_fhir_bundle
            fhir_json = generate_fhir_bundle(result)
            from fastapi.responses import Response
            return Response(
                content=fhir_json,
                media_type="application/fhir+json",
                headers={"Content-Disposition": f"attachment; filename=screening_{screening_id}.fhir.json"}
            )
        elif format == "cda":
            from services.fhir_export import generate_cda
            cda_xml = generate_cda(result)
            from fastapi.responses import Response
            return Response(
                content=cda_xml,
                media_type="application/xml",
                headers={"Content-Disposition": f"attachment; filename=screening_{screening_id}.cda.xml"}
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use: pdf, fhir, or cda")