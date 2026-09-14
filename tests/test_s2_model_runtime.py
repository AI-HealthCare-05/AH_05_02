from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_worker.core import config
from ai_worker.handlers import run_task


@pytest.fixture
def common_input() -> dict:
    return {
        "birth_date": "1970-04-12",
        "sex": "female",
        "height_cm": 162,
        "weight_kg": 68,
        "smoking_status": "never",
        "current_drinker": False,
        "regular_exercise": True,
        "exercise_days_per_week": 3,
        "exercise_minutes": 30,
        "previously_diagnosed_diabetes": False,
    }


@pytest.mark.asyncio
async def test_s2_current_worker_returns_safe_real_model_shape(
    monkeypatch: pytest.MonkeyPatch,
    common_input: dict,
) -> None:
    from src.ml.inference import research_models

    monkeypatch.setattr(config, "S2_MODEL_RUNTIME_ENABLED", True)
    monkeypatch.setattr(
        research_models,
        "predict_research_model",
        lambda *_args, **_kwargs: {
            "model_key": "diabetes_current_screening",
            "task_type": "current_cross_sectional_screening",
            "threshold_scope": "current_screening",
            "model_version": "knhanes-shared7-sk180-research-v1",
            "feature_schema_version": "knhanes-shared7-v1",
            "input_schema_version": "diabetes-incidence-api-25features-v1",
            "calibration_version": "shared7-oof-platt-v1",
            "risk_score_internal": 0.8,
            "screening_signal_detected": True,
            "artifact_sha256": "abc",
            "threshold_version": "threshold-v1",
            "output_status": "research_candidate_not_operationally_approved",
            "disclaimer": "not diagnosis",
        },
    )
    result = await run_task(
        "diabetes_current_screening",
        {"input": common_input, "as_of_date": "2026-09-07"},
    )
    assert result["preview_signal_level"] == "high"
    assert result["preview_only"] is True
    assert result["risk_category"] is None
    assert result["display_allowed"] is False
    assert result["operational_model_activated"] is False


@pytest.mark.asyncio
async def test_s2_future_worker_exposes_only_signal_horizons(
    monkeypatch: pytest.MonkeyPatch,
    common_input: dict,
) -> None:
    from src.ml.inference import research_models

    monkeypatch.setattr(config, "S2_MODEL_RUNTIME_ENABLED", True)
    monkeypatch.setattr(
        research_models,
        "load_ensemble",
        lambda *_args, **_kwargs: SimpleNamespace(manifest={"artifact_sha256": "def"}),
    )
    monkeypatch.setattr(
        research_models,
        "predict_research_model",
        lambda *_args, **_kwargs: {
            "model_key": "diabetes_incidence_multihorizon",
            "task_type": "future_incidence_risk_screening",
            "threshold_scope": "future_cumulative_incidence_by_horizon",
            "model_version": "rf25-first-interval-survival-ensemble-v1",
            "feature_schema_version": "future-v1",
            "input_schema_version": "input-v1",
            "output_definition_version": "output-v1",
            "calibration_version": "calibration-v1",
            "threshold_version": "threshold-v1",
            "risk_curve_status": "unavailable",
            "output_status": "research_candidate_not_operationally_approved",
            "disclaimer": "not diagnosis",
            "curve": [
                {
                    "horizon_years": year,
                    "projected_age": 56 + year,
                    "cumulative_risk_signal": 0.1 * index,
                    "screening_signal_detected": index > 1,
                }
                for index, year in enumerate((2, 4, 6, 8), start=1)
            ],
        },
    )
    result = await run_task(
        "diabetes_incidence",
        {"input": common_input, "as_of_date": "2026-09-07"},
    )
    assert result["preview_only"] is True
    assert result["risk_category"] is None
    assert result["display_allowed"] is False
    assert [point["display_label"].split("년", 1)[0] for point in result["age_risk_forecast"]["points"]] == [
        "2",
        "4",
        "6",
    ]
    assert all("display_percent" not in point for point in result["age_risk_forecast"]["points"])


def test_frontend_accepts_backend_marked_preview_without_enabling_public_display() -> None:
    config_path = Path(__file__).resolve().parents[1] / "src/frontend/app.js"
    script = config_path.read_text(encoding="utf-8")
    assert config_path.is_file()
    assert "prediction?.preview_only === true" in script
    assert "prediction.preview_signal_level" in script
    assert "prediction.display_allowed !== false" in script
