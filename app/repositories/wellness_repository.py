from __future__ import annotations

from datetime import date
from typing import Any

from app.models.wellness import (
    FoodAnalysis,
    NotificationPreference,
    OcrDraft,
    WearableConnection,
    WearableDailySummary,
)


class WellnessRepository:
    async def connect_wearable(self, user_id: int, provider: str, scopes: list[str]) -> WearableConnection:
        item, _ = await WearableConnection.update_or_create(
            defaults={"status": "active", "scopes": scopes, "disconnected_at": None},
            user_id=user_id,
            provider=provider,
        )
        return item

    async def wearable_connection(self, connection_id: int, user_id: int) -> WearableConnection | None:
        return await WearableConnection.get_or_none(id=connection_id, user_id=user_id, status="active")

    async def wearable_connections(self, user_id: int) -> list[WearableConnection]:
        return await WearableConnection.filter(user_id=user_id).order_by("-connected_at")

    async def upsert_daily_summary(self, **values: Any) -> WearableDailySummary:
        item, _ = await WearableDailySummary.update_or_create(
            defaults={
                key: value for key, value in values.items() if key not in {"user_id", "connection_id", "summary_date"}
            },
            user_id=values["user_id"],
            connection_id=values["connection_id"],
            summary_date=values["summary_date"],
        )
        return item

    async def daily_summaries(self, user_id: int, start: date, end: date) -> list[WearableDailySummary]:
        return await WearableDailySummary.filter(
            user_id=user_id, summary_date__gte=start, summary_date__lte=end
        ).order_by("summary_date")

    async def create_food_analysis(self, **values: Any) -> FoodAnalysis:
        return await FoodAnalysis.create(**values)

    async def food_analysis(self, analysis_id: int, user_id: int) -> FoodAnalysis | None:
        return await FoodAnalysis.get_or_none(id=analysis_id, user_id=user_id)

    async def create_ocr_draft(self, **values: Any) -> OcrDraft:
        return await OcrDraft.create(**values)

    async def ocr_draft(self, draft_id: int, user_id: int) -> OcrDraft | None:
        return await OcrDraft.get_or_none(id=draft_id, user_id=user_id)

    async def notification_preferences(self, user_id: int) -> NotificationPreference:
        item, _ = await NotificationPreference.get_or_create(user_id=user_id)
        return item

    async def update_notification_preferences(self, user_id: int, values: dict[str, Any]) -> NotificationPreference:
        item, _ = await NotificationPreference.update_or_create(defaults=values, user_id=user_id)
        return item
