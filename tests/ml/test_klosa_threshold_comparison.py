import pandas as pd
import pytest

from src.ml.evaluation.compare_klosa_thresholds import (
    choose_threshold_for_recall,
    evaluate_operating_points,
)
from src.ml.modeling.train_klosa_diabetes_sample import choose_threshold


def test_operating_points_select_on_validation_and_report_test_confusion() -> None:
    rows = evaluate_operating_points(
        validation_target=pd.Series([0, 0, 0, 1, 1]),
        validation_probabilities=pd.Series([0.1, 0.2, 0.6, 0.5, 0.9]).to_numpy(),
        test_target=pd.Series([0, 0, 1, 1]),
        test_probabilities=pd.Series([0.2, 0.8, 0.4, 0.9]).to_numpy(),
        target_recalls=[0.5, 1.0],
    )

    assert [row["target_validation_recall"] for row in rows] == [0.5, 1.0]
    assert rows[0]["threshold"] >= rows[1]["threshold"]
    for row in rows:
        assert row["test_recall"] == pytest.approx(
            row["test_true_positives"] / (row["test_true_positives"] + row["test_false_negatives"])
        )
        assert row["test_specificity"] == pytest.approx(
            row["test_true_negatives"] / (row["test_true_negatives"] + row["test_false_positives"])
        )


def test_fast_threshold_matches_training_rule() -> None:
    target = pd.Series([0, 0, 0, 1, 1, 1])
    probabilities = pd.Series([0.05, 0.20, 0.70, 0.40, 0.60, 0.90]).to_numpy()

    assert choose_threshold_for_recall(target, probabilities, 2 / 3) == pytest.approx(
        choose_threshold(target, probabilities, minimum_recall=2 / 3)
    )
