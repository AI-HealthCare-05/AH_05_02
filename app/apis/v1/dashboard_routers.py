from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends

from app.apis.responses import envelope
from app.apis.v1.prediction_routers import prediction_payload
from app.dependencies.security import get_request_user
from app.models.users import User
from app.repositories.health_repository import HealthRepository
from app.services import challenge_v2
from app.services.challenges import ChallengeService

dashboard_router = APIRouter(tags=["Dashboard and guidance"])

DASHBOARD_DISCLAIMER = "위험 범주와 챌린지 수행률은 진단, 질병의 호전 또는 치료 효과를 의미하지 않습니다."


@dashboard_router.get("/dashboard/summary")
async def dashboard_summary(user: Annotated[User, Depends(get_request_user)]) -> dict[str, object]:
    repo = HealthRepository()
    prediction = await repo.latest_prediction(user.id)
    cycle = await repo.active_cycle(user.id)
    follow_up = await repo.open_follow_up(user.id)
    cycle_data = await ChallengeService().cycle_payload(cycle, user.id) if cycle is not None else None
    risk_card = prediction_payload(prediction) if prediction is not None else None
    return envelope(
        {
            "risk_cards": [] if risk_card is None else [risk_card],
            "daily_challenge_v2": await challenge_v2.dashboard_snapshot(user),
            "current_cycle": cycle_data,
            "next_action": None
            if follow_up is None
            else {
                "action_id": follow_up.id,
                "type": follow_up.action_type,
                "reason_code": follow_up.reason_code,
                "priority": follow_up.priority,
                "message": "생활습관 챌린지보다 의료기관의 확인을 먼저 권합니다.",
            },
            "risk_change": None,
            "risk_change_notice": "검증 전 점수를 개선율이나 치료 효과로 비교하지 않습니다.",
            "disclaimer": DASHBOARD_DISCLAIMER,
        }
    )


@dashboard_router.get("/dashboard/challenge-progress")
async def challenge_progress(user: Annotated[User, Depends(get_request_user)]) -> dict[str, object]:
    repo = HealthRepository()
    v2_progress = await challenge_v2.progress_summary(user)
    cycle = await repo.active_cycle(user.id)
    if cycle is None:
        return envelope({"cycle": None, "recent_7_days": {"completed": 0, "planned": 0}, "four_weeks": None, "challenge_v2": v2_progress})
    logs = await repo.logs_for_cycle(cycle.id, user.id)
    user_challenges = await repo.list_user_challenges(cycle.id, user.id)
    today = date.today()
    recent_start = max(cycle.start_date, today - timedelta(days=6))
    recent_logs = [item for item in logs if recent_start <= item.log_date <= today]
    recent_days = max(0, (min(today, cycle.end_date) - recent_start).days + 1)
    recent_planned = recent_days * len(user_challenges)
    total_days = max(0, min((today - cycle.start_date).days + 1, 28))
    total_planned = total_days * len(user_challenges)
    return envelope(
        {
            "cycle_id": cycle.id,
            "challenge_v2": v2_progress,
            "recent_7_days": {
                "completed": sum(1 for item in recent_logs if item.is_completed),
                "planned": recent_planned,
            },
            "four_weeks": {
                "completed": sum(1 for item in logs if item.is_completed),
                "planned_to_date": total_planned,
                "completion_rate": round(sum(1 for item in logs if item.is_completed) / total_planned * 100, 1)
                if total_planned
                else 0.0,
            },
            "notice": "수행률은 질병의 호전이나 치료 효과를 의미하지 않습니다.",
        }
    )


@dashboard_router.get("/follow-up-actions")
async def list_follow_up_actions(user: Annotated[User, Depends(get_request_user)]) -> dict[str, object]:
    items = await HealthRepository().list_follow_ups(user.id)
    return envelope(
        {
            "items": [
                {
                    "action_id": item.id,
                    "trigger_source": item.trigger_source,
                    "trigger_entity_id": item.trigger_entity_id,
                    "action_type": item.action_type,
                    "reason_code": item.reason_code,
                    "priority": item.priority,
                    "acknowledged_at": item.acknowledged_at,
                    "created_at": item.created_at,
                    "message": "검사·치료·복약은 담당 의료진의 지침을 따라주세요.",
                }
                for item in items
            ]
        }
    )


@dashboard_router.patch("/follow-up-actions/{action_id}/acknowledge")
async def acknowledge_follow_up(
    action_id: int,
    user: Annotated[User, Depends(get_request_user)],
) -> dict[str, object]:
    item = await ChallengeService().acknowledge_follow_up(user, action_id)
    return envelope({"action_id": item.id, "acknowledged_at": item.acknowledged_at})


@dashboard_router.get("/recommendations")
async def reviewed_recommendations() -> dict[str, object]:
    items = await ChallengeService().ensure_catalog()
    return envelope(
        {
            "type": "reviewed_general_health_templates",
            "personalized_medical_advice": False,
            "items": [
                {
                    "title": item.title,
                    "description": item.description,
                    "safety": item.safety_copy,
                    "source": {"title": item.source_title, "url": item.source_url},
                }
                for item in items
            ],
            "medication_notice": "복용 중인 약을 임의로 시작·중단하거나 용량을 변경하지 마세요.",
        }
    )
