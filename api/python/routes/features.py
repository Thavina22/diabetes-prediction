from fastapi import APIRouter

from services.feature_flags import get_all_flags

router = APIRouter()


@router.get("/features")
async def list_features():
    """Effective feature flags (code defaults overridden by the DB).

    Public — flags carry no sensitive data and are fetched at app load.
    """
    return {"flags": await get_all_flags()}
