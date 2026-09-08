from __future__ import annotations

import json

import pytest

from src.ml.inference import diabetes_current_screening as current


def test_registry_manifest_separates_current_screening_from_future_incidence() -> None:
    manifest = json.loads(current.DEFAULT_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["model_key"] == "diabetes_current_screening"
    assert manifest["task_type"] == "current_cross_sectional_screening"
    assert "future_incidence_probability" in manifest["prohibited_use"]
    assert "score_combination_with_diabetes_incidence" in manifest["prohibited_use"]


def test_prediction_returns_screening_not_diagnosis(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = {
        "model_key": "diabetes_current_screening",
        "model_version": "test-v1",
        "feature_schema_version": "schema-v1",
        "threshold_version": "threshold-v1",
        "threshold": 0.2,
        "features": ["age", "bmi"],
    }
    loaded = current.LoadedCurrentScreeningModel(artifact={}, manifest=manifest)
    monkeypatch.setattr(current, "predict_artifact", lambda artifact, frame: [0.3])

    result = current.predict_with_loaded_current_model(loaded, {"age": 50, "bmi": 25.0})

    assert result["prediction_type"] == "current_screening"
    assert result["screening_signal_detected"] is True
    assert result["output_status"] == "screening_not_diagnosis"
    assert "진단이 아닙니다" in result["disclaimer"]


def test_unknown_input_field_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    loaded = current.LoadedCurrentScreeningModel(
        artifact={},
        manifest={"features": ["age"], "threshold": 0.2},
    )
    monkeypatch.setattr(current, "predict_artifact", lambda artifact, frame: [0.1])

    with pytest.raises(current.CurrentScreeningContractError, match="unknown input fields"):
        current.predict_with_loaded_current_model(loaded, {"age": 50, "glucose": 200})


def test_missing_manifest_is_reported() -> None:
    with pytest.raises(current.CurrentScreeningArtifactUnavailableError):
        current.load_current_screening_model(manifest_path=current.REPOSITORY_ROOT / "missing-manifest.json")
