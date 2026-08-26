"""Convert one web API health record to the fixed RF 25-feature schema."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

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

SUPPORTED_AGE_MINIMUM = 45
SUPPORTED_AGE_MAXIMUM = 105
DIAGNOSIS_FIELDS = (
    "hypertension_diagnosis",
    "cancer_diagnosis",
    "chronic_lung_disease_diagnosis",
    "liver_disease_diagnosis",
    "heart_disease_diagnosis",
    "cerebrovascular_disease_diagnosis",
    "psychiatric_disease_diagnosis",
    "arthritis_rheumatism_diagnosis",
)
REQUIRED_API_FIELDS = (
    "birth_date",
    "sex",
    "height_cm",
    "weight_kg",
    "smoking_status",
    "current_drinker",
    "regular_exercise",
    "exercise_days_per_week",
    "exercise_minutes",
    "previously_diagnosed_diabetes",
)
OPTIONAL_API_FIELDS = (
    "annual_household_income_10k_krw",
    "health_satisfaction_score",
    "economic_satisfaction_score",
    "overall_quality_of_life_score",
    *DIAGNOSIS_FIELDS,
    "education_level",
    "marital_status",
    "household_structure",
    "depressed_feeling_last_week",
    "sleep_difficulty_last_week",
)
API_INPUT_CONTRACT = {
    "birth_date": {"required": True, "type": "date", "unit": "YYYY-MM-DD"},
    "sex": {
        "required": True,
        "type": "string",
        "allowed": ["female", "male"],
    },
    "height_cm": {"required": True, "type": "number", "unit": "cm", "range": [120, 220]},
    "weight_kg": {"required": True, "type": "number", "unit": "kg", "range": [25, 250]},
    "smoking_status": {
        "required": True,
        "type": "string",
        "allowed": ["never", "former", "current"],
    },
    "current_drinker": {"required": True, "type": "boolean"},
    "regular_exercise": {"required": True, "type": "boolean"},
    "exercise_days_per_week": {
        "required": True,
        "type": "number",
        "unit": "days/week",
        "range": [0, 7],
    },
    "exercise_minutes": {
        "required": True,
        "type": "number",
        "unit": "minutes/session",
        "range": [0, 720],
    },
    "previously_diagnosed_diabetes": {
        "required": True,
        "type": "boolean",
        "model_feature": False,
        "true_policy": "reject_as_ineligible",
    },
    "annual_household_income_10k_krw": {
        "required": False,
        "type": "number|null",
        "unit": "10,000 KRW/year",
        "range": [0, 123500],
        "transform": "log1p",
    },
    "health_satisfaction_score": {
        "required": False,
        "type": "number|null",
        "unit": "score",
        "range": [0, 100],
    },
    "economic_satisfaction_score": {
        "required": False,
        "type": "number|null",
        "unit": "score",
        "range": [0, 100],
    },
    "overall_quality_of_life_score": {
        "required": False,
        "type": "number|null",
        "unit": "score",
        "range": [0, 100],
    },
    **{
        name: {
            "required": False,
            "type": "boolean|null",
            "mapping": {"true": "yes", "false": "no", "null": "missing"},
        }
        for name in DIAGNOSIS_FIELDS
    },
    "education_level": {
        "required": False,
        "type": "string|null",
        "allowed": ["code_1", "code_2", "code_3", "code_4", "code_97"],
    },
    "marital_status": {
        "required": False,
        "type": "string|null",
        "allowed": ["code_1", "code_2", "code_3", "code_4", "code_5"],
    },
    "household_structure": {
        "required": False,
        "type": "string|null",
        "allowed": ["single_person", "multi_person"],
    },
    "depressed_feeling_last_week": {
        "required": False,
        "type": "string|null",
        "allowed": ["code_1", "code_2", "code_3", "code_4"],
    },
    "sleep_difficulty_last_week": {
        "required": False,
        "type": "string|null",
        "allowed": ["code_1", "code_2", "code_3", "code_4"],
    },
}


@dataclass(frozen=True)
class DiabetesRiskInput:
    """Web-facing values for one diabetes-incidence screening prediction.

    The first ten fields are required. The remaining fields are optional and
    are imputed by preprocessing objects fitted on Train data only.
    """

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
    annual_household_income_10k_krw: float | None = None
    health_satisfaction_score: float | None = None
    economic_satisfaction_score: float | None = None
    overall_quality_of_life_score: float | None = None
    hypertension_diagnosis: bool | None = None
    cancer_diagnosis: bool | None = None
    chronic_lung_disease_diagnosis: bool | None = None
    liver_disease_diagnosis: bool | None = None
    heart_disease_diagnosis: bool | None = None
    cerebrovascular_disease_diagnosis: bool | None = None
    psychiatric_disease_diagnosis: bool | None = None
    arthritis_rheumatism_diagnosis: bool | None = None
    education_level: str | None = None
    marital_status: str | None = None
    household_structure: str | None = None
    depressed_feeling_last_week: str | None = None
    sleep_difficulty_last_week: str | None = None


def parse_diabetes_risk_input(payload: dict[str, Any]) -> DiabetesRiskInput:
    """Parse a JSON-compatible mapping and reject unknown or missing fields."""

    values = dict(payload)
    birth_date = values.get("birth_date")
    if isinstance(birth_date, str):
        try:
            values["birth_date"] = date.fromisoformat(birth_date)
        except ValueError as exc:
            raise ValueError("birth_date must use YYYY-MM-DD") from exc
    try:
        return DiabetesRiskInput(**values)
    except TypeError as exc:
        raise ValueError(f"invalid diabetes risk input: {exc}") from exc


def _number(name: str, value: Any, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    numeric = float(value)
    if not math.isfinite(numeric) or not minimum <= numeric <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return numeric


def _optional_number(
    name: str,
    value: Any,
    minimum: float,
    maximum: float,
) -> float:
    return np.nan if value is None else _number(name, value, minimum, maximum)


def _category(name: str, value: Any, allowed: set[str]) -> str | float:
    if value is None:
        return np.nan
    if not isinstance(value, str) or value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise ValueError(f"{name} must be one of: {choices}")
    return value


def _required_category(name: str, value: Any, allowed: set[str]) -> str:
    if value is None:
        raise ValueError(f"{name} is required")
    result = _category(name, value, allowed)
    if not isinstance(result, str):  # defensive: required fields cannot be NaN
        raise ValueError(f"{name} is required")
    return result


def _diagnosis(value: Any, name: str) -> str | float:
    if value is None:
        return np.nan
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be boolean or null")
    return "yes" if value else "no"


def _age_on(birth_date: date, as_of_date: date) -> int:
    return as_of_date.year - birth_date.year - (
        (as_of_date.month, as_of_date.day) < (birth_date.month, birth_date.day)
    )


def build_standard_model_frame(
    user_input: DiabetesRiskInput,
    *,
    as_of_date: date,
) -> pd.DataFrame:
    """Validate one API record and return exactly one ordered model row."""

    if not isinstance(user_input.birth_date, date):
        raise ValueError("birth_date must be a date")
    if user_input.birth_date > as_of_date:
        raise ValueError("birth_date cannot be in the future")
    if not isinstance(user_input.previously_diagnosed_diabetes, bool):
        raise ValueError("previously_diagnosed_diabetes must be boolean")
    if user_input.previously_diagnosed_diabetes:
        raise ValueError(
            "previously diagnosed users are ineligible for an incidence screening model"
        )

    age = _age_on(user_input.birth_date, as_of_date)
    if not SUPPORTED_AGE_MINIMUM <= age <= SUPPORTED_AGE_MAXIMUM:
        raise ValueError(
            f"age {age} is outside the model-supported range "
            f"{SUPPORTED_AGE_MINIMUM}-{SUPPORTED_AGE_MAXIMUM}"
        )
    sex = _required_category("sex", user_input.sex, {"female", "male"})
    smoking = _required_category(
        "smoking_status",
        user_input.smoking_status,
        {"never", "former", "current"},
    )
    for name in ("current_drinker", "regular_exercise"):
        if not isinstance(getattr(user_input, name), bool):
            raise ValueError(f"{name} must be boolean")

    height = _number("height_cm", user_input.height_cm, 120, 220)
    weight = _number("weight_kg", user_input.weight_kg, 25, 250)
    bmi = weight / (height / 100) ** 2
    if not 10 <= bmi <= 70:
        raise ValueError("derived bmi must be between 10 and 70 kg/m2")
    days = _number(
        "exercise_days_per_week", user_input.exercise_days_per_week, 0, 7
    )
    minutes = _number("exercise_minutes", user_input.exercise_minutes, 0, 720)
    if not user_input.regular_exercise:
        days = 0.0
        minutes = 0.0

    income = _optional_number(
        "annual_household_income_10k_krw",
        user_input.annual_household_income_10k_krw,
        0,
        123_500,
    )
    row: dict[str, Any] = {
        "age": age,
        "bmi": bmi,
        "exercise_days_per_week": days,
        "exercise_minutes": minutes,
        "log_household_income": np.log1p(income) if not np.isnan(income) else np.nan,
        "health_satisfaction_score": _optional_number(
            "health_satisfaction_score", user_input.health_satisfaction_score, 0, 100
        ),
        "economic_satisfaction_score": _optional_number(
            "economic_satisfaction_score",
            user_input.economic_satisfaction_score,
            0,
            100,
        ),
        "overall_quality_of_life_score": _optional_number(
            "overall_quality_of_life_score",
            user_input.overall_quality_of_life_score,
            0,
            100,
        ),
        "sex": sex,
        "smoking_status": smoking,
        "current_drinker": user_input.current_drinker,
        "regular_exercise": user_input.regular_exercise,
        "education_level": _category(
            "education_level",
            user_input.education_level,
            {"code_1", "code_2", "code_3", "code_4", "code_97"},
        ),
        "marital_status": _category(
            "marital_status",
            user_input.marital_status,
            {"code_1", "code_2", "code_3", "code_4", "code_5"},
        ),
        "household_structure": _category(
            "household_structure",
            user_input.household_structure,
            {"single_person", "multi_person"},
        ),
        "depressed_feeling_last_week": _category(
            "depressed_feeling_last_week",
            user_input.depressed_feeling_last_week,
            {"code_1", "code_2", "code_3", "code_4"},
        ),
        "sleep_difficulty_last_week": _category(
            "sleep_difficulty_last_week",
            user_input.sleep_difficulty_last_week,
            {"code_1", "code_2", "code_3", "code_4"},
        ),
    }
    raw = asdict(user_input)
    row.update({name: _diagnosis(raw[name], name) for name in DIAGNOSIS_FIELDS})
    return pd.DataFrame([row], columns=STANDARD_MODEL_FEATURES)
