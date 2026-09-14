from __future__ import annotations

import pandas as pd
import pytest

from src.ml.preprocessing.build_klosa_diabetes_cohort import TARGET
from src.ml.preprocessing.build_klosa_diabetes_multihorizon_cohort import (
    HORIZON_TARGETS,
    build_cumulative_horizon_cohort,
)


def _base() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "pid": [1, 2, 3, 4],
            "baseline_wave": [1, 1, 1, 1],
            "diabetes_status_t0": [5, 5, 5, 5],
            "diabetes_status_t1": [5, 1, 5, 5],
            TARGET: [0, 1, 0, 0],
            "age": [60, 61, 62, 63],
        }
    )


def _statuses() -> dict[int, pd.DataFrame]:
    return {
        2: pd.DataFrame({"pid": [1, 2, 3, 4], "diabetes_status": [5, 1, 5, 5]}),
        3: pd.DataFrame({"pid": [1, 2, 3, 4], "diabetes_status": [1, 1, 5, -9]}),
        4: pd.DataFrame({"pid": [1, 2, 3, 4], "diabetes_status": [1, 1, 1, 5]}),
        5: pd.DataFrame({"pid": [1, 2, 3, 4], "diabetes_status": [1, 1, 1, 5]}),
    }


def test_four_year_target_is_cumulative_and_excludes_unobserved() -> None:
    cohort = build_cumulative_horizon_cohort(_base(), horizon_years=4, status_by_wave=_statuses())

    assert cohort["pid"].tolist() == [1, 2, 3]
    assert cohort[HORIZON_TARGETS[4]].tolist() == [1, 1, 0]
    assert cohort["horizon_outcome_wave"].eq(3).all()


def test_eight_year_target_counts_any_prior_diagnosis() -> None:
    cohort = build_cumulative_horizon_cohort(_base(), horizon_years=8, status_by_wave=_statuses())

    assert cohort["pid"].tolist() == [1, 2, 3]
    assert cohort[HORIZON_TARGETS[8]].tolist() == [1, 1, 1]


def test_six_year_target_counts_any_prior_diagnosis() -> None:
    cohort = build_cumulative_horizon_cohort(_base(), horizon_years=6, status_by_wave=_statuses())

    assert cohort["pid"].tolist() == [1, 2, 3]
    assert cohort[HORIZON_TARGETS[6]].tolist() == [1, 1, 1]
    assert cohort["horizon_outcome_wave"].eq(4).all()


def test_unknown_horizon_is_rejected() -> None:
    with pytest.raises(ValueError, match="지원하지 않는"):
        build_cumulative_horizon_cohort(_base(), horizon_years=10, status_by_wave=_statuses())
