from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from starlette import status
from tortoise import Tortoise

from ai_worker.handlers import run_task
from app.core import config
from app.core.db.databases import TORTOISE_APP_MODELS
from app.dtos.health import PredictionJobCreateRequest
from app.main import app
from app.services.health import HealthService

ROOT = Path(__file__).resolve().parents[1]


def test_prediction_job_contract_separates_today_and_tomorrow_models() -> None:
    today = PredictionJobCreateRequest(checkup_id=1, model_key="diabetes_current_screening")
    tomorrow = PredictionJobCreateRequest(checkup_id=1, model_key="diabetes_incidence")

    assert today.model_key == "diabetes_current_screening"
    assert tomorrow.model_key == "diabetes_incidence"
    with pytest.raises(ValidationError):
        PredictionJobCreateRequest(
            checkup_id=1,
            model_key="diabetes_current_screening",
            prediction_type="survival_curve",
        )


def test_health_checkup_maps_to_current_screening_without_guessing_missing_fields() -> None:
    checkup = SimpleNamespace(
        age=41,
        height_cm=170.0,
        weight_kg=70.0,
        waist_cm=84.0,
        bmi=24.22,
        exercise_days_per_week=3.0,
        sex="male",
        education_level="code_3",
        current_smoker=False,
        current_drinker=True,
        regular_exercise=True,
    )

    payload = HealthService.current_screening_payload(checkup)

    assert payload["age"] == 41
    assert payload["walking_days"] == 3.0
    assert payload["diabetes_family_history"] is None
    assert payload["energy_kcal"] is None
    assert payload["aerobic_activity"] is True


@pytest.mark.asyncio
async def test_current_screening_worker_keeps_unapproved_result_internal(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.ml.inference import diabetes_current_screening as screening

    loaded = SimpleNamespace(
        manifest={
            "operational_model_activated": False,
            "promotion_status": "baseline_champion_pending_operational_approval",
            "artifact_sha256": "abc123",
            "threshold": 0.02,
        }
    )
    monkeypatch.setattr(screening, "load_current_screening_model", lambda: loaded)
    monkeypatch.setattr(
        screening,
        "predict_with_loaded_current_model",
        lambda _loaded, _payload: {
            "screening_signal_detected": True,
            "risk_score_internal": 0.8,
            "model_version": "today-test-v1",
            "feature_schema_version": "today-features-v1",
            "threshold_version": "today-threshold-v1",
        },
    )

    result = await run_task("diabetes_current_screening", {"input": {"age": 41}})

    assert result["model_key"] == "diabetes_current_screening"
    assert result["promotion_status"] == "development_only"
    assert result["risk_category"] is None
    assert result["screening_signal_detected"] is None


def test_frontend_requests_both_models_and_labels_them_separately() -> None:
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")

    assert 'requestPredictionModel("diabetes_current_screening")' in script
    assert 'requestPredictionModel("diabetes_incidence")' in script
    assert "오늘이 · 현재 당뇨 위험 신호 선별" in html
    assert "내일이 · 약 2년 후 신규 당뇨 발병 위험" in html


@pytest.mark.asyncio
async def test_adult_under_45_can_save_checkup_and_run_today_model_in_demo_mode() -> None:
    previous_demo_mode = config.DEMO_MODE
    config.DEMO_MODE = True
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TORTOISE_APP_MODELS}, timezone="Asia/Seoul")
    await Tortoise.generate_schemas()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            signup = {
                "name": "오늘이 사용자",
                "email": "today-flow@example.com",
                "password": "Password123!",
                "terms_agreed": True,
            }
            assert (await client.post("/api/v1/auth/signup", json=signup)).status_code == status.HTTP_201_CREATED
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": signup["email"], "password": signup["password"]},
            )
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            birthday = "1986-04-12"
            await client.patch(
                "/api/v1/users/me/profile",
                headers=headers,
                json={"birthday": birthday, "gender": "MALE"},
            )
            await client.post(
                "/api/v1/consents",
                headers=headers,
                json={"consent_item": "health_data", "version": "1.0", "is_agreed": True},
            )
            eligibility = await client.post(
                "/api/v1/eligibility-checks",
                headers=headers,
                json={
                    "birth_date": birthday,
                    "has_diabetes_diagnosis": False,
                    "has_urgent_warning_sign": False,
                    "population_in_scope": True,
                },
            )
            eligibility_data = eligibility.json()["data"]
            assert eligibility_data["current_screening_eligible"] is True
            assert eligibility_data["future_prediction_eligible"] is False

            checkup = await client.post(
                "/api/v1/health-checkups",
                headers=headers,
                json={
                    "checkup_type": "initial",
                    "checkup_date": "2026-09-01",
                    "height_cm": 170,
                    "weight_kg": 70,
                    "waist_cm": 84,
                    "systolic_bp": 126,
                    "diastolic_bp": 78,
                    "self_rated_health": "fair",
                    "meal_count_yesterday": 3,
                    "regular_exercise": True,
                    "smoking_status": "never",
                    "current_drinker": False,
                    "exercise_days_per_week": 3,
                    "exercise_minutes": 30,
                    "feature_schema_version": "klosa_stage3_25features_v1",
                },
            )
            assert checkup.status_code == status.HTTP_201_CREATED
            job = await client.post(
                "/api/v1/prediction-jobs",
                headers=headers,
                json={
                    "checkup_id": checkup.json()["data"]["checkup_id"],
                    "model_key": "diabetes_current_screening",
                },
            )
            assert job.status_code == status.HTTP_202_ACCEPTED
            prediction = await client.get(
                f"/api/v1/predictions/{job.json()['data']['prediction_id']}",
                headers=headers,
            )
            data = prediction.json()["data"]
            assert data["prediction_type"] == "current_screening"
            assert data["screening_signal_detected"] is None
            assert data["raw_probability_exposed"] is False
    finally:
        config.DEMO_MODE = previous_demo_mode
        await Tortoise.close_connections()
