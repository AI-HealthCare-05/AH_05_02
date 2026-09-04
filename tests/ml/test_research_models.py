from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import numpy as np
import pytest

from src.ml.inference import research_models as serving
from src.ml.inference.diabetes_first_interval_survival_ensemble import (
    DEFAULT_MANIFEST,
    EnsembleContractError,
    LoadedFirstIntervalEnsemble,
    _cumulative_curve,
)

ROOT = Path(__file__).resolve().parents[2]
AS_OF = date(2026, 8, 31)


@pytest.fixture
def payload():
    return json.loads((ROOT / "docs/api/examples/tuned_rf25_valid_input.json").read_text())


class Constant:
    def __init__(self, probability=0.1):
        self.probability = probability

    def predict_proba(self, frame):
        p = np.full(len(frame), self.probability)
        return np.column_stack([1 - p, p])


@pytest.fixture
def fake_models(monkeypatch):
    manifest = json.loads(serving.SHARED_MANIFEST.read_text())
    bundle = {
        "pipelines": {"logistic": Constant(), "random_forest": Constant()},
        "calibrators": {"logistic": Constant(), "random_forest": Constant()},
        "ensemble_weights": {"logistic": 0.7, "random_forest": 0.3},
    }
    monkeypatch.setattr(serving, "load_shared7", lambda _: (bundle, manifest))
    ensemble = {
        k: Constant() for k in ("rf_model", "survival_model", "rf_calibrator", "logistic_calibrator", "meta_model")
    }
    monkeypatch.setattr(
        serving,
        "load_ensemble",
        lambda _: LoadedFirstIntervalEnsemble(ensemble, json.loads(DEFAULT_MANIFEST.read_text())),
    )


def test_shared_frame_maps_only_seven_features(payload):
    frame = serving.shared7_frame(payload, as_of_date=AS_OF)
    assert tuple(frame.columns) == serving.FEATURES
    assert frame.iloc[0]["sex"] == 2 and frame.iloc[0]["current_smoker"] == 0
    assert frame.iloc[0]["bmi"] == pytest.approx(68 / 1.62**2)
    assert np.isnan(frame.iloc[0]["education"])
    payload.update(education_level="code_3", smoking_status="current", sex="male")
    row = serving.shared7_frame(payload, as_of_date=AS_OF).iloc[0]
    assert (row.education, row.current_smoker, row.sex) == (3, 1, 1)


@pytest.mark.parametrize(
    "change",
    [
        {"height_cm": None},
        {"height_cm": 0},
        {"weight_kg": float("nan")},
        {"birth_date": "1990-01-01"},
        {"birth_date": "1900-01-01"},
        {"education_level": "code_97"},
        {"previously_diagnosed_diabetes": True},
        {"sex": 2},
        {"smoking_status": "unknown"},
        {"fasting_glucose": 200},
    ],
)
@pytest.mark.parametrize("model", ["shared7", "first-interval"])
def test_invalid_input_rejected_before_model_load(payload, change, model):
    with pytest.raises(ValueError):
        serving.predict_research_model(model, {**payload, **change}, as_of_date=AS_OF)


@pytest.mark.parametrize("model", ["shared7", "first-interval"])
def test_missing_input_rejected(payload, model):
    payload.pop("height_cm")
    with pytest.raises(ValueError):
        serving.predict_research_model(model, payload, as_of_date=AS_OF)


@pytest.mark.parametrize("model", ["shared7", "first-interval"])
def test_deterministic_private_response(payload, fake_models, model):
    first = serving.predict_research_model(model, payload, as_of_date=AS_OF)
    assert first == serving.predict_research_model(model, payload, as_of_date=AS_OF)
    assert first["display_allowed"] is False
    assert first["model_version"] and first["threshold_version"]
    if model == "first-interval":
        scores = [p["cumulative_risk_signal"] for p in first["curve"]]
        assert scores == sorted(scores) and len(scores) == 9
        assert all(p["cumulative_risk"] is None for p in first["curve"])


def test_missing_and_corrupt_shared_artifact(tmp_path):
    serving.load_shared7.cache_clear()
    with pytest.raises(serving.ResearchArtifactUnavailableError):
        serving.load_shared7(str(tmp_path / "absent.joblib"))
    corrupt = tmp_path / "corrupt.joblib"
    corrupt.write_bytes(b"not a model")
    with pytest.raises(serving.ResearchModelContractError, match="SHA"):
        serving.load_shared7(str(corrupt))


def test_runtime_mismatch(monkeypatch):
    monkeypatch.setattr(serving.sklearn, "__version__", "1.9.0")
    with pytest.raises(serving.ResearchModelContractError):
        serving._runtime()


def test_nonfinite_curve_rejected(payload):
    from src.ml.preprocessing.diabetes_api_features import build_standard_model_frame, parse_diabetes_risk_input

    frame = build_standard_model_frame(parse_diabetes_risk_input(payload), as_of_date=AS_OF)
    bundle = {
        k: Constant(float("nan"))
        for k in ("rf_model", "survival_model", "rf_calibrator", "logistic_calibrator", "meta_model")
    }
    with pytest.raises(EnsembleContractError):
        _cumulative_curve(bundle, frame)


@pytest.mark.skipif(not os.environ.get("TEST_SHARED7_ARTIFACT"), reason="Private artifact not provisioned")
def test_actual_shared7_golden(payload):
    result = serving.predict_research_model(
        "shared7", payload, as_of_date=AS_OF, model_path=os.environ["TEST_SHARED7_ARTIFACT"]
    )
    assert result["risk_score_internal"] == pytest.approx(0.047658176973160, abs=1e-14)
    assert result == serving.predict_research_model(
        "shared7", payload, as_of_date=AS_OF, model_path=os.environ["TEST_SHARED7_ARTIFACT"]
    )
