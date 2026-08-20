"""Top-level router composition for the v1 API."""

from fastapi import APIRouter

from src.backend.api.v1.routers.predictions import router as predictions_router

api_router = APIRouter()
api_router.include_router(predictions_router)
