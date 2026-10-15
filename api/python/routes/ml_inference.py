from fastapi import APIRouter, Depends, HTTPException
from models.screening import ScreeningInput, MLResult
from services.ml_model import predict_risk, predict_risk_with_shap
from auth.clerk import get_current_user_id

router = APIRouter()


@router.post("/ml/predict", response_model=MLResult)
async def ml_predict(
    input_data: ScreeningInput,
    user_id: str = Depends(get_current_user_id),
):
    """Run ML model inference with SHAP explanations."""
    try:
        result = predict_risk_with_shap(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML inference failed: {str(e)}")


@router.post("/ml/predict-simple")
async def ml_predict_simple(
    input_data: ScreeningInput,
    user_id: str = Depends(get_current_user_id),
):
    """Simple ML prediction without SHAP (faster)."""
    try:
        result = predict_risk(input_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML inference failed: {str(e)}")