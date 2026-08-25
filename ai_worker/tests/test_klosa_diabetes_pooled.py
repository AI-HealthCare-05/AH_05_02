import pandas as pd
import pytest

from ai_worker.ml.build_klosa_diabetes_cohort import TARGET
from ai_worker.ml.train_klosa_diabetes_pooled import (
    describe_age_groups,
    logistic_experiment_identity,
    split_grouped_cohort,
    summarize_calibration,
)
from ai_worker.ml.train_klosa_diabetes_sample import evaluate, make_logistic_pipeline


def make_repeated_pid_cohort() -> pd.DataFrame:
    rows = []
    for pid in range(1, 41):
        for wave in (1, 2):
            rows.append(
                {
                    "pid": pid,
                    "baseline_wave": wave,
                    "age": 50 + pid % 35,
                    TARGET: int(pid % 4 == 0 and wave == 2),
                }
            )
    return pd.DataFrame(rows)


def test_pooled_split_keeps_every_pid_in_exactly_one_partition() -> None:
    cohort = make_repeated_pid_cohort()

    train, validation, test = split_grouped_cohort(cohort, random_state=42)

    pid_sets = [set(frame["pid"]) for frame in (train, validation, test)]
    assert not (pid_sets[0] & pid_sets[1])
    assert not (pid_sets[0] & pid_sets[2])
    assert not (pid_sets[1] & pid_sets[2])
    assert set.union(*pid_sets) == set(cohort["pid"])
    assert [len(pid_set) for pid_set in pid_sets] == [28, 6, 6]


def test_age_group_summary_reports_events_and_non_events() -> None:
    cohort = make_repeated_pid_cohort()

    groups = describe_age_groups(cohort)

    assert groups["45_to_64"]["person_periods"] > 0
    assert groups["65_to_74"]["person_periods"] > 0
    assert groups["75_plus"]["person_periods"] > 0
    for summary in groups.values():
        assert summary["events"] + summary["non_events"] == summary["person_periods"]


def test_evaluation_exposes_sensitivity_as_recall_alias() -> None:
    metrics = evaluate(
        pd.Series([0, 0, 1, 1]),
        probabilities=pd.Series([0.1, 0.8, 0.4, 0.9]).to_numpy(),
        threshold=0.5,
    )

    assert metrics["sensitivity"] == pytest.approx(0.5)
    assert metrics["sensitivity"] == metrics["recall"]


def test_calibration_summary_uses_all_rows_and_reports_ece() -> None:
    summary = summarize_calibration(
        pd.Series([0, 0, 0, 1, 0, 1, 0, 1]),
        probabilities=pd.Series([0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.60, 0.80]),
        n_bins=4,
    )

    assert sum(summary["bin_counts"]) == 8
    assert summary["actual_bins"] == 4
    assert 0 <= summary["expected_calibration_error"] <= 1
    assert summary["selection_policy"].startswith("reporting_only")


def test_balanced_logistic_has_distinct_version_and_class_weight() -> None:
    model_version, experiment = logistic_experiment_identity("balanced")
    model = make_logistic_pipeline(class_weight="balanced")

    assert model_version.endswith("logistic-balanced-v1")
    assert experiment.endswith("logistic_balanced_v1")
    assert model.named_steps["classifier"].class_weight == "balanced"
