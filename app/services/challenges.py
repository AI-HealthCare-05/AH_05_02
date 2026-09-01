from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException, UploadFile, status
from tortoise.transactions import in_transaction

from app.core import config
from app.dtos.health import ChallengeCycleCreateRequest, ChallengeLogUpsertRequest, ChallengeVerificationCreateRequest
from app.models.health import Challenge, ChallengeCycle, UserChallenge
from app.models.users import User
from app.repositories.game_repository import GameRepository
from app.repositories.health_repository import HealthRepository
from app.repositories.wellness_repository import WellnessRepository
from app.vision.food_vision import FoodVisionError, get_food_vision_provider, sha256_digest

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
    {
        "code": "weekly_weight_log",
        "title": "일주일에 한 번 체중 기록하기",
        "category": "tracking",
        "daily_goal": "주 1회 기록",
        "description": "같은 조건에서 체중을 기록하고 장기적인 생활습관 변화를 확인합니다.",
        "safety_copy": "단기간의 체중 변화만으로 건강 상태나 치료 효과를 판단하지 마세요.",
        "source_title": "CDC PreventT2 Curriculum",
        "source_url": "https://www.cdc.gov/diabetes-prevention/php/lifestyle-change-resources/t2-curriculum.html",
    },
    {
        "code": "two_minute_activity_break",
        "title": "오래 앉아 있을 때 2분 움직이기",
        "category": "activity",
        "daily_goal": "하루 1회",
        "description": "오래 앉아 있었다면 몸 상태에 맞춰 잠깐 일어나 가볍게 움직입니다.",
        "safety_copy": "통증·어지럼·호흡곤란이 있으면 중단하고 의료진과 상담하세요.",
        "source_title": "CDC PreventT2 Curriculum",
        "source_url": "https://www.cdc.gov/diabetes-prevention/php/lifestyle-change-resources/t2-curriculum.html",
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
        self.wellness_repo = WellnessRepository()

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
        checkup = await self.repo.latest_checkup(user.id)
        reasons: dict[str, str] = {}
        priority_codes: list[str] = []
        if checkup is not None:
            if not checkup.regular_exercise:
                priority_codes.extend(["walk_after_meal_10m", "two_minute_activity_break"])
                reasons["walk_after_meal_10m"] = (
                    "최근 입력에서 규칙적인 운동을 하지 않는 것으로 확인되어 우선 제안합니다."
                )
                reasons["two_minute_activity_break"] = "작게 시작할 수 있는 활동 목표로 제안합니다."
            if checkup.meal_count_yesterday != 3:
                priority_codes.append("regular_meals_log")
                reasons["regular_meals_log"] = "최근 식사 횟수를 바탕으로 식사 패턴 확인을 제안합니다."
            if checkup.bmi >= 25:
                priority_codes.append("weekly_weight_log")
                reasons["weekly_weight_log"] = "체중 변화가 아닌 생활습관 기록을 위해 주 1회 기록을 제안합니다."
        item_by_code = {item.code: item for item in items}
        ordered_codes = list(dict.fromkeys(priority_codes + [item.code for item in items]))
        ranked = [item_by_code[code] for code in ordered_codes if code in item_by_code][:3]
        return {
            "items": [
                {
                    **challenge_payload(item),
                    "recommendation_reason": reasons.get(item.code, "일반 건강 실천 항목입니다."),
                }
                for item in ranked
            ],
            "recommendation_type": "rule_based_reviewed_template",
            "personalized": checkup is not None,
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
        cycle = await self.refresh_cycle_status(cycle)
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

    async def refresh_cycle_status(self, cycle: ChallengeCycle) -> ChallengeCycle:
        today = date.today()
        next_status = cycle.status
        if cycle.status == "scheduled" and cycle.start_date <= today <= cycle.end_date:
            next_status = "active"
        elif cycle.status in {"scheduled", "active"} and today > cycle.end_date:
            next_status = "completed"
        if next_status != cycle.status:
            cycle.status = next_status
            await cycle.save(update_fields=["status", "updated_at"])
        return cycle

    async def create_verification(
        self, user: User, user_challenge_id: int, request: ChallengeVerificationCreateRequest
    ) -> dict[str, object]:
        if request.verification_date > date.today():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="미래 날짜는 인증할 수 없습니다."
            )
        user_challenge = await self.repo.get_user_challenge(user_challenge_id, user.id)
        if user_challenge is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="선택한 챌린지를 찾을 수 없습니다.")
        cycle = await self.repo.get_cycle(user_challenge.cycle_id, user.id)
        if cycle is None or cycle.status not in {"active", "scheduled"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="진행 중인 챌린지 사이클이 아닙니다.")
        if request.verification_date < cycle.start_date or request.verification_date > cycle.end_date:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="챌린지 기간 밖의 날짜입니다.")
        values = request.model_dump(exclude={"verification_date"})
        values["review_status"] = "accepted"
        async with in_transaction():
            verification = await self.repo.upsert_verification(
                user_challenge_id=user_challenge_id,
                user_id=user.id,
                verification_date=request.verification_date,
                values=values,
            )
            await self.repo.record_verification_event(verification)
            await self.repo.upsert_log(
                user_challenge_id=user_challenge_id,
                user_id=user.id,
                log_date=request.verification_date,
                values={
                    "is_completed": True,
                    "value": 1,
                    "source": "self_report",
                    "note": f"{request.verification_type} verification accepted",
                },
            )
        return {
            "verification_id": verification.id,
            "user_challenge_id": verification.user_challenge_id,
            "verification_date": verification.verification_date,
            "verification_type": verification.verification_type,
            "review_status": verification.review_status,
            "challenge_completed": True,
        }

    async def create_meal_photo_verification(
        self, user: User, user_challenge_id: int, verification_date: date, file: UploadFile
    ) -> dict[str, object]:
        """식사 사진을 업로드하면 AI가 채소 포함 여부만 자동으로 판별해 챌린지 인증을 남깁니다.

        칼로리·영양소·치료 효과는 계산하지 않습니다(REQ-CV-001). 업로드된 원본 이미지 바이트는
        분석 직후 폐기하며 서버에 저장하지 않고, 판별 결과와 SHA-256 다이제스트만 남깁니다.
        """
        if verification_date > date.today():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="미래 날짜는 인증할 수 없습니다."
            )
        user_challenge = await self.repo.get_user_challenge(user_challenge_id, user.id)
        if user_challenge is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="선택한 챌린지를 찾을 수 없습니다.")
        cycle = await self.repo.get_cycle(user_challenge.cycle_id, user.id)
        if cycle is None or cycle.status not in {"active", "scheduled"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="진행 중인 챌린지 사이클이 아닙니다.")
        if verification_date < cycle.start_date or verification_date > cycle.end_date:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="챌린지 기간 밖의 날짜입니다.")

        content_type = file.content_type or ""
        if not content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="이미지 파일만 업로드할 수 있습니다."
            )
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="빈 파일입니다.")
        if len(image_bytes) > config.FOOD_PHOTO_MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"사진 용량은 {config.FOOD_PHOTO_MAX_BYTES // (1024 * 1024)}MB 이하만 업로드할 수 있습니다.",
            )

        digest = sha256_digest(image_bytes)
        provider = get_food_vision_provider()
        try:
            result = await provider.analyze(image_bytes, content_type, file.filename or "meal.jpg")
        except FoodVisionError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        finally:
            del image_bytes  # 분석 후 원본 이미지는 저장하지 않고 즉시 폐기합니다.

        review_status = (
            "accepted"
            if result.contains_vegetable is True
            and (result.vegetable_confidence is None or result.vegetable_confidence >= 0.5)
            else "needs_review"
        )

        analysis = await self.wellness_repo.create_food_analysis(
            user_id=user.id,
            image_name=file.filename or "meal.jpg",
            provider=result.provider_kind,
            predicted_category=result.predicted_category,
            confidence=result.vegetable_confidence,
            contains_vegetable=result.contains_vegetable,
            vegetable_confidence=result.vegetable_confidence,
            vegetable_ratio_percent=result.vegetable_ratio_percent,
            detected_items=result.detected_items,
            user_challenge_id=user_challenge_id,
            verification_date=verification_date,
            status="auto_analyzed",
        )

        challenge_completed = review_status == "accepted"
        async with in_transaction():
            verification = await self.repo.upsert_verification(
                user_challenge_id=user_challenge_id,
                user_id=user.id,
                verification_date=verification_date,
                values={
                    "verification_type": "photo",
                    "evidence_ref": f"food_vision:{result.provider_kind}:{analysis.id}",
                    "evidence_digest": digest,
                    "review_status": review_status,
                },
            )
            await self.repo.record_verification_event(verification)
            if challenge_completed:
                await self.repo.upsert_log(
                    user_challenge_id=user_challenge_id,
                    user_id=user.id,
                    log_date=verification_date,
                    values={
                        "is_completed": True,
                        "value": 1,
                        "source": "photo_vegetable_auto",
                        "note": f"AI 채소 포함 자동 판별: {result.predicted_category}",
                    },
                )

        return {
            "analysis_id": analysis.id,
            "verification_id": verification.id,
            "user_challenge_id": verification.user_challenge_id,
            "verification_date": verification.verification_date,
            "provider": result.provider_kind,
            "predicted_category": result.predicted_category,
            "contains_vegetable": result.contains_vegetable,
            "vegetable_confidence": result.vegetable_confidence,
            "vegetable_ratio_percent": result.vegetable_ratio_percent,
            "detected_items": result.detected_items,
            "review_status": review_status,
            "challenge_completed": challenge_completed,
            "notice": (
                "AI가 사진에서 채소 포함 여부와 대략적인 시각적 비율만 자동으로 판별했습니다. "
                "칼로리·영양소·치료 효과는 계산하지 않으며, 업로드한 사진 원본은 분석 후 저장하지 않습니다."
                if challenge_completed
                else "사진에서 채소를 확인하지 못했습니다. 채소가 잘 보이도록 다시 촬영해 주세요."
            ),
        }

    async def daily_reward_status(self, user: User, reward_date: date) -> dict[str, object]:
        cycle = await self.repo.cycle_for_date(user.id, reward_date)
        selected = await self.repo.list_user_challenges(cycle.id, user.id) if cycle else []
        completed = await self.repo.completed_challenge_ids_for_date(cycle.id, user.id, reward_date) if cycle else set()
        reward = await self.repo.get_daily_reward(user.id, reward_date)
        # A cycle isn't required to have exactly 3 challenges (challenge-selection only
        # enforces "1 or more"), so gating eligibility on len(selected) == 3 permanently
        # locked the daily reward out for any user who picked a different count. Eligibility
        # should mean "finished everything picked for today", whatever that count is.
        eligible = bool(cycle and len(selected) > 0 and len(completed) == len(selected))
        return {
            "reward_date": reward_date,
            "completed": len(completed),
            "required": len(selected),
            "eligible": eligible,
            "claimed": reward is not None,
            "carrot_amount": reward.carrot_amount if reward else 55,
        }

    async def claim_daily_reward(self, user: User, reward_date: date) -> dict[str, object]:
        if reward_date > date.today():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="미래 날짜의 보상은 받을 수 없습니다."
            )
        reward_status = await self.daily_reward_status(user, reward_date)
        if not reward_status["eligible"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="오늘의 챌린지 3개를 모두 완료해야 합니다."
            )
        async with in_transaction():
            reward, created = await self.repo.claim_daily_reward(user.id, reward_date, 55)
            transaction, credited = await GameRepository().credit(
                user.id,
                reward.carrot_amount,
                "daily_challenge_reward",
                str(reward.id),
                f"daily-reward:{user.id}:{reward_date.isoformat()}",
            )
        return {
            "reward_id": reward.id,
            "reward_date": reward.reward_date,
            "carrot_amount": reward.carrot_amount,
            "claimed": True,
            "already_claimed": not created,
            "credited": credited,
            "carrot_balance": transaction.balance_after,
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
