from __future__ import annotations

import json

import pytest

from src.ml.inference import diabetes_current_screening as current


def test_registry_manifest_separates_current_screening_from_future_incidence() -> None:
    manifest = json.loads(current.DEFAULT_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["model_key"] == "diabetes_current_screening"
    assert manifest["task_type"] == "current_cross_sectional_screening"
    assert manifest["threshold_scope"] == "current_cross_sectional_screening"
    assert len(manifest["external_input_features"]) == 22
    assert len(manifest["internal_derived_features"]) == 4
    assert manifest["features"] == manifest["external_input_features"]
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
        "external_input_features": ["age", "bmi"],
        "task_type": "current_cross_sectional_screening",
        "threshold_scope": "current_cross_sectional_screening",
    }
    loaded = current.LoadedCurrentScreeningModel(artifact={}, manifest=manifest)
    monkeypatch.setattr(current, "predict_artifact", lambda artifact, frame: [0.3])
    monkeypatch.setattr(current, "_validate_service_input", lambda payload: None)

    result = current.predict_with_loaded_current_model(loaded, {"age": 50, "bmi": 25.0})

    assert result["prediction_type"] == "current_screening"
    assert result["screening_signal_detected"] is True
    assert result["output_status"] == "research_challenger_not_operationally_approved"
    assert result["display_allowed"] is False
    assert result["threshold_scope"] == "current_cross_sectional_screening"
    assert "진단이 아닙니다" in result["disclaimer"]


def test_input_contract_requires_exact_external_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    loaded = current.LoadedCurrentScreeningModel(
        artifact={},
        manifest={"features": ["age"], "external_input_features": ["age"], "threshold": 0.2},
    )
    monkeypatch.setattr(current, "predict_artifact", lambda artifact, frame: [0.1])

    with pytest.raises(ValueError, match="Supply exactly"):
        current.predict_with_loaded_current_model(loaded, {"age": 50, "glucose": 200})


def test_service_boundary_rejects_ineligible_age_and_negative_weight() -> None:
    valid = {
        "age": 60,
        "height_cm": 170,
        "weight_kg": 70,
        "waist_cm": 85,
        "bmi": 24.2,
        "walking_days": 3,
        "energy_kcal": 2000,
        "protein_g": 70,
        "fat_g": 60,
        "carbohydrate_g": 280,
        "sodium_mg": 2500,
        "sex": 1,
        "region": 1,
        "urban": 1,
        "education": 3,
        "income_quartile": 2,
        "household_income_quartile": 2,
        "hypertension_family_history": 0,
        "diabetes_family_history": 0,
        "current_smoker": 0,
        "alcohol_frequency": 1,
        "aerobic_activity": 1,
    }

    with pytest.raises(ValueError, match="age is outside"):
        current._validate_service_input({**valid, "age": 18})
    with pytest.raises(ValueError, match="weight_kg is outside"):
        current._validate_service_input({**valid, "weight_kg": -1})
    current._validate_service_input({**valid, "waist_cm": None})


def test_missing_manifest_is_reported() -> None:
    with pytest.raises(current.CurrentScreeningArtifactUnavailableError):
        current.load_current_screening_model(manifest_path=current.REPOSITORY_ROOT / "missing-manifest.json")
