from __future__ import annotations

import pandas as pd

from src.ml.preprocessing.build_klosa_discrete_survival_cohort import (
    HORIZON_YEARS,
    SURVIVAL_EVENT,
    build_discrete_survival_cohort,
    horizon_evaluation_frame,
)


def _base() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "pid": [1, 1, 2, 3],
            "baseline_wave": [1, 2, 1, 1],
            "diabetes_status_t0": [5, 5, 5, 5],
            "age": [60, 62, 70, 80],
        }
    )


def _statuses() -> dict[int, pd.DataFrame]:
    return {
        2: pd.DataFrame({"pid": [1, 2, 3], "diabetes_status": [5, 5, 5]}),
        3: pd.DataFrame({"pid": [1, 2, 3], "diabetes_status": [1, -9, 5]}),
        4: pd.DataFrame({"pid": [1, 2, 3], "diabetes_status": [1, 5, 5]}),
    }


def test_survival_cohort_stops_at_event_or_first_unknown_status() -> None:
    cohort = build_discrete_survival_cohort(_base(), _statuses(), feature_columns=["age"])

    pid1 = cohort.loc[cohort["pid"].eq(1)]
    pid2 = cohort.loc[cohort["pid"].eq(2)]
    pid3 = cohort.loc[cohort["pid"].eq(3)]
    assert pid1["origin_wave"].eq(1).all()
    assert pid1[SURVIVAL_EVENT].tolist() == [0, 1]
    assert pid2[SURVIVAL_EVENT].tolist() == [0]
    assert pid3[SURVIVAL_EVENT].tolist() == [0, 0, 0]


def test_horizon_frame_excludes_early_censoring_and_labels_prior_event() -> None:
    cohort = build_discrete_survival_cohort(_base(), _statuses(), feature_columns=["age"])
    four_year = horizon_evaluation_frame(cohort, horizon_years=4, feature_columns=["age"])

    assert four_year["pid"].tolist() == [1, 3]
    assert four_year["target"].tolist() == [1, 0]
    assert HORIZON_YEARS == (2, 4, 6, 8, 10, 12, 14, 16, 18)
