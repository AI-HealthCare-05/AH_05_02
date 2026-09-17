"""Map the final Today API payload to the fixed KNHANES 14-feature order."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

TODAY_MODEL_FEATURES = (
    "age",
    "height_cm",
    "weight_kg",
    "waist_cm",
    "bmi",
    "systolic_bp",
    "diastolic_bp",
    "sex",
    "current_smoker",
    "education",
    "region",
    "diabetes_family_history",
    "hypertension_family_history",
    "alcohol_frequency",
)
TODAY_REQUIRED_API_FIELDS = (
    "birth_date",
    "sex",
    "height_cm",
    "weight_kg",
    "smoking_status",
    "alcohol_frequency",
    "previously_diagnosed_diabetes",
)
TODAY_OPTIONAL_API_FIELDS = (
    "education_level",
    "waist_cm",
    "systolic_bp",
    "diastolic_bp",
    "region",
    "diabetes_family_history",
    "hypertension_family_history",
)
SUPPORTED_AGE_MINIMUM = 19
SUPPORTED_AGE_MAXIMUM = 120


@dataclass(frozen=True)
class TodayRiskInput:
    birth_date: date
    sex: str
    height_cm: float
    weight_kg: float
    smoking_status: str
    alcohol_frequency: int
    previously_diagnosed_diabetes: bool
    education_level: str | None = None
    waist_cm: float | None = None
    systolic_bp: float | None = None
    diastolic_bp: float | None = None
    region: int | None = None
    diabetes_family_history: bool | None = None
    hypertension_family_history: bool | None = None


def parse_today_risk_input(payload: dict[str, Any]) -> TodayRiskInput:
    unknown = sorted(set(payload).difference((*TODAY_REQUIRED_API_FIELDS, *TODAY_OPTIONAL_API_FIELDS)))
    if unknown:
        raise ValueError(f"unknown Today fields: {', '.join(unknown)}")
    missing = [name for name in TODAY_REQUIRED_API_FIELDS if payload.get(name) is None]
    if missing:
        raise ValueError(f"missing required Today fields: {', '.join(missing)}")
    values = dict(payload)
    if isinstance(values.get("birth_date"), str):
        try:
            values["birth_date"] = date.fromisoformat(values["birth_date"])
        except ValueError as exc:
            raise ValueError("birth_date must use YYYY-MM-DD") from exc
    try:
        return TodayRiskInput(**values)
    except TypeError as exc:
        raise ValueError(f"invalid Today input: {exc}") from exc


def _number(name: str, value: Any, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    numeric = float(value)
    if not math.isfinite(numeric) or not minimum <= numeric <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return numeric


def _optional_number(name: str, value: Any, minimum: float, maximum: float) -> float:
    return np.nan if value is None else _number(name, value, minimum, maximum)


def _optional_binary(name: str, value: Any) -> float:
    if value is None:
        return np.nan
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be boolean or null")
    return float(value)


def _integer_code(name: str, value: Any, allowed: set[int]) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value not in allowed:
        choices = ",".join(str(code) for code in sorted(allowed))
        raise ValueError(f"{name} must be one of {choices}")
    return value


def build_today_model_frame(user: TodayRiskInput, *, as_of_date: date) -> pd.DataFrame:
    if not isinstance(user.birth_date, date) or user.birth_date > as_of_date:
        raise ValueError("birth_date must be a valid past date")
    if not isinstance(user.previously_diagnosed_diabetes, bool):
        raise ValueError("previously_diagnosed_diabetes must be boolean")
    if user.previously_diagnosed_diabetes:
        raise ValueError("previously diagnosed users are outside the Today screening cohort")
    age = (
        as_of_date.year
        - user.birth_date.year
        - ((as_of_date.month, as_of_date.day) < (user.birth_date.month, user.birth_date.day))
    )
    if not SUPPORTED_AGE_MINIMUM <= age <= SUPPORTED_AGE_MAXIMUM:
        raise ValueError(f"age {age} is outside the supported range 19-120")
    if user.sex not in {"male", "female"}:
        raise ValueError("sex must be male or female")
    if user.smoking_status not in {"never", "former", "current"}:
        raise ValueError("smoking_status must be never, former, or current")
    if user.education_level not in {None, "code_1", "code_2", "code_3", "code_4", "code_97"}:
        raise ValueError("education_level must be code_1..code_4, code_97, or null")
    alcohol_frequency = _integer_code("alcohol_frequency", user.alcohol_frequency, {1, 2, 3, 4, 5, 6, 8})
    region = np.nan if user.region is None else _integer_code("region", user.region, set(range(1, 18)))

    height = _number("height_cm", user.height_cm, 120, 220)
    weight = _number("weight_kg", user.weight_kg, 25, 250)
    systolic_bp = _optional_number("systolic_bp", user.systolic_bp, 50, 300)
    diastolic_bp = _optional_number("diastolic_bp", user.diastolic_bp, 30, 200)
    if not np.isnan(systolic_bp) and not np.isnan(diastolic_bp) and systolic_bp <= diastolic_bp:
        raise ValueError("systolic_bp must be greater than diastolic_bp")
    row = {
        "age": age,
        "height_cm": height,
        "weight_kg": weight,
        "waist_cm": _optional_number("waist_cm", user.waist_cm, 40, 200),
        "bmi": weight / (height / 100) ** 2,
        "systolic_bp": systolic_bp,
        "diastolic_bp": diastolic_bp,
        "sex": 1 if user.sex == "male" else 2,
        "current_smoker": int(user.smoking_status == "current"),
        "education": (np.nan if user.education_level in {None, "code_97"} else int(user.education_level[-1])),
        "region": region,
        "diabetes_family_history": _optional_binary("diabetes_family_history", user.diabetes_family_history),
        "hypertension_family_history": _optional_binary(
            "hypertension_family_history", user.hypertension_family_history
        ),
        "alcohol_frequency": alcohol_frequency,
    }
    return pd.DataFrame([row], columns=TODAY_MODEL_FEATURES)
