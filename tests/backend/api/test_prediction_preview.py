from datetime import date

from fastapi.testclient import TestClient

from src.backend.main import app

client = TestClient(app)


def valid_request() -> dict[str, object]:
    return {
        "birth_date": "1970-01-01",
        "sex": "female",
        "height_cm": 160,
        "weight_kg": 60,
        "smoking_status": "never",
        "current_drinker": False,
        "regular_exercise": True,
        "exercise_days_per_week": 3,
        "exercise_minutes": 40,
        "previously_diagnosed_diabetes": False,
    }


def test_prediction_preview_returns_temporary_result_without_raw_score() -> None:
    response = client.post("/api/v1/predictions/preview", json=valid_request())

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["condition"] == "diabetes"
    assert data["model_type"] == "future_incidence"
    assert data["risk_category"] == "moderate"
    assert data["predicted_class"] in [0, 1]
    assert data["target_definition_version"] == ("klosa-diabetes-incidence-next-wave-v1")
    assert data["is_temporary"] is True
    assert "risk_score" not in data
    assert "score" not in data
    assert data["safety_notice"]["is_medical_diagnosis"] is False


def test_prediction_preview_rejects_out_of_range_height() -> None:
    payload = valid_request()
    payload["height_cm"] = 100

    response = client.post("/api/v1/predictions/preview", json=payload)

    assert response.status_code == 422


def test_prediction_preview_rejects_diagnosed_user() -> None:
    payload = valid_request()
    payload["previously_diagnosed_diabetes"] = True

    response = client.post("/api/v1/predictions/preview", json=payload)

    assert response.status_code == 422


def test_prediction_preview_rejects_user_under_model_minimum_age() -> None:
    payload = valid_request()
    payload["birth_date"] = date(date.today().year - 30, 1, 1).isoformat()

    response = client.post("/api/v1/predictions/preview", json=payload)

    assert response.status_code == 422


def test_prediction_preview_rejects_unapproved_extra_field() -> None:
    payload = valid_request()
    payload["hba1c"] = 6.2

    response = client.post("/api/v1/predictions/preview", json=payload)

    assert response.status_code == 422


def test_non_exerciser_must_use_structural_zero_values() -> None:
    payload = valid_request()
    payload["regular_exercise"] = False

    response = client.post("/api/v1/predictions/preview", json=payload)

    assert response.status_code == 422
