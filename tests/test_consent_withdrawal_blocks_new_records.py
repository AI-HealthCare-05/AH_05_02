"""동의 철회 후 신규 검진·예측·챌린지 생성이 차단되는지 재검증하는 테스트.

건강정보 동의(consent_item="health_data")를 철회하면 `HealthRepository.active_consent()`가
더 이상 이 사용자의 동의를 반환하지 않는다. 세 생성 경로(건강정보 입력, 예측 작업 생성,
챌린지 사이클 생성)가 모두 이 리포지토리 메서드로 동의를 확인하므로, 철회 후에는 세 경로
전부 403으로 막혀야 한다. 이 테스트는 새 기능을 추가하는 것이 아니라, 이미 구현된 차단
로직이 세 경로 모두에서 실제로 동작하는지를 API 레벨에서 확인한다.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise import Tortoise

from app.core import config
from app.core.db.databases import TORTOISE_APP_MODELS
from app.main import app


async def _signup_login_consent_and_checkup(client: AsyncClient) -> dict[str, object]:
    """회원가입부터 첫 건강정보 입력까지 정상 흐름을 거쳐 필요한 id들을 모은다."""
    signup = {
        "name": "동의철회 테스트",
        "email": "consent-withdrawal@example.com",
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

    consent = await client.post(
        "/api/v1/consents",
        headers=headers,
        json={"consent_item": "health_data", "version": "1.0", "is_agreed": True},
    )
    assert consent.status_code == status.HTTP_201_CREATED
    consent_id = consent.json()["data"]["consent_id"]

    await client.post(
        "/api/v1/eligibility-checks",
        headers=headers,
        json={
            "birth_date": birthday,
            "has_diabetes_diagnosis": False,
            "has_urgent_warning_sign": False,
            "population_in_scope": True,
        },
    )

    checkup_payload = {
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
    }
    checkup = await client.post("/api/v1/health-checkups", headers=headers, json=checkup_payload)
    assert checkup.status_code == status.HTTP_201_CREATED

    return {
        "headers": headers,
        "consent_id": consent_id,
        "checkup_id": checkup.json()["data"]["checkup_id"],
        "checkup_payload": checkup_payload,
    }


@pytest.mark.asyncio
async def test_consent_withdrawal_blocks_new_checkup_prediction_and_challenge_creation() -> None:
    previous_demo_mode = config.DEMO_MODE
    config.DEMO_MODE = True
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TORTOISE_APP_MODELS}, timezone="Asia/Seoul")
    await Tortoise.generate_schemas()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            context = await _signup_login_consent_and_checkup(client)
            headers = context["headers"]

            # 철회 전: 정상적으로 예측 작업을 생성할 수 있어야 한다(대조군).
            job_before = await client.post(
                "/api/v1/prediction-jobs",
                headers=headers,
                json={"checkup_id": context["checkup_id"], "model_key": "diabetes_current_screening"},
            )
            assert job_before.status_code == status.HTTP_202_ACCEPTED

            withdraw = await client.patch(
                f"/api/v1/consents/{context['consent_id']}/withdraw",
                headers=headers,
            )
            assert withdraw.status_code == status.HTTP_200_OK
            assert withdraw.json()["data"]["withdrawn_at"] is not None

            # 철회 후: 신규 건강정보(검진) 입력 차단
            new_checkup = await client.post(
                "/api/v1/health-checkups",
                headers=headers,
                json={**context["checkup_payload"], "checkup_date": "2026-09-08"},
            )
            assert new_checkup.status_code == status.HTTP_403_FORBIDDEN

            # 철회 후: 신규 예측 작업 생성 차단(기존 검진 기록을 재사용해도 막혀야 함)
            new_job = await client.post(
                "/api/v1/prediction-jobs",
                headers=headers,
                json={"checkup_id": context["checkup_id"], "model_key": "diabetes_current_screening"},
            )
            assert new_job.status_code == status.HTTP_403_FORBIDDEN

            # 철회 후: 신규 챌린지 사이클 생성 차단
            new_cycle = await client.post(
                "/api/v1/challenge-cycles",
                headers=headers,
                json={"start_date": "2026-09-08", "challenge_ids": [1]},
            )
            assert new_cycle.status_code == status.HTTP_403_FORBIDDEN
    finally:
        config.DEMO_MODE = previous_demo_mode
        await Tortoise.close_connections()


@pytest.mark.asyncio
async def test_re_agreeing_after_withdrawal_unblocks_new_records() -> None:
    """철회 후 재동의하면 다시 정상적으로 생성할 수 있어야 한다(차단이 영구적이지 않음을 확인)."""
    previous_demo_mode = config.DEMO_MODE
    config.DEMO_MODE = True
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TORTOISE_APP_MODELS}, timezone="Asia/Seoul")
    await Tortoise.generate_schemas()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            context = await _signup_login_consent_and_checkup(client)
            headers = context["headers"]

            await client.patch(f"/api/v1/consents/{context['consent_id']}/withdraw", headers=headers)

            blocked = await client.post(
                "/api/v1/challenge-cycles",
                headers=headers,
                json={"start_date": "2026-09-08", "challenge_ids": [1]},
            )
            assert blocked.status_code == status.HTTP_403_FORBIDDEN

            re_consent = await client.post(
                "/api/v1/consents",
                headers=headers,
                json={"consent_item": "health_data", "version": "1.0", "is_agreed": True},
            )
            assert re_consent.status_code == status.HTTP_201_CREATED

            unblocked_checkup = await client.post(
                "/api/v1/health-checkups",
                headers=headers,
                json={**context["checkup_payload"], "checkup_date": "2026-09-09"},
            )
            assert unblocked_checkup.status_code == status.HTTP_201_CREATED
    finally:
        config.DEMO_MODE = previous_demo_mode
        await Tortoise.close_connections()
