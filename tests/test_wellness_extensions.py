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
    assert all("checked_at" in item for item in grounded["citations"])

    refused = answer_with_sources("당뇨약 용량을 줄여도 되나요?")
    assert refused["answer_status"] == "medical_safety_refusal"
    assert "의료진" in refused["answer"]


def test_rag_redirects_emergency_symptoms_before_normal_answer() -> None:
    emergency = answer_with_sources("갑자기 가슴 통증이 심하고 숨쉬기 힘들어요")
    assert emergency["answer_status"] == "emergency_redirect"
    assert "119" in emergency["answer"]
    assert emergency["citations"]
    assert emergency["citations"][0]["document_id"] == "kdca-hyperglycemia-emergency"

    unconscious = answer_with_sources("어지러워서 쓰러졌는데 의식이 흐려요")
    assert unconscious["answer_status"] == "emergency_redirect"


def test_rag_emergency_takes_priority_over_medication_pattern() -> None:
    result = answer_with_sources("의식을 잃었는데 약을 늘려도 되나요?")
    assert result["answer_status"] == "emergency_redirect"


def test_rag_diet_and_complication_questions_are_grounded_in_new_documents() -> None:
    diet = answer_with_sources("당뇨병 식이요법에서 탄수화물은 얼마나 먹어야 하나요?")
    assert diet["answer_status"] == "grounded"
    assert any(item["document_id"] == "kdca-diabetes-diet" for item in diet["citations"])

    complications = answer_with_sources("당뇨병 합병증으로 어떤 검진을 받아야 하나요?")
    assert complications["answer_status"] == "grounded"
    assert any(item["document_id"] == "kdca-diabetes-complications" for item in complications["citations"])


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
            assert imported.json()["data"]["exercise_verification_candidates"][0]["eligible"] is True

            health_candidates = await client.get("/api/v1/wearables/health-candidates", headers=headers)
            candidate_data = health_candidates.json()["data"]
            assert candidate_data["health_input_candidates"]["exercise_days_per_week"] == 1
            assert candidate_data["requires_user_confirmation"] is True

            rag = await client.post(
                "/api/v1/health-education/questions",
                headers=headers,
                json={"question": "걷기 운동은 어떻게 시작하나요?"},
            )
            assert rag.json()["data"]["citations"]

            quizzes = await client.get("/api/v1/health-education/quizzes", headers=headers)
            quiz_items = quizzes.json()["data"]["items"]
            assert quiz_items
            for item in quiz_items:
                assert "answer" not in item
                assert "explanation" not in item

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

            text_ocr = await client.post(
                "/api/v1/ocr-drafts",
                headers=headers,
                json={
                    "document_name": "2025-general-checkup.txt",
                    "ocr_text": "검진일: 2025-06-18\n신장: 168.2 cm\n혈압: 132 / 84 mmHg\n공복혈당: 108 mg/dL",
                },
            )
            assert text_ocr.json()["data"]["extracted_fields"]["fasting_glucose_mg_dl"] == 108

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
