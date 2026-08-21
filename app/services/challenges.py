from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException, status
from tortoise.transactions import in_transaction

from app.dtos.health import ChallengeCycleCreateRequest, ChallengeLogUpsertRequest
from app.models.health import Challenge, ChallengeCycle, UserChallenge
from app.models.users import User
from app.repositories.health_repository import HealthRepository

CHALLENGE_CATALOG = (
    {
        "code": "walk_after_meal_10m",
        "title": "식후 10분 천천히 걷기",
        "category": "activity",
        "daily_goal": "10분",
        "description": "식후 몸 상태에 맞춰 가볍게 걷고 수행 여부를 기록합니다.",
        "safety_copy": "통증·어지럼·호흡곤란이 있으면 중단하고 의료진과 상담하세요.",
        "source_title": "질병관리청 국가건강정보포털 당뇨병",
        "source_url": "https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5305",
    },
    {
        "code": "regular_meals_log",
        "title": "규칙적인 식사 횟수 기록하기",
        "category": "diet",
        "daily_goal": "하루 1회 기록",
        "description": "어제 먹은 끼니 수를 기록해 식사 습관을 돌아봅니다.",
        "safety_copy": "치료식이나 식사 제한을 안내받았다면 담당 의료진 지침을 우선하세요.",
        "source_title": "질병관리청 국가건강정보포털 당뇨병",
        "source_url": "https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5305",
    },
    {
        "code": "activity_check",
        "title": "오늘의 신체활동 확인하기",
        "category": "activity",
        "daily_goal": "하루 1회 확인",
        "description": "무리하지 않은 범위에서 활동했는지 간단히 체크합니다.",
        "safety_copy": "개인의 질환·통증·운동 제한이 있다면 의료진의 안내를 우선하세요.",
        "source_title": "질병관리청 국가건강정보포털 당뇨병",
        "source_url": "https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5305",
    },
)


def challenge_payload(item: Challenge) -> dict[str, object]:
    return {
        "challenge_id": item.id,
        "code": item.code,
        "title": item.title,
        "category": item.category,
        "daily_goal": item.daily_goal,
        "description": item.description,
        "safety": item.safety_copy,
        "source": {"title": item.source_title, "url": item.source_url},
    }


