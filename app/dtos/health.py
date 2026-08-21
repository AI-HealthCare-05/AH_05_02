from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.prediction.contracts import ACTIVE_MODEL


class ConsentCreateRequest(BaseModel):
    consent_item: Literal["health_data"] = "health_data"
    version: str = Field(default="1.0", max_length=30)
    is_agreed: Literal[True]


class EligibilityCreateRequest(BaseModel):
    birth_date: date | None = None
    has_diabetes_diagnosis: bool = False
    has_urgent_warning_sign: bool = False
    population_in_scope: bool = True


class HealthCheckupCreateRequest(BaseModel):
    checkup_type: Literal["initial", "reassessment"] = "initial"
    checkup_date: date
    height_cm: float = Field(ge=120, le=220)
    weight_kg: float = Field(ge=30, le=250)
    waist_cm: float | None = Field(default=None, ge=45, le=180)
    systolic_bp: int | None = Field(default=None, ge=70, le=250)
    diastolic_bp: int | None = Field(default=None, ge=40, le=150)
    self_rated_health: Literal["very_good", "good", "fair", "poor", "very_poor"]
    meal_count_yesterday: int = Field(ge=0, le=10)
    regular_exercise: bool
    current_smoker: bool
    current_drinker: bool
    feature_schema_version: str = Field(default=ACTIVE_MODEL.feature_schema_version, max_length=100)

    @model_validator(mode="after")
    def validate_blood_pressure(self) -> HealthCheckupCreateRequest:
        if self.systolic_bp is not None and self.diastolic_bp is not None and self.systolic_bp <= self.diastolic_bp:
            raise ValueError("수축기 혈압은 이완기 혈압보다 커야 합니다.")
        return self


class PredictionJobCreateRequest(BaseModel):
    checkup_id: int = Field(gt=0)
    model_key: Literal["diabetes_incidence"] = "diabetes_incidence"


class ChallengeCycleCreateRequest(BaseModel):
    start_date: date
    challenge_ids: list[int] = Field(min_length=1, max_length=3)
    prediction_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def unique_challenges(self) -> ChallengeCycleCreateRequest:
        if len(self.challenge_ids) != len(set(self.challenge_ids)):
            raise ValueError("같은 챌린지를 중복 선택할 수 없습니다.")
        return self


class ChallengeLogUpsertRequest(BaseModel):
    is_completed: bool
    value: float | None = Field(default=None, ge=0)
    source: Literal["self_report"] = "self_report"
    note: str | None = Field(default=None, max_length=200)


class ChallengeCycleStatusRequest(BaseModel):
    status: Literal["stopped"]
    reason: str = Field(default="user_requested", max_length=80)


class EnvelopeMeta(BaseModel):
    request_id: str
    timestamp: datetime
