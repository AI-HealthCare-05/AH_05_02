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
    {
        "code": "brisk_walk_30m",
        "title": "빠르게 걷기",
        "category": "activity",
        "daily_goal": "몸 상태에 맞춰 최대 30분",
        "description": "대화는 가능하지만 약간 숨이 차는 정도로 걷고 시간을 기록합니다.",
        "safety_copy": "통증·어지럼·심한 호흡곤란이 생기면 즉시 중단하세요.",
        "source_title": "ADA Standards of Care 2026",
        "source_url": "https://doi.org/10.2337/dc26-S005",
    },
    {
        "code": "activity_break_30m",
        "title": "30분마다 일어나기",
        "category": "activity",
        "daily_goal": "3~5분 가볍게 움직이기",
        "description": "오래 앉아 있을 때 잠깐 일어나 움직인 횟수를 기록합니다.",
        "safety_copy": "서 있기 어려우면 앉은 자세의 가벼운 움직임으로 대신하세요.",
        "source_title": "ADA Standards of Care 2026",
        "source_url": "https://doi.org/10.2337/dc26-S005",
    },
    {
        "code": "strength_twice_weekly",
        "title": "근력운동 주 2회",
        "category": "activity",
        "daily_goal": "연속되지 않은 날에 주 2회",
        "description": "몸 상태에 맞는 근력운동 수행 횟수를 기록합니다.",
        "safety_copy": "운동 제한을 안내받았다면 의료진의 지침을 우선하세요.",
        "source_title": "ADA Standards of Care 2026",
        "source_url": "https://doi.org/10.2337/dc26-S005",
    },
    {
        "code": "balance_flex_twice_weekly",
        "title": "균형·유연성 운동 주 2회",
        "category": "activity",
        "daily_goal": "스트레칭·의자운동·균형운동 주 2회",
        "description": "안전한 환경에서 균형 또는 유연성 운동 횟수를 기록합니다.",
        "safety_copy": "낙상 위험이 있다면 보호자나 전문가의 안내를 받아 진행하세요.",
        "source_title": "ADA Standards of Care 2026",
        "source_url": "https://doi.org/10.2337/dc26-S005",
    },
    {
        "code": "water_instead_sugary_drink",
        "title": "단 음료 대신 물",
        "category": "diet",
        "daily_goal": "물이나 무가당 음료 선택",
        "description": "가당 음료 대신 물 또는 무가당 음료를 선택한 횟수를 기록합니다.",
        "safety_copy": "수분 섭취 제한을 안내받았다면 의료진의 지침을 우선하세요.",
        "source_title": "ADA Standards of Care 2026",
        "source_url": "https://doi.org/10.2337/dc26-S005",
    },
    {
        "code": "vegetables_first",
        "title": "채소 먼저 먹기",
        "category": "diet",
        "daily_goal": "한 끼 이상 채소 먼저 먹기",
        "description": "한 끼 이상에서 비전분 채소를 먼저 먹었는지 체크합니다.",
        "safety_copy": "개인별 치료식이나 식사 제한이 있다면 해당 지침을 우선하세요.",
        "source_title": "대한당뇨병학회 자료",
        "source_url": "https://diabetes.or.kr/bbs/download.php?code=guide&number=1596",
    },
    {
        "code": "half_plate_vegetables",
        "title": "접시 절반 채소",
        "category": "diet",
        "daily_goal": "한 끼의 약 절반을 채소로 구성",
        "description": "채소를 충분히 포함한 식사를 했는지 간편 체크합니다.",
        "safety_copy": "개인별 치료식이나 식사 제한이 있다면 해당 지침을 우선하세요.",
        "source_title": "대한당뇨병학회 자료",
        "source_url": "https://diabetes.or.kr/bbs/download.php?code=guide&number=1596",
    },
    {
        "code": "whole_grain_choice",
        "title": "통곡물·잡곡 선택",
        "category": "diet",
        "daily_goal": "한 끼를 잡곡·통곡물·콩류로 바꾸기",
        "description": "흰밥이나 흰빵 대신 통곡물·잡곡·콩류를 선택한 식사를 기록합니다.",
        "safety_copy": "개인별 치료식이나 식사 제한이 있다면 해당 지침을 우선하세요.",
        "source_title": "Finnish Diabetes Prevention Study",
        "source_url": "https://doi.org/10.1056/NEJM200105033441801",
    },
    {
        "code": "whole_fruit_choice",
        "title": "과일은 통째로",
        "category": "diet",
        "daily_goal": "과일주스 대신 생과일 선택",
        "description": "과일주스 대신 적정량의 생과일을 선택했는지 체크합니다.",
        "safety_copy": "섭취량은 개인별 건강 상태와 의료진의 식사 지침을 우선하세요.",
        "source_title": "대한당뇨병학회 자료",
        "source_url": "https://diabetes.or.kr/bbs/download.php?code=guide&number=1596",
    },
    {
        "code": "healthy_snack_swap",
        "title": "달콤한 간식 바꾸기",
        "category": "diet",
        "daily_goal": "견과류·무가당 유제품·과일 중 선택",
        "description": "과자나 사탕 대신 선택한 간식을 기록합니다.",
        "safety_copy": "알레르기와 개인별 식사 제한을 확인하세요.",
        "source_title": "CDC PreventT2 Curriculum",
        "source_url": "https://www.cdc.gov/diabetes-prevention/php/lifestyle-change-resources/t2-curriculum.html",
    },
    {
        "code": "reduce_processed_food",
        "title": "가공식품 줄이기",
        "category": "diet",
        "daily_goal": "가공식품을 먹지 않은 하루 만들기",
        "description": "라면·햄·과자 등 가공식품을 줄였는지 체크합니다.",
        "safety_copy": "무리한 식사 제한보다 지속 가능한 작은 변화를 선택하세요.",
        "source_title": "CDC PreventT2 Curriculum",
        "source_url": "https://www.cdc.gov/diabetes-prevention/php/lifestyle-change-resources/t2-curriculum.html",
    },
    {
        "code": "slow_meal_15m",
        "title": "천천히 식사하기",
        "category": "diet",
        "daily_goal": "한 끼를 15분 이상 먹기",
        "description": "한 끼 식사에 걸린 시간을 기록합니다.",
        "safety_copy": "치료식이나 식사 방법을 안내받았다면 의료진의 지침을 우선하세요.",
        "source_title": "CDC PreventT2 Curriculum",
        "source_url": "https://www.cdc.gov/diabetes-prevention/php/lifestyle-change-resources/t2-curriculum.html",
    },
    {
        "code": "daily_meal_review",
        "title": "오늘 식사 돌아보기",
        "category": "tracking",
        "daily_goal": "하루 식사 습관 간단 기록",
        "description": "채소·통곡물·단 음료 섭취 여부를 간단히 돌아봅니다.",
        "safety_copy": "이 기록은 진단이나 영양 처방을 대신하지 않습니다.",
        "source_title": "CDC PreventT2 Curriculum",
        "source_url": "https://www.cdc.gov/diabetes-prevention/php/lifestyle-change-resources/t2-curriculum.html",
    },
    {
        "code": "sleep_7_8h",
        "title": "7~8시간 수면 기록",
        "category": "tracking",
        "daily_goal": "기상 후 수면시간 입력",
        "description": "잠든 시간과 일어난 시간을 바탕으로 수면시간을 기록합니다.",
        "safety_copy": "지속적인 수면 문제가 있다면 의료진과 상담하세요.",
        "source_title": "수면과 제2형 당뇨병 위험 메타분석",
        "source_url": "https://doi.org/10.2337/dc14-2073",
    },
    {
        "code": "smoke_free_today",
        "title": "오늘도 금연",
        "category": "tracking",
        "daily_goal": "담배와 전자담배 사용하지 않기",
        "description": "오늘 금연 실천 여부를 간편 체크합니다.",
        "safety_copy": "금연 지원이 필요하면 보건소나 의료진의 도움을 받으세요.",
        "source_title": "대한당뇨병학회 자료",
        "source_url": "https://diabetes.or.kr/bbs/download.php?code=guide&number=1596",
    },
    {
        "code": "healthy_grocery_list",
        "title": "건강한 장보기",
        "category": "tracking",
        "daily_goal": "건강한 식재료 3종 이상 준비",
        "description": "채소·통곡물·콩류·과일·저지방 단백질 중 준비한 항목을 체크합니다.",
        "safety_copy": "개인별 치료식과 알레르기를 먼저 확인하세요.",
        "source_title": "CDC PreventT2 Curriculum",
        "source_url": "https://www.cdc.gov/diabetes-prevention/php/lifestyle-change-resources/t2-curriculum.html",
    },
    {
        "code": "weekly_habit_review",
        "title": "생활습관 돌아보기",
        "category": "tracking",
        "daily_goal": "운동·식사·수면 기록 주 1회 확인",
        "description": "한 주의 생활습관 기록을 확인하고 다음 목표를 정합니다.",
        "safety_copy": "기록은 건강 상태를 판정하거나 치료 효과를 판단하기 위한 자료가 아닙니다.",
        "source_title": "CDC PreventT2 Curriculum",
        "source_url": "https://www.cdc.gov/diabetes-prevention/php/lifestyle-change-resources/t2-curriculum.html",
    },
    {
        "code": "postmeal_light_activity",
        "title": "식후 10분 가볍게 움직이기",
        "category": "activity",
        "daily_goal": "걷기 또는 가벼운 집안일 10분",
        "description": "식사 후 무리하지 않는 범위에서 가볍게 움직인 시간을 기록합니다.",
        "safety_copy": "통증·어지럼·심한 호흡곤란이 생기면 즉시 중단하세요.",
        "source_title": "ADA Standards of Care 2026",
        "source_url": "https://doi.org/10.2337/dc26-S005",
    },
    {
        "code": "activity_150m_weekly",
        "title": "주 150분 움직이기",
        "category": "activity",
        "daily_goal": "중강도 활동시간을 주간 누적으로 기록",
        "description": "한 주 동안 실천한 중강도 활동시간을 누적해 확인합니다.",
        "safety_copy": "운동 제한을 안내받았다면 의료진의 지침을 우선하세요.",
        "source_title": "ADA Standards of Care 2026",
        "source_url": "https://doi.org/10.2337/dc26-S005",
    },
    {
        "code": "walk_three_days_weekly",
        "title": "주 3일 이상 걷기",
        "category": "activity",
        "daily_goal": "걸은 날을 주 3일 이상 기록",
        "description": "걷기 활동을 실천한 날을 주간 단위로 확인합니다.",
        "safety_copy": "몸 상태에 맞는 속도와 시간으로 시작하세요.",
        "source_title": "CDC PreventT2 Curriculum",
        "source_url": "https://www.cdc.gov/diabetes-prevention/php/lifestyle-change-resources/t2-curriculum.html",
    },
    {
        "code": "unsweetened_drink_five_days",
        "title": "무가당 음료 주 5일",
        "category": "diet",
        "daily_goal": "물 또는 무가당 음료를 선택한 날 기록",
        "description": "가당 음료 대신 물이나 무가당 음료를 선택한 날을 확인합니다.",
        "safety_copy": "수분 섭취 제한을 안내받았다면 의료진의 지침을 우선하세요.",
        "source_title": "CDC PreventT2 Curriculum",
        "source_url": "https://www.cdc.gov/diabetes-prevention/php/lifestyle-change-resources/t2-curriculum.html",
    },
    {
        "code": "vegetables_five_days",
        "title": "채소 먹기 주 5일",
        "category": "diet",
        "daily_goal": "채소를 충분히 먹은 날 기록",
        "description": "채소를 포함한 식사를 한 날을 주간 단위로 확인합니다.",
        "safety_copy": "개인별 치료식이나 식사 제한이 있다면 해당 지침을 우선하세요.",
        "source_title": "CDC PreventT2 Curriculum",
        "source_url": "https://www.cdc.gov/diabetes-prevention/php/lifestyle-change-resources/t2-curriculum.html",
    },
    {
        "code": "whole_grain_three_times",
        "title": "통곡물 선택 주 3회",
        "category": "diet",
        "daily_goal": "잡곡·통곡물·콩류를 선택한 횟수 기록",
        "description": "정제 곡물 대신 통곡물·잡곡·콩류를 선택한 횟수를 확인합니다.",
        "safety_copy": "개인별 치료식이나 식사 제한이 있다면 해당 지침을 우선하세요.",
        "source_title": "Finnish Diabetes Prevention Study",
        "source_url": "https://doi.org/10.1056/NEJM200105033441801",
    },
    {
        "code": "weekly_weight_trend",
        "title": "체중 추이 확인",
        "category": "tracking",
        "daily_goal": "주 1회 같은 조건에서 기록 확인",
        "description": "체중 숫자 하나보다 일정한 조건에서 기록한 변화 추이를 확인합니다.",
        "safety_copy": "체중 기록은 진단이나 치료 효과를 판단하기 위한 자료가 아닙니다.",
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
