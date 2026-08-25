from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ml.modeling.recall_ensemble import (  # noqa: E402
    _blend_weights,
    _stable_sample,
    metric_row,
    select_threshold,
)


def test_recall_metric_cannot_hide_all_positive_predictions() -> None:
    metrics = metric_row(np.array([0, 0, 0, 1]), np.ones(4), 0.5)
    assert metrics["recall"] == 1.0
    assert metrics["specificity"] == 0.0
    assert metrics["predicted_positive_rate"] == 1.0


def test_subgroup_metric_handles_no_positive_cases() -> None:
    metrics = metric_row(np.array([0, 0, 0]), np.array([0.1, 0.2, 0.3]), 0.5)

    assert np.isnan(metrics["auroc"])
    assert np.isnan(metrics["auprc"])
    assert metrics["specificity"] == 1.0


def test_threshold_selection_applies_specificity_constraint() -> None:
    y = np.array([0, 0, 0, 0, 1, 1])
    probabilities = np.array([0.1, 0.2, 0.3, 0.6, 0.55, 0.9])
    config = {
        "threshold_grid": {"minimum": 0.1, "maximum": 0.9, "points": 9},
        "selection_constraints": {"minimum_specificity": 0.5, "minimum_auprc_lift": 1.0},
    }
    threshold, metrics = select_threshold(y, probabilities, config)
    assert 0.1 <= threshold <= 0.9
    assert metrics["constraints_passed"]
    assert metrics["specificity"] >= 0.5


def test_stable_sample_is_reproducible_and_retains_labels() -> None:
    frame = pd.DataFrame(
        {
            "_row_key": [f"r{i}" for i in range(100)],
            "age": [30] * 50 + [70] * 50,
            "_target": [0, 1] * 50,
        }
    )
    first = _stable_sample(frame, 20, 7, "knhanes", "train")
    second = _stable_sample(frame, 20, 7, "knhanes", "train")
    assert first["_row_key"].tolist() == second["_row_key"].tolist()
    assert set(first["_target"]) == {0, 1}


def test_blend_weights_sum_to_one_and_use_multiple_models() -> None:
    weights = _blend_weights(["a", "b", "c"], 0.5)
    assert weights
    assert all(sum(item.values()) == pytest.approx(1.0) for item in weights)
    assert all(sum(value > 0 for value in item.values()) >= 2 for item in weights)
