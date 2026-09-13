"""Opt-in golden tests for local-only service candidate artifacts."""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import pytest

from src.ml.inference import research_models
from src.ml.inference.diabetes_standard import ModelArtifactUnavailableError

ROOT = Path(__file__).resolve().parents[2]
AS_OF_DATE = date(2026, 8, 31)


def _payload() -> dict:
    return json.loads((ROOT / "docs/api/examples/tuned_rf25_valid_input.json").read_text(encoding="utf-8"))


def test_missing_service_artifacts_fail_closed(tmp_path: Path) -> None:
    missing = str(tmp_path / "missing.joblib")
    research_models.load_shared8.cache_clear()
    research_models.load_tomorrow_rf25.cache_clear()
    with pytest.raises(research_models.ResearchArtifactUnavailableError):
        research_models.load_shared8(missing)
    with pytest.raises(ModelArtifactUnavailableError):
        research_models.load_tomorrow_rf25(missing)


@pytest.mark.skipif(not os.environ.get("TEST_SHARED8_ARTIFACT"), reason="Today artifact not provisioned")
def test_actual_today_shared8_is_reproducible() -> None:
    path = os.environ["TEST_SHARED8_ARTIFACT"]
    first = research_models.predict_research_model("shared8-waist", _payload(), as_of_date=AS_OF_DATE, model_path=path)
    second = research_models.predict_research_model("shared8-waist", _payload(), as_of_date=AS_OF_DATE, model_path=path)

    assert first == second
    assert first["risk_score_internal"] == pytest.approx(0.057802753905042, abs=1e-14)
    assert first["screening_signal_detected"] is True
    assert first["artifact_sha256"] == "aceafb1011afed055da727f63c996f1e35a711e0e01f3a38c349360d2f3ee8fc"
    assert first["display_allowed"] is False
    assert first["explanation"]["method"] == "exact_grouped_shap_missing_reference_v1"
    assert first["explanation"]["additivity_verified"] is True
    assert len(first["explanation"]["items"]) <= 3


@pytest.mark.skipif(not os.environ.get("TEST_RF25_ARTIFACT"), reason="Tomorrow artifact not provisioned")
def test_actual_tomorrow_rf25_is_reproducible() -> None:
    path = os.environ["TEST_RF25_ARTIFACT"]
    first = research_models.predict_research_model("tomorrow-rf25", _payload(), as_of_date=AS_OF_DATE, model_path=path)
    second = research_models.predict_research_model("tomorrow-rf25", _payload(), as_of_date=AS_OF_DATE, model_path=path)

    assert first == second
    assert first["risk_score"] == pytest.approx(0.022053512988, abs=1e-14)
    assert first["risk_category"] == "high"
    assert first["artifact_sha256"] == "e5067dacd50006b8d7681ef9e558a2a3488913ae1db58d15632c842623c05bf8"
    assert first["display_allowed"] is False
    assert first["explanation"]["method"] == "treeshap_tree_path_dependent_v1"
    assert first["explanation"]["additivity_verified"] is True
    assert len(first["explanation"]["items"]) <= 3
