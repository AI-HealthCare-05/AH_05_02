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
    def validate_model_population(self) -> "PredictionPreviewRequest":
        today = date.today()
        age = (
            today.year
            - self.birth_date.year
            - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        )
        if age < 45 or age > 105:
            raise ValueError("KLoSA 미래발병 모델 적용 연령은 만 45~105세입니다.")
        if self.previously_diagnosed_diabetes:
            raise ValueError("당뇨병 기진단자는 미래발병 예측 대상이 아닙니다.")
        if not self.regular_exercise and (self.exercise_days_per_week != 0 or self.exercise_minutes != 0):
            raise ValueError("규칙적 운동을 하지 않는 경우 운동 일수와 시간은 0이어야 합니다.")
        return self


class SafetyNotice(BaseModel):
    summary: str
    is_medical_diagnosis: bool = False
    message: str


class PredictionPreviewData(BaseModel):
    prediction_id: UUID
    condition: Literal["diabetes"]
    model_type: Literal["future_incidence"]
    data_source: Literal["klosa"]
    target_horizon: Literal["next_wave_about_2y"]
    risk_category: Literal["low", "moderate", "high"]
    risk_category_label: Literal["낮음", "주의", "높음"]
    predicted_class: Literal[0, 1]
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
