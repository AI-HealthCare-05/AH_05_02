from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core import config

KLOSA_FEATURE_SCHEMA = (
    "age",
    "bmi",
    "self_rated_health",
    "meal_count_yesterday",
    "sex",
    "regular_exercise",
    "current_smoker",
    "current_drinker",
)


class ActiveModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    model_key: str
    version: str
    feature_schema_version: str
    threshold_version: str
    min_age: int
    max_age: int | None
    model_population: str
    outcome_definition: str = "next_observation_new_diabetes_diagnosis"
    observation_horizon: str = "approximately_2_years_next_klosa_wave"
    promotion_status: str = "development_only"

    @property
    def threshold_is_approved(self) -> bool:
        return self.threshold_version not in {"", "unapproved"} and self.promotion_status == "approved"


ACTIVE_MODEL = ActiveModel(
    model_key=config.PREDICTION_MODEL_KEY,
    version=config.PREDICTION_MODEL_VERSION,
    feature_schema_version=config.PREDICTION_FEATURE_SCHEMA_VERSION,
    threshold_version=config.PREDICTION_THRESHOLD_VERSION,
    min_age=config.PREDICTION_MODEL_MIN_AGE,
    max_age=config.PREDICTION_MODEL_MAX_AGE,
    model_population=config.PREDICTION_MODEL_POPULATION,
    promotion_status="approved" if config.PREDICTION_THRESHOLD_VERSION != "unapproved" else "development_only",
)


class PredictionFeatures(BaseModel):
    """Versioned KLoSA incidence input. Target/leakage variables are intentionally absent."""

    model_config = ConfigDict(extra="forbid")

    age: int = Field(ge=45, le=120)
    bmi: float = Field(ge=10, le=80)
    self_rated_health: Literal["very_good", "good", "fair", "poor", "very_poor"]
    meal_count_yesterday: int = Field(ge=0, le=10)
    sex: Literal["female", "male"]
    regular_exercise: bool
    current_smoker: bool
    current_drinker: bool

    def as_model_record(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in KLOSA_FEATURE_SCHEMA}


def input_schema_document() -> dict[str, Any]:
    return {
        "model_key": ACTIVE_MODEL.model_key,
        "feature_schema_version": ACTIVE_MODEL.feature_schema_version,
        "fields": [
            {"name": "height_cm", "type": "number", "unit": "cm", "required": True, "min": 120, "max": 220},
            {"name": "weight_kg", "type": "number", "unit": "kg", "required": True, "min": 30, "max": 250},
            {
                "name": "self_rated_health",
                "type": "enum",
                "required": True,
                "values": ["very_good", "good", "fair", "poor", "very_poor"],
            },
            {"name": "meal_count_yesterday", "type": "integer", "unit": "회", "required": True, "min": 0, "max": 10},
            {"name": "regular_exercise", "type": "boolean", "required": True},
            {"name": "current_smoker", "type": "boolean", "required": True},
            {"name": "current_drinker", "type": "boolean", "required": True},
        ],
        "derived_fields": ["age", "bmi", "sex"],
        "excluded_leakage_fields": [
            "diabetes_diagnosis_at_followup",
            "glucose_lowering_medication_at_followup",
            "future_wave_measurements",
        ],
    }
