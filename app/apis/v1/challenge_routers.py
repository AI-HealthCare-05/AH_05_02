from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.apis.responses import envelope
from app.dependencies.security import get_request_user
from app.dtos.health import (
    ChallengeCycleCreateRequest,
    ChallengeCycleStatusRequest,
    ChallengeLogUpsertRequest,
)
from app.models.users import User
from app.repositories.health_repository import HealthRepository
from app.services.challenges import ChallengeService, challenge_payload

challenge_router = APIRouter(tags=["Challenges"])


@challenge_router.get("/challenges")
async def list_challenges() -> dict[str, object]:
    items = await ChallengeService().ensure_catalog()
    return envelope({"items": [challenge_payload(item) for item in items]})


@challenge_router.get("/challenge-recommendations")
async def challenge_recommendations(
    user: Annotated[User, Depends(get_request_user)],
    prediction_id: int | None = Query(default=None),
) -> dict[str, object]:
    return envelope(await ChallengeService().recommendations(user, prediction_id))


@challenge_router.post("/challenge-cycles", status_code=status.HTTP_201_CREATED)
async def create_challenge_cycle(
    request: ChallengeCycleCreateRequest,
    user: Annotated[User, Depends(get_request_user)],
) -> dict[str, object]:
    service = ChallengeService()
    cycle = await service.create_cycle(user, request)
    return envelope(await service.cycle_payload(cycle, user.id))


@challenge_router.get("/challenge-cycles/current")
async def current_challenge_cycle(user: Annotated[User, Depends(get_request_user)]) -> dict[str, object]:
    cycle = await HealthRepository().active_cycle(user.id)
    if cycle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="진행 중인 챌린지가 없습니다.")
    return envelope(await ChallengeService().cycle_payload(cycle, user.id))


@challenge_router.get("/challenge-cycles/{cycle_id}")
async def read_challenge_cycle(
    cycle_id: int,
    user: Annotated[User, Depends(get_request_user)],
) -> dict[str, object]:
    cycle = await HealthRepository().get_cycle(cycle_id, user.id)
    if cycle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="챌린지 사이클을 찾을 수 없습니다.")
    return envelope(await ChallengeService().cycle_payload(cycle, user.id))


@challenge_router.patch("/challenge-cycles/{cycle_id}/status")
async def update_challenge_cycle_status(
    cycle_id: int,
    request: ChallengeCycleStatusRequest,
    user: Annotated[User, Depends(get_request_user)],
) -> dict[str, object]:
    service = ChallengeService()
    cycle = await service.stop_cycle(user, cycle_id, request.reason)
    return envelope(await service.cycle_payload(cycle, user.id))


@challenge_router.put("/user-challenges/{user_challenge_id}/logs/{log_date}")
async def upsert_challenge_log(
    user_challenge_id: int,
    log_date: date,
    request: ChallengeLogUpsertRequest,
    user: Annotated[User, Depends(get_request_user)],
) -> dict[str, object]:
    item = await ChallengeService().upsert_log(user, user_challenge_id, log_date, request)
    return envelope(
        {
            "log_id": item.id,
            "user_challenge_id": item.user_challenge_id,
            "log_date": item.log_date,
            "is_completed": item.is_completed,
            "value": item.value,
            "source": item.source,
            "note": item.note,
            "updated_at": item.updated_at,
        }
    )


@challenge_router.get("/user-challenges/{user_challenge_id}/logs")
async def list_challenge_logs(
    user_challenge_id: int,
    user: Annotated[User, Depends(get_request_user)],
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
) -> dict[str, object]:
    repo = HealthRepository()
    if await repo.get_user_challenge(user_challenge_id, user.id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="선택한 챌린지를 찾을 수 없습니다.")
    items = await repo.logs_for_user_challenge(user_challenge_id, user.id, start_date, end_date)
    return envelope(
        {
            "items": [
                {
                    "log_id": item.id,
                    "log_date": item.log_date,
                    "is_completed": item.is_completed,
                    "value": item.value,
                    "source": item.source,
                    "note": item.note,
                }
                for item in items
            ]
        }
    )
