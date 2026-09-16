import numpy as np
import pandas as pd

from src.ml.modeling.train_klosa_diabetes_extended_features import (
    make_extended_pipeline,
)
from src.ml.preprocessing.build_klosa_diabetes_socioeconomic_cohort import (
    SOCIOECONOMIC_EXTENDED_FEATURES,
    build_socioeconomic_transition,
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


def test_socioeconomic_features_are_t0_only_and_stably_derived() -> None:
    t0, t1 = _transition_frames()
    cohort = build_socioeconomic_transition(t0, t1, 1)

    assert cohort["education_level"].tolist() == ["code_2", "code_4"]
    assert cohort["marital_status"].tolist() == ["code_1", "code_4"]
    assert cohort["household_structure"].tolist() == [
        "single_person",
        "multi_person",
    ]
    assert cohort["log_household_income"].tolist() == [0, np.log1p(999)]
    assert len(SOCIOECONOMIC_EXTENDED_FEATURES) == 20


def test_stage_two_pipeline_adds_income_to_train_fitted_numeric_preprocessing() -> None:
    pipeline = make_extended_pipeline(
        "logistic_regression",
        additional_numeric_features=["log_household_income"],
        additional_categorical_features=[
            "education_level",
            "marital_status",
            "household_structure",
        ],
    )
    numeric_columns = pipeline.named_steps["preprocessing"].transformers[0][2]

    assert "log_household_income" in numeric_columns


def test_unknown_socioeconomic_category_is_sklearn_compatible_nan() -> None:
    t0, t1 = _transition_frames()
    t0.loc[0, "w01edu"] = -9

    cohort = build_socioeconomic_transition(t0, t1, 1)

    assert np.isnan(cohort.loc[0, "education_level"])
