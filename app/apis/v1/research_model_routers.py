"""Administrator-only integration endpoints; no public model activation."""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict

from app.core import config
from app.dependencies.security import get_request_user
from app.models.users import User
from app.prediction.errors import classify_ml_input_error

research_model_router = APIRouter(prefix="/research/models", tags=["Research models"])


class ResearchPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    as_of_date: date
    input: dict[str, Any]


@research_model_router.post("/{model}/predict")
async def research_predict(
    model: Literal["shared7", "shared8-waist", "first-interval", "tomorrow-rf25"],
    request: ResearchPredictionRequest,
    response: Response,
    user: Annotated[User, Depends(get_request_user)],
) -> dict:
    if not config.ML_RESEARCH_ENDPOINTS_ENABLED:
        raise HTTPException(404, detail="Research endpoints disabled")
    if not user.is_active or not user.is_admin:
        raise HTTPException(403, detail="Administrator access required")
    response.headers["Cache-Control"] = "no-store"
    # Lazy import keeps ML dependencies optional when endpoints are disabled.
    from src.ml.inference.diabetes_first_interval_survival_ensemble import (
        EnsembleArtifactUnavailableError,
        EnsembleContractError,
    )
    from src.ml.inference.diabetes_standard import ModelArtifactUnavailableError, ModelContractError
    from src.ml.inference.research_models import (
        ResearchArtifactUnavailableError,
        ResearchModelContractError,
        predict_research_model,
    )

    model_paths = {
        "shared7": config.ML_SHARED7_MODEL_URI,
        "shared8-waist": config.ML_SHARED8_MODEL_URI,
        "first-interval": config.ML_FIRST_INTERVAL_MODEL_URI,
        "tomorrow-rf25": config.ML_RF25_MODEL_URI or config.MODEL_URI,
    }
    model_path = model_paths[model]
    try:
        result = await asyncio.to_thread(
            predict_research_model,
            model,
            request.input,
            as_of_date=request.as_of_date,
            model_path=model_path,
        )
    except (ResearchArtifactUnavailableError, EnsembleArtifactUnavailableError, ModelArtifactUnavailableError) as exc:
        raise HTTPException(503, detail={"code": "ML_MODEL_UNAVAILABLE"}) from exc
    except (ResearchModelContractError, EnsembleContractError, ModelContractError) as exc:
        raise HTTPException(503, detail={"code": "ML_MODEL_CONTRACT_ERROR"}) from exc
    except ValueError as exc:
        # Do not echo health values in an error response or log.
        raise HTTPException(422, detail={"code": classify_ml_input_error(exc)}) from exc
    return {"data": result}
