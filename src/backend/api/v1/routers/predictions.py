"""Synchronous endpoint for today's model integration verification."""

from fastapi import APIRouter

from src.backend.api.v1.schemas.prediction import (
    PredictionPreviewRequest,
    PredictionPreviewResponse,
)
from src.backend.services.prediction_service import create_prediction_preview

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("/preview", response_model=PredictionPreviewResponse)
def preview_prediction(request: PredictionPreviewRequest) -> PredictionPreviewResponse:
    """Run one synchronous temporary inference without Redis or DB persistence."""
    return PredictionPreviewResponse(data=create_prediction_preview(request))
