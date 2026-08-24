"""Single-user inference for the research KLoSA diabetes-incidence baseline.

The baseline returns an uncalibrated research probability only. Operational
risk bands and binary decision thresholds remain pending mentor review.
Only load model bundles produced by this project from a trusted location.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from ai_worker.ml.build_klosa_diabetes_cohort import WEB_MODEL_FEATURES

MODEL_VERSION = "klosa-diabetes-incidence-pooled-logistic-v1"
TARGET_DEFINITION_VERSION = "klosa-diabetes-incidence-next-wave-v1"
INPUT_SCHEMA_VERSION = "diabetes-incidence-input-v1"
FEATURE_SET_VERSION = "klosa-web-minimal-8-v1"
PREPROCESSING_VERSION = "median-mode-onehot-standardscale-v1"
CALIBRATION_VERSION = "none-research-baseline-v1"
SUPPORTED_AGE_MINIMUM = 45
SUPPORTED_AGE_MAXIMUM = 105


@dataclass(frozen=True)
class DiabetesIncidenceInput:
    """Service-facing fields required for one research prediction."""

    birth_date: date
    sex: str
    height_cm: float
    weight_kg: float
    smoking_status: str
    current_drinker: bool
    regular_exercise: bool
    exercise_days_per_week: float
    exercise_minutes: float
    previously_diagnosed_diabetes: bool


def _age_on(birth_date: date, as_of_date: date) -> int:
    return as_of_date.year - birth_date.year - (
        (as_of_date.month, as_of_date.day) < (birth_date.month, birth_date.day)
    )


def _require_number_between(name: str, value: Any, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    numeric = float(value)
    if not minimum <= numeric <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return numeric


def build_model_frame(
    user_input: DiabetesIncidenceInput,
    *,
    as_of_date: date,
) -> pd.DataFrame:
    """Validate service inputs and derive the exact eight-feature model row."""

    if user_input.previously_diagnosed_diabetes:
        raise ValueError(
            "previously diagnosed users are ineligible for an incident-diagnosis model"
        )
    if user_input.birth_date > as_of_date:
        raise ValueError("birth_date cannot be in the future")

    age = _age_on(user_input.birth_date, as_of_date)
    if not SUPPORTED_AGE_MINIMUM <= age <= SUPPORTED_AGE_MAXIMUM:
        raise ValueError(
            f"age {age} is outside the model-supported range "
            f"{SUPPORTED_AGE_MINIMUM}-{SUPPORTED_AGE_MAXIMUM}"
        )
    if user_input.sex not in {"male", "female"}:
        raise ValueError("sex must be 'male' or 'female'")
    if user_input.smoking_status not in {"never", "former", "current"}:
        raise ValueError("smoking_status must be never, former, or current")
    if not isinstance(user_input.current_drinker, bool):
        raise ValueError("current_drinker must be boolean")
    if not isinstance(user_input.regular_exercise, bool):
        raise ValueError("regular_exercise must be boolean")

    height_cm = _require_number_between("height_cm", user_input.height_cm, 120, 220)
    weight_kg = _require_number_between("weight_kg", user_input.weight_kg, 25, 250)
    days = _require_number_between(
        "exercise_days_per_week", user_input.exercise_days_per_week, 0, 7
    )
    minutes = _require_number_between(
        "exercise_minutes", user_input.exercise_minutes, 0, 720
    )
    if not user_input.regular_exercise:
        days = 0.0
        minutes = 0.0

    row = {
        "age": age,
        "sex": user_input.sex,
        "bmi": weight_kg / (height_cm / 100) ** 2,
        "smoking_status": user_input.smoking_status,
        "current_drinker": user_input.current_drinker,
        "regular_exercise": user_input.regular_exercise,
        "exercise_days_per_week": days,
        "exercise_minutes": minutes,
    }
    return pd.DataFrame([row], columns=WEB_MODEL_FEATURES)


def load_model_bundle(path: Path) -> dict[str, Any]:
    """Load and validate a trusted model bundle created by the training script."""

    bundle = joblib.load(path)
    if not isinstance(bundle, dict) or "pipeline" not in bundle or "metadata" not in bundle:
        raise ValueError("invalid KLoSA model bundle")
    metadata = bundle["metadata"]
    if metadata.get("input_schema_version") != INPUT_SCHEMA_VERSION:
        raise ValueError("model input schema version mismatch")
    if metadata.get("features") != WEB_MODEL_FEATURES:
        raise ValueError("model feature contract mismatch")
    return bundle


def predict_single_user(
    bundle: dict[str, Any],
    user_input: DiabetesIncidenceInput,
    *,
    as_of_date: date,
    predicted_at: datetime | None = None,
) -> dict[str, Any]:
    """Return an API-aligned, probability-only result for one eligible user."""

    metadata = bundle["metadata"]
    if metadata.get("features") != WEB_MODEL_FEATURES:
        raise ValueError("model feature contract mismatch")
    model_frame = build_model_frame(user_input, as_of_date=as_of_date)
    probability = float(bundle["pipeline"].predict_proba(model_frame)[0, 1])
    completed_at = predicted_at or datetime.now(UTC)
    return {
        "disease_type": "diabetes",
        "task_type": "binary_incidence",
        "outcome_definition": "next_observation_new_diabetes_diagnosis",
        "class_probabilities": {
            "no_incident_diagnosis": 1.0 - probability,
            "incident_diagnosis": probability,
        },
        "risk_category": None,
        "risk_category_label": None,
        "decision_threshold": None,
        "output_status": "uncalibrated_research_probability_only",
        "model_version": metadata["model_version"],
        "target_definition_version": metadata["target_definition_version"],
        "input_schema_version": metadata["input_schema_version"],
        "feature_set_version": metadata["feature_set_version"],
        "preprocessing_version": metadata["preprocessing_version"],
        "calibration_version": metadata["calibration_version"],
        "predicted_at": completed_at.isoformat(),
        "disclaimer": (
            "연구용 모델이 추정한 다음 조사 시점까지의 신규 당뇨병 의사진단 "
            "확률입니다. 진단이나 처방이 아니며 위험구간과 운영 임계값은 확정되지 "
            "않았습니다."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("models/baselines/klosa_diabetes_incidence_pooled/model.joblib"),
    )
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=date.today())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw = json.loads(args.input_json.read_text(encoding="utf-8"))
    raw["birth_date"] = date.fromisoformat(raw["birth_date"])
    user_input = DiabetesIncidenceInput(**raw)
    result = predict_single_user(
        load_model_bundle(args.model),
        user_input,
        as_of_date=args.as_of_date,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
