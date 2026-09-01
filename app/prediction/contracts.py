from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core import config

STANDARD_MODEL_FEATURES = (
    "age",
    "sex",
    "bmi",
    "smoking_status",
    "current_drinker",
    "regular_exercise",
    "exercise_days_per_week",
    "exercise_minutes",
    "hypertension_diagnosis",
    "cancer_diagnosis",
    "chronic_lung_disease_diagnosis",
    "liver_disease_diagnosis",
    "heart_disease_diagnosis",
    "cerebrovascular_disease_diagnosis",
    "psychiatric_disease_diagnosis",
    "arthritis_rheumatism_diagnosis",
    "log_household_income",
    "education_level",
    "marital_status",
    "household_structure",
    "health_satisfaction_score",
    "economic_satisfaction_score",
    "overall_quality_of_life_score",
    "depressed_feeling_last_week",
    "sleep_difficulty_last_week",
)
KLOSA_FEATURE_SCHEMA = STANDARD_MODEL_FEATURES


class ActiveModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    model_key: str
    version: str
    feature_schema_version: str
    input_schema_version: str
    preprocessing_version: str
    target_definition_version: str
    calibration_version: str
    model_artifact_digest: str | None
    threshold_version: str
    decision_threshold: float | None
    min_age: int
    max_age: int | None
    model_population: str
    outcome_definition: str = "next_observation_new_diabetes_diagnosis"
    observation_horizon: str = "approximately_2_years_next_klosa_wave"
    promotion_status: str = "development_only"

    @property
    def threshold_is_approved(self) -> bool:
        return self.threshold_version not in {"", "unapproved"} and self.promotion_status == "approved"


# v3.0 연령별 당뇨 위험 전망(생존곡선). diabetes_incidence와 달리 아직 승인된
# 모델이 없어 ModelRegistry 테이블(is_active=True row)로만 활성화된다 — 정적
# ActiveModel 상수를 만들지 않는 이유는, 아직 없는 모델을 있는 것처럼 하드코딩
# 하지 않기 위함이다.
LIFETIME_RISK_MODEL_KEY = "diabetes_lifetime_risk"

ACTIVE_MODEL = ActiveModel(
    model_key=config.PREDICTION_MODEL_KEY,
    version=config.PREDICTION_MODEL_VERSION,
    feature_schema_version=config.PREDICTION_FEATURE_SCHEMA_VERSION,
    input_schema_version=config.PREDICTION_INPUT_SCHEMA_VERSION,
    preprocessing_version=config.PREDICTION_PREPROCESSING_VERSION,
    target_definition_version=config.PREDICTION_TARGET_DEFINITION_VERSION,
    calibration_version=config.PREDICTION_CALIBRATION_VERSION,
    model_artifact_digest=config.PREDICTION_MODEL_ARTIFACT_DIGEST or None,
    threshold_version=config.PREDICTION_THRESHOLD_VERSION,
    decision_threshold=config.PREDICTION_DECISION_THRESHOLD,
    min_age=config.PREDICTION_MODEL_MIN_AGE,
    max_age=config.PREDICTION_MODEL_MAX_AGE,
    model_population=config.PREDICTION_MODEL_POPULATION,
    promotion_status=config.PREDICTION_PROMOTION_STATUS,
)


class PredictionFeatures(BaseModel):
    """Versioned KLoSA incidence input. Target/leakage variables are intentionally absent."""

    model_config = ConfigDict(extra="forbid")

    age: int = Field(ge=45, le=105)
    sex: Literal["female", "male"]
    bmi: float = Field(ge=10, le=70)
    smoking_status: Literal["never", "former", "current"]
    current_drinker: bool
    regular_exercise: bool
    exercise_days_per_week: float = Field(ge=0, le=7)
    exercise_minutes: float = Field(ge=0, le=720)
    hypertension_diagnosis: bool | None = None
    cancer_diagnosis: bool | None = None
    chronic_lung_disease_diagnosis: bool | None = None
    liver_disease_diagnosis: bool | None = None
    heart_disease_diagnosis: bool | None = None
    cerebrovascular_disease_diagnosis: bool | None = None
    psychiatric_disease_diagnosis: bool | None = None
    arthritis_rheumatism_diagnosis: bool | None = None
    log_household_income: float | None = Field(default=None, ge=0)
    education_level: str | None = Field(default=None, max_length=50)
    marital_status: str | None = Field(default=None, max_length=50)
    household_structure: str | None = Field(default=None, max_length=50)
    health_satisfaction_score: float | None = Field(default=None, ge=0, le=100)
    economic_satisfaction_score: float | None = Field(default=None, ge=0, le=100)
    overall_quality_of_life_score: float | None = Field(default=None, ge=0, le=100)
    depressed_feeling_last_week: Literal["code_1", "code_2", "code_3", "code_4"] | None = None
    sleep_difficulty_last_week: Literal["code_1", "code_2", "code_3", "code_4"] | None = None

    def as_model_record(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in STANDARD_MODEL_FEATURES}


def input_schema_document() -> dict[str, Any]:
    return {
        "model_key": ACTIVE_MODEL.model_key,
        "feature_schema_version": ACTIVE_MODEL.feature_schema_version,
        "fields": [
            {"name": "height_cm", "type": "number", "unit": "cm", "required": True, "min": 120, "max": 220},
            {"name": "weight_kg", "type": "number", "unit": "kg", "required": True, "min": 25, "max": 250},
            {
                "name": "self_rated_health",
                "type": "enum",
                "required": True,
                "values": ["very_good", "good", "fair", "poor", "very_poor"],
            },
            {"name": "meal_count_yesterday", "type": "integer", "unit": "회", "required": True, "min": 0, "max": 10},
            {"name": "smoking_status", "type": "enum", "required": True, "values": ["never", "former", "current"]},
            {"name": "current_drinker", "type": "boolean", "required": True},
            {"name": "regular_exercise", "type": "boolean", "required": True},
            {"name": "exercise_days_per_week", "type": "number", "required": True, "min": 0, "max": 7},
            {"name": "exercise_minutes", "type": "number", "required": True, "min": 0, "max": 720},
        ],
        "derived_fields": ["age", "bmi", "sex"],
        "excluded_leakage_fields": [
            "diabetes_diagnosis_at_followup",
            "glucose_lowering_medication_at_followup",
            "future_wave_measurements",
        ],
    }
