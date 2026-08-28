import pandas as pd
import pytest

from src.ml.preprocessing.build_klosa_diabetes_cohort import (
    TARGET,
    assert_model_matrix_is_safe,
    build_transition,
    summarize,
)


def test_build_transition_separates_t0_features_and_t1_target() -> None:
    t0 = pd.DataFrame(
        {
            "pid": [1, 2, 3],
            "w01A002_age": [45, 50, 55],
            "w01gender1": [1, 5, 1],
            "w01C105": [70, 60, 80],
            "w01C107": [170, 160, 180],
            "w01C108": [1, 5, 1],
            "w01C111": [3.0, None, 2.0],
            "w01C112": [30.0, None, 40.0],
            "w01smoke": [0, 1, 2],
            "w01Alc": [1, 2, 3],
            "w01chronic_b": [5, 5, 1],
            "w01mniw_y": [2006, 2006, 2006],
            "w01mniw_m": [9, 9, 9],
            "w01mniw_d": [1, 1, 1],
        }
    )
    t1 = pd.DataFrame(
        {
            "pid": [1, 2, 3],
            "w02chronic_b": [1, 5, 1],
            "w02C011": [1, 5, None],
            "w02mniw_y": [2008, 2008, 2008],
            "w02mniw_m": [9, 9, 9],
            "w02mniw_d": [1, 1, 1],
        }
    )

    cohort = build_transition(t0, t1, baseline_wave=1)

    assert cohort["pid"].tolist() == [1, 2]
    assert cohort[TARGET].tolist() == [1, 0]
    assert cohort.loc[cohort["pid"].eq(2), "exercise_days_per_week"].item() == 0
    assert cohort["outcome_wave"].eq(cohort["baseline_wave"] + 1).all()


def test_model_feature_allowlist_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unsafe model matrix"):
        assert_model_matrix_is_safe(["age", "diabetes_status_t1"])


def test_summary_reports_people_follow_up_and_transition_counts() -> None:
    t0 = pd.DataFrame(
        {
            "pid": [1, 2],
            "w01A002_age": [45, 60],
            "w01gender1": [1, 5],
            "w01C105": [70, 60],
            "w01C107": [170, 160],
            "w01C108": [1, 5],
            "w01C111": [3.0, None],
            "w01C112": [30.0, None],
            "w01smoke": [0, 1],
            "w01Alc": [1, 2],
            "w01chronic_b": [5, 5],
            "w01mniw_y": [2006, 2006],
            "w01mniw_m": [9, 9],
            "w01mniw_d": [1, 1],
        }
    )
    t1 = pd.DataFrame(
        {
            "pid": [1, 2],
            "w02chronic_b": [1, 5],
            "w02C011": [1, 5],
            "w02mniw_y": [2008, 2008],
            "w02mniw_m": [9, 9],
            "w02mniw_d": [1, 1],
        }
    )

    summary = summarize(build_transition(t0, t1, baseline_wave=1))

    assert summary["all_available"]["unique_people"] == 2
    assert summary["follow_up_days"]["median"] == 731.0
    assert summary["transitions"][0] == {
        "transition": "1_to_2",
        "person_periods": 2,
        "events": 1,
        "non_events": 1,
        "event_rate": 0.5,
    }
