from datetime import date

from fastapi.testclient import TestClient

from src.backend.main import app


client = TestClient(app)


def signup_headers(email: str = "senior@example.com") -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "Prototype123!", "terms_agreed": True},
    )
    assert response.status_code == 201
    token = response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    consent = client.post(
        "/api/v1/consents",
        headers=headers,
        json={"consent_item": "health_data", "version": "1.0", "is_agreed": True},
    )
    assert consent.status_code == 201
    return headers


def eligible_senior(headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/eligibility-checks",
        headers=headers,
        json={
            "birth_date": "1955-04-12",
            "has_diabetes_diagnosis": False,
            "has_hypertension_diagnosis": False,
            "uses_glucose_lowering_drug": False,
            "has_alarming_symptom": False,
            "has_exercise_limitation": False,
        },
    )
    assert response.status_code == 201
    assert response.json()["data"]["target_segment"] == "primary_senior"
    assert response.json()["data"]["is_eligible"] is True


def test_complete_prototype_flow() -> None:
    headers = signup_headers()
    eligible_senior(headers)
    checkup = client.post(
        "/api/v1/health-checkups",
        headers=headers,
        json={
            "checkup_type": "initial",
            "checkup_date": date.today().isoformat(),
            "gender": "female",
            "height_cm": 160,
            "weight_kg": 67.5,
            "waist_cm": 91,
            "systolic_bp": 138,
            "diastolic_bp": 84,
            "fasting_glucose": 112,
            "smoking_status": "never",
            "drinking_frequency": "monthly_or_less",
            "physical_activity_level": "insufficient",
            "has_family_history_diabetes": True,
        },
    )
    assert checkup.status_code == 201
    checkup_id = checkup.json()["data"]["checkup_id"]

    job = client.post(
        "/api/v1/prediction-jobs",
        headers=headers,
        json={"checkup_id": checkup_id, "disease_type": "diabetes"},
    )
    assert job.status_code == 202
    prediction_id = job.json()["data"]["prediction_id"]
    prediction = client.get(f"/api/v1/predictions/{prediction_id}", headers=headers)
    result = prediction.json()["data"]
    assert result["is_mock"] is True
    assert result["model_version"].startswith("mock-")
    assert abs(sum(result["probabilities"].values()) - 1) < 1e-9
    assert "진단" in result["medical_notice"]

    recommendations = client.get(
        f"/api/v1/challenge-recommendations?prediction_id={prediction_id}",
        headers=headers,
    )
    challenge_id = recommendations.json()["data"]["items"][0]["challenge_id"]
    cycle = client.post(
        "/api/v1/challenge-cycles",
        headers=headers,
        json={"prediction_id": prediction_id, "challenge_ids": [challenge_id]},
    )
    assert cycle.status_code == 201
    user_challenge_id = cycle.json()["data"]["user_challenges"][0]["user_challenge_id"]
    log = client.put(
        f"/api/v1/user-challenges/{user_challenge_id}/logs/{date.today().isoformat()}",
        headers=headers,
        json={"is_completed": True},
    )
    assert log.status_code == 200
    dashboard = client.get("/api/v1/dashboard/summary", headers=headers)
    assert dashboard.json()["data"]["challenge_completion"]["completed_logs"] == 1


def test_under_19_and_diagnosed_users_are_not_eligible() -> None:
    minor_headers = signup_headers("minor@example.com")
    minor = client.post(
        "/api/v1/eligibility-checks",
        headers=minor_headers,
        json={"birth_date": "2010-01-01"},
    )
    assert minor.json()["data"]["is_eligible"] is False
    assert "만 19세 미만" in minor.json()["data"]["exclusion_reasons"]

    diagnosed_headers = signup_headers("diagnosed@example.com")
    diagnosed = client.post(
        "/api/v1/eligibility-checks",
        headers=diagnosed_headers,
        json={"birth_date": "1950-01-01", "has_diabetes_diagnosis": True},
    )
    assert diagnosed.json()["data"]["next_action"] == "medical_guidance"


def test_home_has_accessibility_and_medical_notice() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "본문으로 바로가기" in response.text
    assert "진단·처방" in response.text
    assert "MOCK AI" in response.text


def test_hypertension_is_explicitly_planned_not_faked() -> None:
    response = client.get("/api/v1/models/active")
    models = response.json()["data"]["items"]
    assert {item["disease_type"]: item["status"] for item in models}["hypertension"] == "planned"
