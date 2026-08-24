import numpy as np
import pandas as pd

from ai_worker.ml.build_klosa_diabetes_mental_rhythm_cohort import (
    MENTAL_RHYTHM_EXTENDED_FEATURES,
    build_mental_rhythm_transition,
)
from ai_worker.ml.train_klosa_diabetes_extended_features import (
    make_extended_pipeline,
)


def _transition_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    t0 = pd.DataFrame(
        {
            "pid": [1, 2],
            "w01A002_age": [60, 70],
            "w01gender1": [1, 5],
            "w01C105": [70, 60],
            "w01C107": [170, 160],
            "w01C108": [1, 5],
            "w01C111": [3, -9],
            "w01C112": [30, -9],
            "w01smoke": [0, 2],
            "w01Alc": [2, 1],
            "w01chronic_b": [5, 5],
            "w01mniw_y": [2006, 2006],
            "w01mniw_m": [8, 8],
            "w01mniw_d": [1, 1],
            **{
                f"w01{suffix}": [5, 1]
                for suffix in [
                    "chronic_a",
                    "chronic_c",
                    "chronic_d",
                    "chronic_e",
                    "chronic_f",
                    "chronic_g",
                    "chronic_h",
                    "chronic_i",
                ]
            },
            "w01edu": [2, 4],
            "w01marital": [1, 4],
            "w01hhsize": [1, 3],
            "w01hhinc": [0, 999],
            "w01C144": [1, 4],
            "w01C148": [2, -9],
            "w01G026": [70, 101],
            "w01G027": [40, 50],
            "w01G030": [80, 30],
        }
    )
    t1 = pd.DataFrame(
        {
            "pid": [1, 2],
            "w02chronic_b": [1, 5],
            "w02C011": [1, 5],
            "w02mniw_y": [2008, 2008],
            "w02mniw_m": [8, 8],
            "w02mniw_d": [1, 1],
        }
    )
    return t0, t1


def test_stage_three_features_are_t0_only_and_stably_derived() -> None:
    t0, t1 = _transition_frames()
    cohort = build_mental_rhythm_transition(t0, t1, 1)

    assert cohort["depressed_feeling_last_week"].tolist() == [
        "code_1",
        "code_4",
    ]
    assert cohort.loc[0, "sleep_difficulty_last_week"] == "code_2"
    assert np.isnan(cohort.loc[1, "sleep_difficulty_last_week"])
    assert cohort["health_satisfaction_score"].tolist()[0] == 70
    assert np.isnan(cohort.loc[1, "health_satisfaction_score"])
    assert len(MENTAL_RHYTHM_EXTENDED_FEATURES) == 25


def test_stage_three_pipeline_uses_train_fitted_preprocessing() -> None:
    pipeline = make_extended_pipeline(
        "logistic_regression",
        additional_numeric_features=[
            "log_household_income",
            "health_satisfaction_score",
            "economic_satisfaction_score",
            "overall_quality_of_life_score",
        ],
        additional_categorical_features=[
            "education_level",
            "marital_status",
            "household_structure",
            "depressed_feeling_last_week",
            "sleep_difficulty_last_week",
        ],
    )
    preprocessing = pipeline.named_steps["preprocessing"]
    numeric_columns = preprocessing.transformers[0][2]
    categorical_columns = preprocessing.transformers[1][2]

    assert "health_satisfaction_score" in numeric_columns
    assert "depressed_feeling_last_week" in categorical_columns
