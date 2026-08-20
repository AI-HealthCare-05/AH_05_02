"""Service health fields to the KLoSA single-user feature contract."""

from datetime import date
from typing import TypedDict

from src.backend.api.v1.schemas.prediction import PredictionPreviewRequest


class DiabetesModelInput(TypedDict):
    age: int
    sex: str
    bmi: float
    smoking_status: str
    current_drinker: bool
    regular_exercise: bool
    exercise_days_per_week: int
    exercise_minutes: int


WEB_MODEL_FEATURES = (
    "age",
    "sex",
    "bmi",
    "smoking_status",
    "current_drinker",
    "regular_exercise",
    "exercise_days_per_week",
    "exercise_minutes",
)


def to_diabetes_model_input(
    health: PredictionPreviewRequest,
    *,
    as_of: date | None = None,
) -> DiabetesModelInput:
    """Convert API values to stable model names and encodings."""
    age = health.age_years(as_of=as_of)
    bmi = health.weight_kg / ((health.height_cm / 100) ** 2)
    model_input: DiabetesModelInput = {
        "age": age,
        "sex": health.sex,
        "bmi": round(bmi, 2),
        "smoking_status": health.smoking_status,
        "current_drinker": health.current_drinker,
        "regular_exercise": health.regular_exercise,
        "exercise_days_per_week": health.exercise_days_per_week,
        "exercise_minutes": health.exercise_minutes,
    }
    if tuple(model_input) != WEB_MODEL_FEATURES:
        raise ValueError("Model input does not match the approved feature allowlist")
    return model_input
