from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from app.core import config
from app.models.health import Prediction
from app.models.prediction_jobs import PredictionJob
from app.prediction.providers import ProviderResult
from app.services import ai_jobs
from tests.db_utils import init_sqlite_test_db, reset_tortoise


@pytest.mark.asyncio
async def test_demo_artifact_future_result_is_public_only_after_release_gate(monkeypatch) -> None:
    await init_sqlite_test_db()
    monkeypatch.setattr(config, "DEMO_ARTIFACT_INFERENCE_ENABLED", True)

    class Provider:
        async def predict(self, payload, *, as_of_date):
            del payload, as_of_date
            return ProviderResult(
                internal_score=0.031,
                risk_category="high",
                model_version="rf25-tuned-education4-v2",
                feature_schema_version="klosa_stage3_25features_education4_v2",
                input_schema_version="diabetes-incidence-api-education4-v2",
                preprocessing_version="train-median-indicator-mode-onehot-education4-v2",
                target_definition_version="next-observation-new-diabetes-v1",
                calibration_version="not_probability_calibrated-v1",
                model_artifact_digest=config.PREDICTION_MODEL_ARTIFACT_DIGEST,
                threshold_version=config.PREDICTION_THRESHOLD_VERSION,
                decision_threshold=config.PREDICTION_DECISION_THRESHOLD,
                promotion_status="approved",
                display_allowed=True,
                operational_model_activated=True,
            )

    monkeypatch.setattr(ai_jobs, "get_prediction_provider", lambda: Provider())
    try:
        job = await PredictionJob.create(
            job_id="future",
            task_type="diabetes_incidence",
            request_payload={},
            user_id=1,
            health_checkup_id=1,
        )
        await ai_jobs._complete_demo_prediction(job, {}, date(2026, 9, 18))
        prediction = await Prediction.get(job_id="future")

        assert prediction.result_status == "approved"
        assert prediction.risk_category == "high"
        assert prediction.internal_score == pytest.approx(0.031)
        assert prediction.display_allowed is True
        assert prediction.operational_model_activated is True
        assert prediction.decision_threshold == pytest.approx(config.PREDICTION_DECISION_THRESHOLD)
    finally:
        await reset_tortoise()


@pytest.mark.asyncio
async def test_demo_artifact_current_result_uses_pinned_manifest(monkeypatch) -> None:
    await init_sqlite_test_db()
    monkeypatch.setattr(config, "DEMO_ARTIFACT_INFERENCE_ENABLED", True)
    loaded = SimpleNamespace(
        manifest={
            "features": ["age", "sex"],
            "operational_model_activated": True,
            "artifact_sha256": config.CURRENT_SCREENING_MODEL_ARTIFACT_DIGEST,
            "threshold": config.CURRENT_SCREENING_DECISION_THRESHOLD,
        }
    )

    from src.ml.inference import diabetes_current_screening

    monkeypatch.setattr(diabetes_current_screening, "load_current_screening_model", lambda **kwargs: loaded)
    monkeypatch.setattr(
        diabetes_current_screening,
        "predict_with_loaded_current_model",
        lambda model, payload: {
            "risk_score_internal": 0.04,
            "screening_signal_detected": True,
            "model_version": config.CURRENT_SCREENING_MODEL_VERSION,
            "feature_schema_version": config.CURRENT_SCREENING_FEATURE_SCHEMA_VERSION,
            "threshold_version": config.CURRENT_SCREENING_THRESHOLD_VERSION,
        },
    )
    try:
        job = await PredictionJob.create(
            job_id="current",
            task_type="diabetes_current_screening",
            request_payload={},
            user_id=1,
            health_checkup_id=1,
        )
        await ai_jobs._complete_demo_current_screening(
            job,
            date(2026, 9, 18),
            {"age": 60, "sex": "female", "ignored": "service superset"},
        )
        prediction = await Prediction.get(job_id="current")

        assert prediction.result_status == "approved"
        assert prediction.risk_category == "high"
        assert prediction.internal_score == pytest.approx(0.04)
        assert prediction.display_allowed is True
        assert prediction.operational_model_activated is True
        assert prediction.decision_threshold == pytest.approx(config.CURRENT_SCREENING_DECISION_THRESHOLD)
    finally:
        await reset_tortoise()
