"""KLoSA-based diabetes future-incidence binary inference adapter."""

from dataclasses import dataclass

from src.ml.preprocessing.diabetes_input import DiabetesModelInput


@dataclass(frozen=True)
class DiabetesInferenceResult:
    predicted_class: int
    score: float
    model_version: str


def predict_single_user(model_input: DiabetesModelInput) -> DiabetesInferenceResult:
    """Temporary adapter to replace with Junhyuk's single-user function.

    The fixed score is deliberately non-clinical. It verifies only that the API,
    preprocessing, and response layers are connected without inventing a model.
    """
    required = {
        "age",
        "sex",
        "bmi",
        "smoking_status",
        "current_drinker",
        "regular_exercise",
        "exercise_days_per_week",
        "exercise_minutes",
    }
    missing = required.difference(model_input)
    if missing:
        raise ValueError(f"Missing model inputs: {sorted(missing)}")

    score = 0.28
    return DiabetesInferenceResult(
        predicted_class=int(score >= 0.5),
        score=score,
        model_version="temporary-integration-v1",
    )
