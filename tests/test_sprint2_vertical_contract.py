from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from ai_worker.handlers import run_task
from app.apis.v1.prediction_routers import prediction_payload
from app.main import app
from app.prediction.contracts import ACTIVE_MODEL, KLOSA_FEATURE_SCHEMA, PredictionFeatures, input_schema_document
from app.prediction.providers import DevelopmentPredictionProvider
from app.services.health import eligibility_reason_codes

VALID_FEATURES = {
    "age": 61,
    "bmi": 25.3,
    "self_rated_health": "fair",
    "meal_count_yesterday": 3,
    "sex": "female",
    "regular_exercise": True,
    "current_smoker": False,
    "current_drinker": False,
}


def test_formal_app_exposes_only_prediction_job_path_in_openapi() -> None:
    visible_paths = set(app.openapi()["paths"])
    assert "/api/v1/prediction-jobs" in visible_paths
    assert "/api/v1/prediction-jobs/{job_id}" in visible_paths
    assert "/api/v1/ai-jobs" not in visible_paths


def test_feature_contract_matches_pr4_klosa_schema_and_rejects_extra_fields() -> None:
    features = PredictionFeatures.model_validate(VALID_FEATURES)
    assert tuple(features.as_model_record()) == KLOSA_FEATURE_SCHEMA
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PredictionFeatures.model_validate({**VALID_FEATURES, "future_diabetes_diagnosis": True})


def test_input_schema_names_leakage_fields_as_excluded() -> None:
    schema = input_schema_document()
    assert schema["feature_schema_version"] == "klosa-diabetes-incident-v1"
    assert "future_wave_measurements" in schema["excluded_leakage_fields"]


@pytest.mark.asyncio
async def test_development_provider_does_not_fabricate_probability_or_category() -> None:
    result = await DevelopmentPredictionProvider().predict(PredictionFeatures.model_validate(VALID_FEATURES))
    assert result.internal_score is None
    assert result.risk_category is None
    assert result.promotion_status == "development_only"


@pytest.mark.asyncio
async def test_worker_development_inference_returns_versioned_safe_result() -> None:
    result = await run_task("diabetes_incidence", {"features": VALID_FEATURES})
    assert result["risk_category"] is None
    assert result["internal_score"] is None
    assert result["feature_schema_version"] == ACTIVE_MODEL.feature_schema_version
    assert "진단·처방이 아닙니다" in result["medical_notice"]


def test_eligibility_blocks_minor_diagnosed_warning_and_out_of_scope() -> None:
    reasons = eligibility_reason_codes(
        age=17,
        has_consent=False,
        has_diabetes_diagnosis=True,
        has_urgent_warning_sign=True,
        population_in_scope=False,
    )
    assert set(reasons) == {
        "UNDER_MINIMUM_SERVICE_AGE",
        "CONSENT_REQUIRED",
        "DIAGNOSED_DIABETES",
        "URGENT_MEDICAL_ATTENTION",
        "MODEL_AGE_OUT_OF_RANGE",
        "MODEL_POPULATION_OUT_OF_SCOPE",
    }


def test_unapproved_prediction_never_exposes_internal_score_as_public_probability() -> None:
    item = SimpleNamespace(
        id=9,
        health_checkup_id=4,
        model_key="diabetes_incidence",
        outcome_definition="next_observation_new_diabetes_diagnosis",
        result_status="development_only",
        risk_category="high",
        internal_score=0.99,
        model_version="candidate-v0",
        feature_schema_version="klosa-diabetes-incident-v1",
        threshold_version="unapproved",
        model_population="baseline_undiagnosed_age_45_plus",
        predicted_at=datetime.now(UTC),
    )
    public = prediction_payload(item)
    assert public["risk_category"] is None
    assert public["raw_probability_exposed"] is False
    assert "internal_score" not in public
    assert "probability" not in public
