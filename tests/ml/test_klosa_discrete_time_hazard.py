from __future__ import annotations

import pandas as pd
import pytest

from src.ml.modeling.klosa_discrete_time_hazard import (
    hazards_to_curve,
    make_person_period,
)


def test_make_person_period_stops_after_first_diagnosis() -> None:
    panel = pd.DataFrame(
        {
            "pid": [1, 1, 1, 1, 2, 2],
            "survey_year": [2006, 2008, 2010, 2012, 2006, 2008],
            "diabetes_dx": [0, 0, 1, 1, 0, 0],
            "age": [50, 52, 54, 56, 60, 62],
            "bmi": [23.0, 24.0, 25.0, 25.0, 22.0, 22.5],
        }
    )

    result = make_person_period(panel, ["age", "bmi"])

    participant_one = result.loc[result["pid"] == 1]
    assert participant_one["event_next_interval"].tolist() == [0, 1]
    assert participant_one["interval_start"].tolist() == [2006, 2008]
    assert len(result.loc[result["pid"] == 2]) == 1


def test_make_person_period_rejects_target_leakage() -> None:
    panel = pd.DataFrame(
        {
            "pid": [1, 1],
            "survey_year": [2006, 2008],
            "diabetes_dx": [0, 1],
            "future_diabetes_diagnosis": [1, 1],
        }
    )

    with pytest.raises(ValueError, match="leakage"):
        make_person_period(panel, ["future_diabetes_diagnosis"])


def test_hazards_to_curve_uses_product_limit() -> None:
    result = hazards_to_curve([0.03, 0.04, 0.05])

    assert result["approx_horizon_years"].tolist() == [2.0, 4.0, 6.0]
    assert result.iloc[-1]["cumulative_risk_signal"] == pytest.approx(1 - (1 - 0.03) * (1 - 0.04) * (1 - 0.05))
