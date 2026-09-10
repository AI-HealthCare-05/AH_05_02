from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class WearableConnectionRequest(BaseModel):
    provider: Literal["development_mock", "file_import"] = "development_mock"
    scopes: list[Literal["activity", "sleep", "heart_rate"]] = Field(default_factory=lambda: ["activity"])


class WearableDailyItem(BaseModel):
    summary_date: date
    steps: int | None = Field(default=None, ge=0, le=200_000)
    active_minutes: int | None = Field(default=None, ge=0, le=1_440)
    sleep_minutes: int | None = Field(default=None, ge=0, le=1_440)
    resting_heart_rate: int | None = Field(default=None, ge=25, le=250)

    @model_validator(mode="after")
    def require_one_measurement(self) -> WearableDailyItem:
        if all(
            value is None for value in (self.steps, self.active_minutes, self.sleep_minutes, self.resting_heart_rate)
        ):
            raise ValueError("하나 이상의 웨어러블 측정값이 필요합니다.")
        return self


class WearableImportRequest(BaseModel):
    connection_id: int = Field(gt=0)
    items: list[WearableDailyItem] = Field(min_length=1, max_length=31)


class RagQuestionRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class FoodAnalysisRequest(BaseModel):
    image_name: str = Field(min_length=1, max_length=200)


class FoodAnalysisConfirmRequest(BaseModel):
    confirmed_category: Literal["곡류", "채소", "과일", "단백질", "유제품", "혼합식", "확인불가"]


class OcrDraftRequest(BaseModel):
    document_name: str = Field(min_length=1, max_length=200)
    extracted_fields: dict[str, str | int | float | None] = Field(default_factory=dict)


class NotificationPreferenceRequest(BaseModel):
    in_app_enabled: bool = True
    challenge_reminder_enabled: bool = True
    weekly_report_enabled: bool = True
    quiet_start_hour: int = Field(default=21, ge=0, le=23)
    quiet_end_hour: int = Field(default=8, ge=0, le=23)
