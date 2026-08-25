from __future__ import annotations

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise import Tortoise

from app.core import config
from app.core.db.databases import TORTOISE_APP_MODELS
from app.main import app


@pytest.mark.asyncio
async def test_demo_mode_completes_core_user_flow_without_redis() -> None:
    previous_demo_mode = config.DEMO_MODE
    config.DEMO_MODE = True
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TORTOISE_APP_MODELS}, timezone="Asia/Seoul")
    await Tortoise.generate_schemas()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            signup = {
                "email": "mvp-flow@example.com",
                "password": "Password123!",
                "gender": "FEMALE",
                "birth_date": "1965-04-12",
            }
            assert (await client.post("/api/v1/auth/signup", json=signup)).status_code == status.HTTP_201_CREATED
            login = await client.post(
                "/api/v1/auth/login", json={"email": signup["email"], "password": signup["password"]}
            )
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            consent = await client.post(
                "/api/v1/consents",
                headers=headers,
                json={"consent_item": "health_data", "version": "1.0", "is_agreed": True},
            )
            assert consent.status_code == status.HTTP_201_CREATED

            eligibility = await client.post(
                "/api/v1/eligibility-checks",
                headers=headers,
                json={
                    "birth_date": signup["birth_date"],
                    "has_diabetes_diagnosis": False,
                    "has_urgent_warning_sign": False,
                    "population_in_scope": True,
                },
            )
            assert eligibility.json()["data"]["model_eligible"] is True

            checkup = await client.post(
                "/api/v1/health-checkups",
                headers=headers,
                json={
                    "checkup_type": "initial",
                    "checkup_date": date.today().isoformat(),
                    "height_cm": 160,
                    "weight_kg": 62,
                    "waist_cm": 78,
                    "systolic_bp": 128,
                    "diastolic_bp": 78,
                    "self_rated_health": "fair",
                    "meal_count_yesterday": 3,
                    "regular_exercise": False,
                    "current_smoker": False,
                    "current_drinker": False,
                    "feature_schema_version": "klosa-diabetes-incident-v1",
                },
            )
            assert checkup.status_code == status.HTTP_201_CREATED

            job = await client.post(
                "/api/v1/prediction-jobs",
                headers=headers,
                json={"checkup_id": checkup.json()["data"]["checkup_id"], "model_key": "diabetes_incidence"},
            )
            assert job.status_code == status.HTTP_202_ACCEPTED
            assert job.json()["data"]["status"] == "succeeded"
            prediction_id = job.json()["data"]["prediction_id"]

            prediction = await client.get(f"/api/v1/predictions/{prediction_id}", headers=headers)
            assert prediction.json()["data"]["raw_probability_exposed"] is False
            assert prediction.json()["data"]["risk_category"] is None

            recommendations = await client.get(
                f"/api/v1/challenge-recommendations?prediction_id={prediction_id}", headers=headers
            )
            challenge_id = recommendations.json()["data"]["items"][0]["challenge_id"]
            cycle = await client.post(
                "/api/v1/challenge-cycles",
                headers=headers,
                json={
                    "start_date": date.today().isoformat(),
                    "challenge_ids": [challenge_id],
                    "prediction_id": prediction_id,
                },
            )
            user_challenge_id = cycle.json()["data"]["user_challenges"][0]["user_challenge_id"]
            log = await client.put(
                f"/api/v1/user-challenges/{user_challenge_id}/logs/{date.today().isoformat()}",
                headers=headers,
                json={"is_completed": True, "value": 1, "source": "self_report", "note": None},
            )
            assert log.status_code == status.HTTP_200_OK

            dashboard = await client.get("/api/v1/dashboard/summary", headers=headers)
            assert dashboard.status_code == status.HTTP_200_OK
            weekly = await client.get("/api/v1/weekly-reports/current", headers=headers)
            assert weekly.json()["data"]["status"] == "ready"
            assert weekly.json()["data"]["summary_method"] == "deterministic_template_v1"
    finally:
        config.DEMO_MODE = previous_demo_mode
        await Tortoise.close_connections()
