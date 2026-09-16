from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.apis.responses import envelope
from app.dependencies.security import get_request_user
from app.dtos.health import FeedbackCreateRequest
from app.models.users import User
from app.repositories.health_repository import HealthRepository

feedback_router = APIRouter(prefix="/feedback", tags=["Feedback"])


@feedback_router.post("", status_code=status.HTTP_201_CREATED)
async def create_feedback(
    request: FeedbackCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
) -> dict[str, object]:
    repo = HealthRepository()
    if request.prediction_id is not None and await repo.get_prediction(request.prediction_id, user.id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="예측 결과를 찾을 수 없습니다.")
    item = await repo.create_feedback(user_id=user.id, **request.model_dump())
    return envelope({"feedback_id": item.id, "created_at": item.created_at})


@feedback_router.get("")
async def list_feedback(user: Annotated[User, Depends(get_request_user)]) -> dict[str, object]:
    items = await HealthRepository().list_feedback(user.id)
    return envelope(
        {
            "items": [
                {
                    "feedback_id": item.id,
                    "context_type": item.context_type,
                    "prediction_id": item.prediction_id,
                    "recommendation_id": item.recommendation_id,
                    "rating": item.rating,
                    "comment": item.comment,
                    "created_at": item.created_at,
                }
                for item in items
            ]
        }
    )
