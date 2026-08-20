from datetime import date

from src.backend.api.v1.schemas.prediction import PredictionPreviewRequest
from src.ml.preprocessing.diabetes_input import to_diabetes_model_input


def test_health_fields_are_converted_to_model_contract() -> None:
    request = PredictionPreviewRequest(
        birth_date=date(1970, 6, 15),
        sex="female",
        height_cm=160,
        weight_kg=64,
        smoking_status="current",
        current_drinker=True,
        regular_exercise=True,
        exercise_days_per_week=4,
        exercise_minutes=30,
        previously_diagnosed_diabetes=False,
    )

    result = to_diabetes_model_input(request, as_of=date(2026, 6, 14))

    assert result == {
        "age": 55,
        "sex": "female",
        "bmi": 25.0,
        "smoking_status": "current",
        "current_drinker": True,
        "regular_exercise": True,
        "exercise_days_per_week": 4,
        "exercise_minutes": 30,
    }
