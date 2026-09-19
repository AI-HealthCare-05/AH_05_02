from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from app.core import config
from app.models.health import Prediction, RiskFactor
from app.models.prediction_jobs import PredictionJob
from app.prediction.providers import ProviderResult
from app.services import ai_jobs
from tests.db_utils import init_sqlite_test_db, reset_tortoise


def approved_explanation() -> dict[str, object]:
    return {
        "status": "approved",
        "display_allowed": True,
        "shap_claimed": True,
        "additivity_verified": True,
        "selection_status": "complete",
        "explanation_version": "three-factor-shap-v1",
        "items": [
            {
                "feature": "age",
                "display_name": "나이",
                "direction": "increase",
                "contribution": 0.01,
                "modifiable": False,
                "message": "입력 정보가 기준값 대비 당뇨 위험을 높이는 방향으로 반영되었습니다.",
            }
        ],
    }


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
async def test_demo_artifact_future_persists_independently_approved_xai(monkeypatch) -> None:
    await init_sqlite_test_db()
    monkeypatch.setattr(config, "DEMO_ARTIFACT_INFERENCE_ENABLED", True)
    monkeypatch.setattr(config, "XAI_DISPLAY_ALLOWED", True)

    class Provider:
        async def predict(self, payload, *, as_of_date):
            del payload, as_of_date
            return ProviderResult(
                internal_score=0.031,
                risk_category="high",
                model_version=config.PREDICTION_MODEL_VERSION,
                feature_schema_version=config.PREDICTION_FEATURE_SCHEMA_VERSION,
                input_schema_version=config.PREDICTION_INPUT_SCHEMA_VERSION,
                preprocessing_version=config.PREDICTION_PREPROCESSING_VERSION,
                target_definition_version=config.PREDICTION_TARGET_DEFINITION_VERSION,
                calibration_version=config.PREDICTION_CALIBRATION_VERSION,
                model_artifact_digest=config.PREDICTION_MODEL_ARTIFACT_DIGEST,
                threshold_version=config.PREDICTION_THRESHOLD_VERSION,
                decision_threshold=config.PREDICTION_DECISION_THRESHOLD,
                promotion_status="approved",
                display_allowed=True,
                operational_model_activated=True,
            )

    async def explain(*args, **kwargs):
        del args, kwargs
        return approved_explanation()

    monkeypatch.setattr(ai_jobs, "get_prediction_provider", lambda: Provider())
    monkeypatch.setattr(ai_jobs, "_demo_future_explanation", explain)
    try:
        job = await PredictionJob.create(
            job_id="future-xai",
            task_type="diabetes_incidence",
            request_payload={},
            user_id=1,
            health_checkup_id=1,
        )
        await ai_jobs._complete_demo_prediction(job, {}, date(2026, 9, 18))
        prediction = await Prediction.get(job_id="future-xai")
        factor = await RiskFactor.get(prediction_id=prediction.id)
        await job.refresh_from_db()

        assert prediction.explanation_status == "approved"
        assert factor.factor_name == "age"
        assert factor.impact_direction == "increase"
        assert job.result["explanation"]["status"] == "approved"
    finally:
        await reset_tortoise()


@pytest.mark.asyncio
async def test_demo_artifact_current_result_uses_pinned_manifest(monkeypatch) -> None:
    await init_sqlite_test_db()
    monkeypatch.setattr(config, "DEMO_ARTIFACT_INFERENCE_ENABLED", True)
    monkeypatch.setattr(config, "XAI_DISPLAY_ALLOWED", True)
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

    async def explain(*args, **kwargs):
        del args, kwargs
        return approved_explanation()

    monkeypatch.setattr(ai_jobs, "_demo_current_explanation", explain)
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
        assert prediction.explanation_status == "approved"
        assert await RiskFactor.filter(prediction_id=prediction.id).count() == 1
    finally:
        await reset_tortoise()