class ChallengeService:
    def __init__(self) -> None:
        self.repo = HealthRepository()

    async def ensure_catalog(self) -> list[Challenge]:
        for values in CHALLENGE_CATALOG:
            await Challenge.update_or_create(defaults={**values, "is_active": True}, code=values["code"])
        return list((await self.repo.challenge_map()).values())

    async def recommendations(self, user: User, prediction_id: int | None) -> dict[str, object]:
        if prediction_id is not None:
            prediction = await self.repo.get_prediction(prediction_id, user.id)
            if prediction is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="예측 결과를 찾을 수 없습니다.")
        open_action = await self.repo.open_follow_up(user.id)
        items = await self.ensure_catalog()
        return {
            "items": [challenge_payload(item) for item in items],
            "recommendation_type": "reviewed_general_template",
            "personalized": False,
            "medical_guidance_required_first": open_action is not None,
            "notice": "치료가 아닌 일반 건강 실천입니다. 몸 상태와 의료진 지침을 우선하세요.",
        }

    async def create_cycle(self, user: User, request: ChallengeCycleCreateRequest) -> ChallengeCycle:
        if await self.repo.active_consent(user.id) is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="건강정보 처리 동의가 필요합니다.")
        eligibility = await self.repo.latest_eligibility(user.id)
        if eligibility is None or eligibility.has_diabetes_diagnosis or eligibility.has_urgent_warning_sign:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="현재는 챌린지보다 의료기관 안내가 우선입니다."
            )
        if await self.repo.open_follow_up(user.id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error_code": "FOLLOW_UP_ACKNOWLEDGEMENT_REQUIRED",
                    "message": "의료기관 안내를 먼저 확인해 주세요.",
                },
            )
        if await self.repo.active_cycle(user.id) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="진행 중인 4주 챌린지가 이미 있습니다.")
        challenges = await self.repo.challenge_map(request.challenge_ids)
        if len(challenges) != len(request.challenge_ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="선택할 수 없는 챌린지가 있습니다."
            )
        if request.prediction_id is not None and await self.repo.get_prediction(request.prediction_id, user.id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="예측 결과를 찾을 수 없습니다.")
        end_date = request.start_date + timedelta(days=27)
        cycle_number = await self.repo.count_cycles(user.id) + 1
        cycle_status = "active" if request.start_date <= date.today() else "scheduled"
        async with in_transaction():
            cycle = await ChallengeCycle.create(
                user_id=user.id,
                prediction_id=request.prediction_id,
                cycle_number=cycle_number,
                start_date=request.start_date,
                end_date=end_date,
                status=cycle_status,
            )
            for challenge_id in request.challenge_ids:
                await UserChallenge.create(user_id=user.id, cycle_id=cycle.id, challenge_id=challenge_id)
        return cycle

    async def upsert_log(
        self,
        user: User,
        user_challenge_id: int,
        log_date: date,
        request: ChallengeLogUpsertRequest,
    ) -> object:
        if log_date > date.today():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="미래 날짜는 기록할 수 없습니다."
            )
        user_challenge = await self.repo.get_user_challenge(user_challenge_id, user.id)
        if user_challenge is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="선택한 챌린지를 찾을 수 없습니다.")
        cycle = await self.repo.get_cycle(user_challenge.cycle_id, user.id)
        if cycle is None or cycle.status not in {"active", "scheduled"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="진행 중인 챌린지 사이클이 아닙니다.")
        if log_date < cycle.start_date or log_date > cycle.end_date:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="챌린지 기간 밖의 날짜입니다.")
        return await self.repo.upsert_log(
            user_challenge_id=user_challenge_id,
            user_id=user.id,
            log_date=log_date,
            values=request.model_dump(),
        )

    async def cycle_payload(self, cycle: ChallengeCycle, user_id: int) -> dict[str, object]:
        user_challenges = await self.repo.list_user_challenges(cycle.id, user_id)
        challenge_map = await self.repo.challenge_map([item.challenge_id for item in user_challenges])
        logs = await self.repo.logs_for_cycle(cycle.id, user_id)
        planned = len(user_challenges) * max(0, min((date.today() - cycle.start_date).days + 1, 28))
        completed = sum(1 for item in logs if item.is_completed)
        return {
            "cycle_id": cycle.id,
            "cycle_number": cycle.cycle_number,
            "start_date": cycle.start_date,
            "end_date": cycle.end_date,
            "status": cycle.status,
            "ended_reason": cycle.ended_reason,
            "completion_rate": round(completed / planned * 100, 1) if planned else 0.0,
            "user_challenges": [
                {
                    "user_challenge_id": item.id,
                    **challenge_payload(challenge_map[item.challenge_id]),
                }
                for item in user_challenges
                if item.challenge_id in challenge_map
            ],
        }

    async def stop_cycle(self, user: User, cycle_id: int, reason: str) -> ChallengeCycle:
        cycle = await self.repo.get_cycle(cycle_id, user.id)
        if cycle is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="챌린지 사이클을 찾을 수 없습니다.")
        if cycle.status in {"completed", "terminated", "stopped"}:
            return cycle
        cycle.status = "stopped"
        cycle.ended_reason = reason
        await cycle.save(update_fields=["status", "ended_reason", "updated_at"])
        return cycle

    async def acknowledge_follow_up(self, user: User, action_id: int) -> object:
        item = await self.repo.get_follow_up(action_id, user.id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="의료기관 안내를 찾을 수 없습니다.")
        return await self.repo.acknowledge_follow_up(item, datetime.now(UTC))
