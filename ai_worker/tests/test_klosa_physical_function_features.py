import numpy as np
import pandas as pd

from ai_worker.ml.build_klosa_diabetes_physical_function_cohort import (
    PHYSICAL_FUNCTION_EXTENDED_FEATURES,
    build_physical_function_transition,
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
            "w01G026": [70, 50],
            "w01G027": [40, 50],
            "w01G030": [80, 30],
            "w01Adl": [0, 8],
            "w01iadl": [2, 10],
            "w01mgrip": [32.5, 99],
            "w01C056": [1, 5],
            "w01C212": [1, 3],
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


def test_stage_four_features_are_t0_only_and_plausibly_derived() -> None:
    t0, t1 = _transition_frames()
    cohort = build_physical_function_transition(t0, t1, 1)

    assert cohort.loc[0, "adl_limitation_count"] == 0
    assert np.isnan(cohort.loc[1, "adl_limitation_count"])
    assert cohort["iadl_limitation_count"].tolist() == [2, 10]
    assert cohort.loc[0, "mean_grip_strength_kg"] == 32.5
    assert np.isnan(cohort.loc[1, "mean_grip_strength_kg"])
    assert cohort["recent_fall_history"].tolist() == [True, False]
    assert cohort["nearby_outing_assistance"].tolist() == [
        "code_1",
        "code_3",
    ]
    assert len(PHYSICAL_FUNCTION_EXTENDED_FEATURES) == 30
