from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import pytest

from src.ml.inference.diabetes_first_interval_survival_ensemble import (
    EnsembleArtifactUnavailableError,
    load_first_interval_ensemble,
    predict_first_interval_survival_ensemble,
)

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = Path(
    os.environ.get(
        "TEST_FIRST_INTERVAL_ARTIFACT",
        str(
            ROOT
            / "models/artifacts/candidates/diabetes_incidence/rf25-first-interval-survival-ensemble-v1/model.joblib"
        ),
    )
)
INPUT_PATH = ROOT / "docs/api/examples/tuned_rf25_valid_input.json"
RESPONSE_PATH = ROOT / ("docs/api/examples/first_interval_survival_ensemble_response.actual.json")


def _payload() -> dict:
    return json.loads(INPUT_PATH.read_text(encoding="utf-8"))


@pytest.mark.skipif(not MODEL_PATH.is_file(), reason="Private artifact not provisioned; synthetic tests run in CI")
def test_fixed_input_is_deterministic_versioned_and_monotonic() -> None:
    first = predict_first_interval_survival_ensemble(_payload(), as_of_date=date(2026, 8, 31), model_path=MODEL_PATH)
    second = predict_first_interval_survival_ensemble(_payload(), as_of_date=date(2026, 8, 31), model_path=MODEL_PATH)

    assert first == second
    assert first == json.loads(RESPONSE_PATH.read_text(encoding="utf-8"))
    assert first["model_version"] == "rf25-first-interval-survival-ensemble-v1"
    assert first["display_allowed"] is False
    assert first["risk_curve_status"] == "unavailable"
    scores = [point["cumulative_risk_signal"] for point in first["curve"]]
    assert scores == sorted(scores)


@pytest.mark.skipif(not MODEL_PATH.is_file(), reason="Private artifact not provisioned; synthetic tests run in CI")
def test_missing_required_and_unsupported_age_are_rejected() -> None:
    missing = _payload()
    missing.pop("height_cm")
    with pytest.raises(ValueError, match="height_cm"):
        predict_first_interval_survival_ensemble(missing, as_of_date=date(2026, 8, 31), model_path=MODEL_PATH)

    unsupported = {**_payload(), "birth_date": "1990-02-14"}
    with pytest.raises(ValueError, match="outside the model-supported range"):
        predict_first_interval_survival_ensemble(unsupported, as_of_date=date(2026, 8, 31), model_path=MODEL_PATH)


def test_missing_artifact_has_clear_error(tmp_path: Path) -> None:
    with pytest.raises(EnsembleArtifactUnavailableError, match="artifact is missing"):
        load_first_interval_ensemble(model_path=tmp_path / "missing.joblib")
