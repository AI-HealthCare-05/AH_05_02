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
    weight_kg: float = Field(ge=25, le=250)
    waist_cm: float | None = Field(default=None, ge=45, le=180)
    systolic_bp: int | None = Field(default=None, ge=70, le=250)
    diastolic_bp: int | None = Field(default=None, ge=40, le=150)
    self_rated_health: Literal["very_good", "good", "fair", "poor", "very_poor"]
    meal_count_yesterday: int = Field(ge=0, le=10)
    smoking_status: Literal["never", "former", "current"]
    regular_exercise: bool
    current_drinker: bool
    exercise_days_per_week: float = Field(ge=0, le=7)
    exercise_minutes: float = Field(ge=0, le=720)
    annual_household_income_10k_krw: float | None = Field(default=None, ge=0)
    health_satisfaction_score: float | None = Field(default=None, ge=0, le=10)
    economic_satisfaction_score: float | None = Field(default=None, ge=0, le=10)
    overall_quality_of_life_score: float | None = Field(default=None, ge=0, le=10)
    hypertension_diagnosis: bool | None = None
    cancer_diagnosis: bool | None = None
    chronic_lung_disease_diagnosis: bool | None = None
    liver_disease_diagnosis: bool | None = None
    heart_disease_diagnosis: bool | None = None
    cerebrovascular_disease_diagnosis: bool | None = None
    psychiatric_disease_diagnosis: bool | None = None
    arthritis_rheumatism_diagnosis: bool | None = None
    education_level: str | None = Field(default=None, max_length=50)
    marital_status: str | None = Field(default=None, max_length=50)
    household_structure: str | None = Field(default=None, max_length=50)
    depressed_feeling_last_week: bool | None = None
    sleep_difficulty_last_week: bool | None = None
    feature_schema_version: str = Field(default=ACTIVE_MODEL.feature_schema_version, max_length=100)

    @model_validator(mode="after")
    def validate_blood_pressure(self) -> HealthCheckupCreateRequest:
        if self.systolic_bp is not None and self.diastolic_bp is not None and self.systolic_bp <= self.diastolic_bp:
            raise ValueError("수축기 혈압은 이완기 혈압보다 커야 합니다.")
        if not self.regular_exercise:
            self.exercise_days_per_week = 0
            self.exercise_minutes = 0
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


class ChallengeVerificationCreateRequest(BaseModel):
    verification_date: date
    verification_type: Literal["photo", "location"]
    evidence_ref: str | None = Field(default=None, max_length=500)
    evidence_digest: str | None = Field(default=None, min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    location_accuracy_m: float | None = Field(default=None, ge=0, le=100000)

    @model_validator(mode="after")
    def validate_evidence(self) -> ChallengeVerificationCreateRequest:
        if self.verification_type == "photo" and not (self.evidence_ref or self.evidence_digest):
            raise ValueError("사진 인증에는 증빙 참조 또는 SHA-256 해시가 필요합니다.")
        if self.verification_type == "location" and self.location_accuracy_m is None:
            raise ValueError("위치 인증에는 위치 정확도가 필요합니다.")
        return self


class ChallengeCycleStatusRequest(BaseModel):
    status: Literal["stopped"]
    reason: str = Field(default="user_requested", max_length=80)


class EnvelopeMeta(BaseModel):
    request_id: str
    timestamp: datetime


class FeedbackCreateRequest(BaseModel):
    context_type: Literal["prediction", "recommendation", "service"]
    prediction_id: int | None = Field(default=None, gt=0)
    recommendation_id: int | None = Field(default=None, gt=0)
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_context_reference(self) -> FeedbackCreateRequest:
        if self.context_type == "prediction" and self.prediction_id is None:
            raise ValueError("예측 결과 피드백에는 prediction_id가 필요합니다.")
        if self.context_type == "recommendation" and self.recommendation_id is None:
            raise ValueError("추천 피드백에는 recommendation_id가 필요합니다.")
        return self
