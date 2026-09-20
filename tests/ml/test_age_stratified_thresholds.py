import numpy as np
import pandas as pd

from src.ml.modeling.age_stratified_thresholds import (
    age_groups,
    evaluate_risk_bands,
    evaluate_threshold_policy,
    exploratory_sensitivity_analysis,
    select_age_thresholds,
    select_risk_band_cutoffs,
)


def test_age_groups_use_expected_boundaries() -> None:
    frame = pd.DataFrame({"age": [19, 44, 45, 64, 65, 90]})
    assert age_groups(frame).tolist() == ["19-44", "19-44", "45-64", "45-64", "65+", "65+"]


def test_age_thresholds_are_selected_from_each_validation_group() -> None:
    frame = pd.DataFrame(
        {
            "age": [30] * 8 + [50] * 8 + [70] * 8,
            "_target": ([0, 0, 0, 0, 1, 1, 1, 1]) * 3,
        }
    )
    probabilities = np.asarray(([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]) * 3)
    config = {
        "experiment_id": "test",
        "minimum_validation_positive_events": 4,
        "minimum_auprc_lift": 1.0,
        "knhanes": {
            "minimum_specificity_by_age": {"19-44": 0.5, "45-64": 0.5, "65+": 0.5},
            "threshold_grid": {"minimum": 0.1, "maximum": 0.8, "points": 8},
        },
    }
    thresholds, rows = select_age_thresholds(frame, probabilities, config)
    assert set(thresholds) == {"19-44", "45-64", "65+"}
    assert all(row["specificity"] >= 0.5 for row in rows)


def test_age_policy_uses_row_specific_thresholds() -> None:
    frame = pd.DataFrame(
        {
            "age": [30, 30, 50, 50, 70, 70],
            "_target": [0, 1, 0, 1, 0, 1],
        }
    )
    probabilities = np.asarray([0.3, 0.7, 0.3, 0.7, 0.3, 0.7])
    aggregate, per_group = evaluate_threshold_policy(
        frame,
        probabilities,
        {"19-44": 0.2, "45-64": 0.5, "65+": 0.8},
        0.5,
        0.5,
    )
    assert {row["policy"] for row in aggregate} == {"global", "age_stratified"}
    assert len(per_group) == 6


def test_sensitivity_analysis_keeps_policy_targets_separate() -> None:
    frame = pd.DataFrame(
        {
            "age": [30] * 8 + [50] * 8 + [70] * 8,
            "_target": ([0, 0, 0, 0, 1, 1, 1, 1]) * 3,
        }
    )
    probabilities = np.asarray(([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]) * 3)
    config = {
        "experiment_id": "test",
        "minimum_validation_positive_events": 4,
        "minimum_auprc_lift": 1.0,
        "exploratory_specificity_targets": [0.5, 0.75],
        "knhanes": {
            "minimum_specificity_by_age": {"19-44": 0.5, "45-64": 0.5, "65+": 0.5},
            "threshold_grid": {"minimum": 0.1, "maximum": 0.8, "points": 8},
        },
    }
    threshold_rows, aggregate_rows = exploratory_sensitivity_analysis(
        frame, frame, probabilities, probabilities, 0.5, 0.5, config
    )
    assert len(threshold_rows) == 6
    assert len(aggregate_rows) == 4
    assert {row["specificity_policy_target"] for row in aggregate_rows} == {0.5, 0.75}


def test_risk_band_cutoffs_are_validation_derived_and_ordered() -> None:
    frame = pd.DataFrame(
        {
            "age": [30] * 10 + [50] * 10 + [70] * 10,
            "_target": ([0, 0, 0, 0, 0, 1, 1, 1, 1, 1]) * 3,
        }
    )
    probabilities = np.asarray(([0.05, 0.1, 0.15, 0.2, 0.25, 0.55, 0.6, 0.7, 0.8, 0.9]) * 3)
    config = {
        "risk_band_policy": {
            "low_cutoff_minimum_recall": 0.9,
            "high_cutoff_minimum_specificity": 0.8,
        },
        "knhanes": {"threshold_grid": {"minimum": 0.01, "maximum": 0.99, "points": 99}},
    }
    cutoffs, rows = select_risk_band_cutoffs(frame, probabilities, config)
    assert len(rows) == 3
    assert all(values["low_cutoff"] < values["high_cutoff"] for values in cutoffs.values())
    band_rows = evaluate_risk_bands(frame, probabilities, cutoffs)
    assert len(band_rows) == 9
