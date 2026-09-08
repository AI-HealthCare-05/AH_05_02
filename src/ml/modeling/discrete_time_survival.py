"""Pooled discrete-time hazard model and cumulative-risk projection."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.ml.preprocessing.build_klosa_diabetes_mental_rhythm_cohort import (
    MENTAL_RHYTHM_CATEGORICAL_FEATURES,
    MENTAL_RHYTHM_NUMERIC_FEATURES,
)
from src.ml.preprocessing.build_klosa_diabetes_socioeconomic_cohort import (
    SOCIOECONOMIC_CATEGORICAL_FEATURES,
    SOCIOECONOMIC_NUMERIC_FEATURES,
)
from src.ml.preprocessing.diabetes_api_features import STANDARD_MODEL_FEATURES

NUMERIC_25_FEATURES = [
    "age",
    "bmi",
    "exercise_days_per_week",
    "exercise_minutes",
    "log_household_income",
    "health_satisfaction_score",
    "economic_satisfaction_score",
    "overall_quality_of_life_score",
]
BASE_FEATURES = [*NUMERIC_25_FEATURES, *(f for f in STANDARD_MODEL_FEATURES if f not in NUMERIC_25_FEATURES)]
TIME_FEATURE = "interval_index"
MODEL_FEATURES = [*BASE_FEATURES, TIME_FEATURE]


def make_pooled_logistic_hazard_model(*, random_state: int = 42):
    """Create a regularized pooled-logistic discrete hazard pipeline."""

    from src.ml.modeling.train_klosa_diabetes_extended_features import make_extended_pipeline

    return make_extended_pipeline(
        "logistic_regression",
        random_state=random_state,
        additional_numeric_features=[
            *SOCIOECONOMIC_NUMERIC_FEATURES,
            *MENTAL_RHYTHM_NUMERIC_FEATURES,
        ],
        additional_categorical_features=[
            *SOCIOECONOMIC_CATEGORICAL_FEATURES,
            *MENTAL_RHYTHM_CATEGORICAL_FEATURES,
            TIME_FEATURE,
        ],
    )


def predict_cumulative_risk(
    model: Any,
    origins: pd.DataFrame,
    *,
    horizon_years: int,
) -> np.ndarray:
    """Convert interval hazards into monotonic cumulative risk for each origin."""

    if horizon_years not in range(2, 19, 2):
        raise ValueError(f"지원하지 않는 예측기간입니다: {horizon_years}")
    intervals = horizon_years // 2
    repeated = origins[BASE_FEATURES].loc[origins.index.repeat(intervals)].copy()
    repeated[TIME_FEATURE] = np.tile(np.arange(1, intervals + 1), len(origins))
    hazards = model.predict_proba(repeated[MODEL_FEATURES])[:, 1].reshape(len(origins), intervals)
    if not np.isfinite(hazards).all() or ((hazards < 0) | (hazards > 1)).any():
        raise ValueError("구간 hazard는 0과 1 사이의 유한한 값이어야 합니다.")
    return 1 - np.prod(1 - hazards, axis=1)
