import numpy as np

from src.ml.modeling.klosa_full_retrain import (
    brier_reference_metrics,
    expected_calibration_error,
    reliability_bins,
    select_adaptive_threshold,
)


def test_brier_skill_score_is_zero_for_null_model():
    y = np.array([0, 0, 1, 0])
    probability = float(y.mean())
    probabilities = np.full(len(y), probability)

    metrics = brier_reference_metrics(y, probabilities, probability)

    assert metrics["brier_skill_score"] == 0.0


def test_brier_skill_score_is_positive_for_better_probabilities():
    y = np.array([0, 0, 1, 1])
    probabilities = np.array([0.1, 0.2, 0.8, 0.9])

    metrics = brier_reference_metrics(y, probabilities, 0.5)

    assert metrics["brier_skill_score"] > 0


def test_reliability_bins_retain_all_rows_and_compute_ece():
    y = np.array([0, 0, 0, 1, 1, 1])
    probabilities = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])

    curve = reliability_bins(y, probabilities, bins=3, model_name="candidate")

    assert int(curve["n"].sum()) == len(y)
    assert expected_calibration_error(curve) >= 0


def test_reliability_bins_support_constant_null_probability():
    y = np.array([0, 0, 1, 0])
    curve = reliability_bins(y, np.full(len(y), 0.25), bins=10, model_name="null")

    assert len(curve) == 1
    assert int(curve.loc[0, "n"]) == len(y)


def test_adaptive_threshold_supports_low_calibrated_probabilities():
    y = np.array([0, 0, 0, 0, 1, 1])
    probabilities = np.array([0.001, 0.002, 0.003, 0.004, 0.005, 0.006])
    config = {
        "threshold_grid": {"minimum": 0.01, "maximum": 0.99, "points": 99},
        "selection_constraints": {
            "minimum_specificity": 0.5,
            "minimum_auprc_lift": 1.0,
        },
    }

    threshold, metrics = select_adaptive_threshold(y, probabilities, config)

    assert threshold < 0.01
    assert metrics["recall"] == 1.0
    assert metrics["specificity"] >= 0.5
