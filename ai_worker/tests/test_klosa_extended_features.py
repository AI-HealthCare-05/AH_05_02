import pandas as pd

from ai_worker.ml.build_klosa_diabetes_extended_cohort import (
    COMORBIDITY_FEATURES,
    EXTENDED_MODEL_FEATURES,
    build_extended_transition,
)
from ai_worker.ml.train_klosa_diabetes_extended_features import (
    MODEL_NAMES,
    make_extended_pipeline,
)


def test_extended_transition_maps_t0_diagnoses_without_using_diabetes() -> None:
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
                f"w01{suffix}": [1, -9]
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

    cohort = build_extended_transition(t0, t1, 1)

    assert cohort.loc[0, "hypertension_diagnosis"] == "yes"
    assert pd.isna(cohort.loc[1, "hypertension_diagnosis"])
    assert "diabetes_diagnosis" not in EXTENDED_MODEL_FEATURES
    assert len(COMORBIDITY_FEATURES) == 8


def test_all_extended_models_include_sixteen_features() -> None:
    assert len(EXTENDED_MODEL_FEATURES) == 16
    for model_name in MODEL_NAMES:
        pipeline = make_extended_pipeline(model_name)
        assert list(pipeline.named_steps) == ["preprocessing", "classifier"]
