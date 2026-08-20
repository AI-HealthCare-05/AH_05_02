"""Diabetes future-incidence prediction schemas."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PredictionPreviewRequest(BaseModel):
    """Health fields currently confirmed for the model integration contract."""

    model_config = ConfigDict(extra="forbid")

    birth_date: date
    sex: Literal["male", "female"]
    height_cm: float = Field(ge=120, le=220)
    weight_kg: float = Field(ge=25, le=250)
    smoking_status: Literal["never", "former", "current"]
    current_drinker: bool
    regular_exercise: bool
    exercise_days_per_week: int = Field(ge=0, le=7)
    exercise_minutes: int = Field(ge=0, le=720)
    previously_diagnosed_diabetes: bool = False

    @model_validator(mode="after")
    def validate_input_consistency(self) -> "PredictionPreviewRequest":
        """Pure input-format/logic checks only (422 territory).

        Policy-based exclusions — model age range, prior diagnosis, consent,
        etc. — are NOT checked here. Per SERVICE_SCOPE_AND_SAFETY_COPY.md
        SS6-1/6-2 those must return 403 PREDICTION_NOT_ALLOWED, which a
        pydantic validator cannot produce (FastAPI always maps validator
        errors to 422). See prediction_service._ensure_policy_eligible.
        """
        if not self.regular_exercise and (self.exercise_days_per_week != 0 or self.exercise_minutes != 0):
            raise ValueError("규칙적 운동을 하지 않는 경우 운동 일수와 시간은 0이어야 합니다.")
        return self

    def age_years(self, *, as_of: date | None = None) -> int:
        """Age in whole years as of ``as_of`` (defaults to today)."""
        reference_date = as_of or date.today()
        return (
            reference_date.year
            - self.birth_date.year
            - ((reference_date.month, reference_date.day) < (self.birth_date.month, self.birth_date.day))
        )


class SafetyNotice(BaseModel):
    summary: str
    is_medical_diagnosis: bool = False
    message: str


class PredictionPreviewData(BaseModel):
    prediction_id: UUID
    condition: Literal["diabetes"]
    model_type: Literal["future_incidence"]
    data_source: Literal["klosa"]
    # 2026-08-20 모델 연동 Q&A SS5 "최종 명칭": target_horizon -> outcome_definition.
    outcome_definition: Literal["next_observation_new_diabetes_diagnosis"]
    risk_score: float
    # 2026-08-20 모델 연동 Q&A SS6, 안 B 채택: 임계값 승인 전에는 범주·판정을
    # 반환하지 않는다. risk_score만 노출하고 나머지는 null.
    risk_category: Literal["low", "caution", "high"] | None
    risk_category_label: Literal["낮음", "주의", "높음"] | None
    decision_threshold: float | None
    predicted_class: Literal[0, 1] | None
    model_version: str
    target_definition_version: str
    input_schema_version: str
    feature_schema_version: str
    preprocessing_version: str
    calibration_version: str
    predicted_at: datetime
    is_temporary: bool
    safety_notice: SafetyNotice


class PredictionPreviewResponse(BaseModel):
    data: PredictionPreviewData
