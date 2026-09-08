from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
import pytest

from src.ml.modeling.knhanes_current_screening import (
    predict_artifact,
    select_threshold,
    threshold_metrics,
    validate_contract,
)
from src.ml.modeling.transformers import AnthropometricWaistEstimator


def test_waist_estimator_preserves_observed_and_fills_missing() -> None:
    frame = pd.DataFrame(
        {
            "height_cm": [160.0, 170.0, 180.0] * 40,
            "weight_kg": [55.0, 70.0, 90.0] * 40,
            "age": [30, 50, 70] * 40,
            "sex": [2, 1, 1] * 40,
            "waist_cm": [70.0, 85.0, 105.0] * 40,
        }
    )
    frame.loc[0, "waist_cm"] = np.nan
    transformer = AnthropometricWaistEstimator(seed=7).fit(frame.iloc[1:])
    transformed = transformer.transform(frame)
    assert transformed.loc[0, "waist_cm"] == pytest.approx(70.0, abs=8.0)
    assert transformed.loc[1, "waist_cm"] == 85.0
    assert transformed.loc[0, "waist_was_estimated"] == 1.0
    assert transformed.loc[1, "waist_was_estimated"] == 0.0
    assert transformed["waist_height_ratio"].notna().all()
    assert transformed.loc[0, "waist_minus_expected_cm"] == pytest.approx(0.0)
    assert transformed["waist_expected_cm"].notna().all()


def test_waist_estimator_joblib_round_trip(tmp_path) -> None:
    frame = pd.DataFrame(
        {
            "height_cm": [155.0, 165.0, 175.0, 185.0] * 30,
            "weight_kg": [50.0, 62.0, 78.0, 95.0] * 30,
            "age": [25, 40, 58, 72] * 30,
            "sex": [2, 2, 1, 1] * 30,
            "waist_cm": [65.0, 76.0, 91.0, 108.0] * 30,
        }
    )
    fitted = AnthropometricWaistEstimator(seed=11).fit(frame)
    artifact_path = tmp_path / "waist_estimator.joblib"
    joblib.dump(fitted, artifact_path)
    restored = joblib.load(artifact_path)

    sample = frame.iloc[[0]].copy()
    sample["waist_cm"] = np.nan
    transformed = restored.transform(sample)
    assert restored.__class__.__module__ == "src.ml.modeling.transformers"
    assert transformed["waist_cm"].notna().all()
    assert transformed.loc[sample.index[0], "waist_was_estimated"] == 1.0


def test_validate_contract_rejects_target_leakage() -> None:
    config = {
        "numeric_features": ["age", "hba1c"],
        "categorical_features": [],
        "leakage_denylist": ["hba1c"],
        "split_contract": {"train": [2016], "validation": [2021], "test": [2023]},
    }
    with pytest.raises(ValueError, match="leakage"):
        validate_contract(config)


def test_validate_contract_rejects_overlapping_years() -> None:
    config = {
        "numeric_features": ["age"],
        "categorical_features": [],
        "leakage_denylist": [],
        "split_contract": {"train": [2016, 2021], "validation": [2021], "test": [2023]},
    }
    with pytest.raises(ValueError, match="disjoint"):
        validate_contract(config)


def test_select_threshold_maximizes_recall_with_specificity_floor() -> None:
    y = np.array([0, 0, 0, 0, 0, 1, 1, 1])
    probabilities = np.array([0.05, 0.10, 0.20, 0.45, 0.55, 0.30, 0.60, 0.90])
    threshold, metrics = select_threshold(y, probabilities, minimum_specificity=0.6)
    assert metrics["specificity"] >= 0.6
    assert metrics["recall"] == pytest.approx(1.0)
    assert threshold == pytest.approx(0.30)


def test_threshold_metrics_reports_confusion_matrix() -> None:
    y = np.array([0, 0, 1, 1])
    probabilities = np.array([0.1, 0.8, 0.7, 0.9])
    metrics = threshold_metrics(y, probabilities, 0.5)
    assert metrics["tn"] == 1
    assert metrics["fp"] == 1
    assert metrics["fn"] == 0
    assert metrics["tp"] == 2
    assert metrics["recall"] == pytest.approx(1.0)
    assert metrics["specificity"] == pytest.approx(0.5)


def test_predict_artifact_rejects_missing_features() -> None:
    artifact = {"features": ["age", "bmi"]}
    with pytest.raises(ValueError, match="bmi"):
        predict_artifact(artifact, pd.DataFrame({"age": [50]}))
