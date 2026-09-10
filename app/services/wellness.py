from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException, status

from app.dtos.wellness import (
    FoodAnalysisConfirmRequest,
    FoodAnalysisRequest,
    NotificationPreferenceRequest,
    OcrDraftRequest,
    WearableConnectionRequest,
    WearableImportRequest,
)
from app.models.users import User
from app.repositories.health_repository import HealthRepository
from app.repositories.wellness_repository import WellnessRepository

ALLOWED_OCR_FIELDS = {
    "checkup_date",
    "height_cm",
    "weight_kg",
    "waist_cm",
    "systolic_bp",
    "diastolic_bp",
}

FOOD_KEYWORDS = {
    "곡류": ("rice", "bap", "bread", "noodle", "밥", "빵", "면"),
    "채소": ("vegetable", "salad", "greens", "채소", "샐러드"),
    "과일": ("fruit", "apple", "banana", "과일", "사과", "바나나"),
    "단백질": ("meat", "fish", "egg", "tofu", "고기", "생선", "달걀", "두부"),
    "유제품": ("milk", "yogurt", "cheese", "우유", "요거트", "치즈"),
}


class WellnessService:
    def __init__(self) -> None:
        self.repo = WellnessRepository()
        self.health_repo = HealthRepository()

    async def connect_wearable(self, user: User, request: WearableConnectionRequest) -> dict[str, object]:
        item = await self.repo.connect_wearable(user.id, request.provider, request.scopes)
        return {
            "connection_id": item.id,
            "provider": item.provider,
            "status": item.status,
            "scopes": item.scopes,
            "mode": "development_adapter" if item.provider == "development_mock" else "manual_file_import",
            "notice": "실제 제조사 계정 연동 전 단계입니다. 가져온 값은 사용자가 확인한 생활기록으로만 사용합니다.",
        }

    async def wearable_connections(self, user: User) -> dict[str, object]:
        items = await self.repo.wearable_connections(user.id)
        return {
            "items": [
                {
                    "connection_id": item.id,
                    "provider": item.provider,
                    "status": item.status,
                    "scopes": item.scopes,
                }
                for item in items
            ]
        }

    async def import_wearable(self, user: User, request: WearableImportRequest) -> dict[str, object]:
        connection = await self.repo.wearable_connection(request.connection_id, user.id)
        if connection is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="활성 웨어러블 연결을 찾을 수 없습니다.")
        today = date.today()
        if any(item.summary_date > today for item in request.items):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="미래 날짜의 기록은 가져올 수 없습니다."
            )
        if any(item.summary_date < today - timedelta(days=365) for item in request.items):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="최근 1년 이내 기록만 가져올 수 있습니다."
            )
        summaries = []
        auto_logged = []
        cycle = await self.health_repo.active_cycle(user.id)
        selected = await self.health_repo.list_user_challenges(cycle.id, user.id) if cycle else []
        catalog = await self.health_repo.challenge_map([item.challenge_id for item in selected]) if selected else {}
        for values in request.items:
            item = await self.repo.upsert_daily_summary(
                user_id=user.id,
                connection_id=connection.id,
                source=connection.provider,
                quality="user_confirmed",
                **values.model_dump(),
            )
            summaries.append(item.id)
            if cycle and cycle.start_date <= values.summary_date <= cycle.end_date:
                for user_challenge in selected:
                    challenge = catalog.get(user_challenge.challenge_id)
                    if (
                        challenge
                        and challenge.code == "activity_check"
                        and ((values.active_minutes or 0) >= 10 or (values.steps or 0) >= 1_000)
                    ):
                        await self.health_repo.upsert_log(
                            user_challenge_id=user_challenge.id,
                            user_id=user.id,
                            log_date=values.summary_date,
                            values={
                                "is_completed": True,
                                "value": float(values.active_minutes or values.steps or 0),
                                "source": "wearable",
                                "note": "사용자가 확인한 웨어러블 일일 요약에서 자동 기록",
                            },
                        )
                        auto_logged.append({"user_challenge_id": user_challenge.id, "log_date": values.summary_date})
        return {
            "imported_count": len(summaries),
            "auto_logged_challenges": auto_logged,
            "notice": "걸음 수만으로 식후 걷기 여부를 추정하지 않습니다. 명확히 대응되는 활동 확인 챌린지만 자동 기록합니다.",
        }

    async def wearable_summaries(self, user: User, start: date, end: date) -> dict[str, object]:
        if end < start or (end - start).days > 31:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="조회 기간은 최대 31일입니다.")
        items = await self.repo.daily_summaries(user.id, start, end)
        return {
            "period": {"start_date": start, "end_date": end},
            "items": [
                {
                    "summary_date": item.summary_date,
                    "steps": item.steps,
                    "active_minutes": item.active_minutes,
                    "sleep_minutes": item.sleep_minutes,
                    "resting_heart_rate": item.resting_heart_rate,
                    "source": item.source,
                    "quality": item.quality,
                }
                for item in items
            ],
        }

    async def food_analysis(self, user: User, request: FoodAnalysisRequest) -> dict[str, object]:
        normalized = request.image_name.casefold()
        matches = [category for category, words in FOOD_KEYWORDS.items() if any(word in normalized for word in words)]
        category = matches[0] if len(matches) == 1 else "확인불가"
        confidence = 0.55 if category != "확인불가" else None
        item = await self.repo.create_food_analysis(
            user_id=user.id,
            image_name=request.image_name,
            predicted_category=category,
            confidence=confidence,
        )
        return {
            "analysis_id": item.id,
            "provider": item.provider,
            "predicted_category": item.predicted_category,
            "confidence": item.confidence,
            "status": item.status,
            "requires_user_confirmation": True,
            "notice": "개발용 분류 어댑터 결과입니다. 영양소·열량·치료 효과를 판정하지 않으며 반드시 사용자가 확인해야 합니다.",
        }

    async def confirm_food(
        self, user: User, analysis_id: int, request: FoodAnalysisConfirmRequest
    ) -> dict[str, object]:
        item = await self.repo.food_analysis(analysis_id, user.id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="식단 분석 기록을 찾을 수 없습니다.")
        item.confirmed_category = request.confirmed_category
        item.status = "user_confirmed"
        item.confirmed_at = datetime.now(UTC)
        await item.save(update_fields=["confirmed_category", "status", "confirmed_at"])
        return {"analysis_id": item.id, "status": item.status, "confirmed_category": item.confirmed_category}

    async def ocr_draft(self, user: User, request: OcrDraftRequest) -> dict[str, object]:
        filtered = {key: value for key, value in request.extracted_fields.items() if key in ALLOWED_OCR_FIELDS}
        item = await self.repo.create_ocr_draft(
            user_id=user.id,
            document_name=request.document_name,
            extracted_fields=filtered,
        )
        return {
            "draft_id": item.id,
            "provider": item.provider,
            "extracted_fields": filtered,
            "ignored_fields": sorted(set(request.extracted_fields) - ALLOWED_OCR_FIELDS),
            "status": item.status,
            "requires_user_confirmation": True,
            "notice": "OCR 초안은 건강검진 기록에 자동 저장되지 않습니다. 원문과 대조해 확인해야 합니다.",
        }

    async def confirm_ocr(self, user: User, draft_id: int) -> dict[str, object]:
        item = await self.repo.ocr_draft(draft_id, user.id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OCR 초안을 찾을 수 없습니다.")
        item.status = "user_confirmed_not_saved"
        item.confirmed_at = datetime.now(UTC)
        await item.save(update_fields=["status", "confirmed_at"])
        return {
            "draft_id": item.id,
            "status": item.status,
            "extracted_fields": item.extracted_fields,
            "next_action": "건강정보 입력 화면에서 값을 다시 확인한 뒤 제출하세요.",
        }

    async def notification_preferences(self, user: User) -> dict[str, object]:
        item = await self.repo.notification_preferences(user.id)
        return self._preference_payload(item)

    async def update_notification_preferences(
        self, user: User, request: NotificationPreferenceRequest
    ) -> dict[str, object]:
        item = await self.repo.update_notification_preferences(user.id, request.model_dump())
        return self._preference_payload(item)

    @staticmethod
    def _preference_payload(item: object) -> dict[str, object]:
        return {
            "in_app_enabled": item.in_app_enabled,
            "challenge_reminder_enabled": item.challenge_reminder_enabled,
            "weekly_report_enabled": item.weekly_report_enabled,
            "quiet_hours": {"start": item.quiet_start_hour, "end": item.quiet_end_hour},
            "notice": "현재는 웹 내부 알림만 지원하며 문자·푸시 알림은 전송하지 않습니다.",
        }

    async def notifications(self, user: User) -> dict[str, object]:
        preference = await self.repo.notification_preferences(user.id)
        if not preference.in_app_enabled:
            return {"items": [], "notice": "웹 내부 알림이 꺼져 있습니다."}
        cycle = await self.health_repo.active_cycle(user.id)
        items = []
        if cycle and preference.challenge_reminder_enabled:
            items.append(
                {
                    "notification_id": f"challenge-{cycle.id}-{date.today().isoformat()}",
                    "type": "challenge_reminder",
                    "title": "오늘의 챌린지를 확인해 보세요",
                    "message": "몸 상태에 맞는 범위에서 실천하고 기록해 주세요.",
                }
            )
        if cycle and preference.weekly_report_enabled:
            items.append(
                {
                    "notification_id": f"report-{cycle.id}",
                    "type": "weekly_report",
                    "title": "주간 리포트를 확인할 수 있어요",
                    "message": "기록을 요약해 다음 목표 조정에 활용해 보세요.",
                }
            )
        return {"items": items, "notice": "의료 경고가 아닌 생활기록 알림입니다."}
