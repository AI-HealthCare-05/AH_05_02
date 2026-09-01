from __future__ import annotations

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise import Tortoise

from app.core.db.databases import TORTOISE_APP_MODELS
from app.main import app
from src.rag.engine import answer_with_sources


async def signup_and_login(client: AsyncClient) -> dict[str, str]:
    signup = {
        "name": "웰니스 사용자",
        "email": "wellness@example.com",
        "password": "Password123!",
        "terms_agreed": True,
    }
    response = await client.post("/api/v1/auth/signup", json=signup)
    assert response.status_code == status.HTTP_201_CREATED
    login = await client.post("/api/v1/auth/login", json={"email": signup["email"], "password": signup["password"]})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_rag_returns_citations_and_refuses_medication_changes() -> None:
    grounded = answer_with_sources("당뇨 예방을 위해 어떤 생활습관을 기록하면 좋나요?")
    assert grounded["answer_status"] == "grounded"
    assert grounded["citations"]
    assert all(item["url"].startswith("https://") for item in grounded["citations"])

    refused = answer_with_sources("당뇨약 용량을 줄여도 되나요?")
    assert refused["answer_status"] == "medical_safety_refusal"
    assert "의료진" in refused["answer"]


@pytest.mark.asyncio
async def test_wearable_rag_cv_ocr_notification_and_pdf_contracts() -> None:
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TORTOISE_APP_MODELS}, timezone="Asia/Seoul")
    await Tortoise.generate_schemas()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = await signup_and_login(client)

            connection = await client.post(
                "/api/v1/wearables/connections",
                headers=headers,
                json={"provider": "development_mock", "scopes": ["activity"]},
            )
            assert connection.status_code == status.HTTP_201_CREATED
            connection_id = connection.json()["data"]["connection_id"]
            imported = await client.post(
                "/api/v1/wearables/daily-summaries/import",
                headers=headers,
                json={
                    "connection_id": connection_id,
                    "items": [{"summary_date": date.today().isoformat(), "steps": 4321}],
                },
            )
            assert imported.json()["data"]["imported_count"] == 1

            rag = await client.post(
                "/api/v1/health-education/questions",
                headers=headers,
                json={"question": "걷기 운동은 어떻게 시작하나요?"},
            )
            assert rag.json()["data"]["citations"]

            food = await client.post("/api/v1/food-analyses", headers=headers, json={"image_name": "lunch_salad.jpg"})
            food_data = food.json()["data"]
            assert food_data["provider"] == "development_mock"
            assert food_data["requires_user_confirmation"] is True
            confirmed = await client.patch(
                f"/api/v1/food-analyses/{food_data['analysis_id']}/confirm",
                headers=headers,
                json={"confirmed_category": "채소"},
            )
            assert confirmed.json()["data"]["status"] == "user_confirmed"

            ocr = await client.post(
                "/api/v1/ocr-drafts",
                headers=headers,
                json={
                    "document_name": "검진결과.jpg",
                    "extracted_fields": {"height_cm": 165, "systolic_bp": 128, "resident_number": "blocked"},
                },
            )
            ocr_data = ocr.json()["data"]
            assert ocr_data["requires_user_confirmation"] is True
            assert "resident_number" in ocr_data["ignored_fields"]
            assert "resident_number" not in ocr_data["extracted_fields"]

            preferences = await client.put(
                "/api/v1/notification-preferences",
                headers=headers,
                json={
                    "in_app_enabled": True,
                    "challenge_reminder_enabled": False,
                    "weekly_report_enabled": True,
                    "quiet_start_hour": 22,
                    "quiet_end_hour": 7,
                },
            )
            assert preferences.json()["data"]["quiet_hours"] == {"start": 22, "end": 7}

            pdf = await client.get("/api/v1/weekly-reports/current/pdf", headers=headers)
            assert pdf.status_code == status.HTTP_200_OK
            assert pdf.headers["content-type"] == "application/pdf"
            assert pdf.content.startswith(b"%PDF")
    finally:
        await Tortoise.close_connections()
