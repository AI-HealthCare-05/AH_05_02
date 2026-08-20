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


def test_prediction_preview_returns_temporary_result_with_risk_score() -> None:
    # API_SPEC.md v2 SS9 "점수 필드는 risk_score로 통일" — risk_score is now
    # part of the confirmed response contract (reverses the earlier
    # SERVICE_SCOPE_AND_SAFETY_COPY.md "hide the raw probability" guidance).
    #
    # 2026-08-20 모델 연동 Q&A SS6, 안 B 채택: 임계값 미승인 상태이므로
    # risk_category/risk_category_label/decision_threshold/predicted_class는
    # 전부 null이고 risk_score만 노출한다.
    response = client.post("/api/v1/predictions/preview", json=valid_request())

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["condition"] == "diabetes"
    assert data["model_type"] == "future_incidence"
    assert data["outcome_definition"] == "next_observation_new_diabetes_diagnosis"
    assert 0.0 <= data["risk_score"] <= 1.0
    assert data["risk_category"] is None
    assert data["risk_category_label"] is None
    assert data["decision_threshold"] is None
    assert data["predicted_class"] is None
    assert data["target_definition_version"] == ("klosa-diabetes-incidence-next-wave-v1")
    assert data["is_temporary"] is True
    assert data["safety_notice"]["is_medical_diagnosis"] is False


def test_prediction_preview_rejects_out_of_range_height() -> None:
    payload = valid_request()
    payload["height_cm"] = 100

    response = client.post("/api/v1/predictions/preview", json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["trace_id"]
    assert error["fields"][0]["field"] == "height_cm"
    assert error["fields"][0]["code"] == "OUT_OF_RANGE"


def test_prediction_preview_rejects_diagnosed_user() -> None:
    # Policy exclusion, not an input-format error: SERVICE_SCOPE_AND_SAFETY_COPY.md
    # SS6-1/6-2 requires 403 PREDICTION_NOT_ALLOWED here, not 422.
    payload = valid_request()
    payload["previously_diagnosed_diabetes"] = True

    response = client.post("/api/v1/predictions/preview", json=payload)

    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "PREDICTION_NOT_ALLOWED"
    assert error["trace_id"]
    assert "DIAGNOSED_DIABETES" in error["reason_codes"]


def test_prediction_preview_rejects_user_under_model_minimum_age() -> None:
    # Policy exclusion (outside the active model's validated age range), not an
    # input-format error: SERVICE_SCOPE_AND_SAFETY_COPY.md SS6-1/6-2 requires
    # 403 PREDICTION_NOT_ALLOWED here, not 422.
    payload = valid_request()
    payload["birth_date"] = date(date.today().year - 30, 1, 1).isoformat()

    response = client.post("/api/v1/predictions/preview", json=payload)

    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "PREDICTION_NOT_ALLOWED"
    assert error["trace_id"]
    assert "MODEL_AGE_OUT_OF_RANGE" in error["reason_codes"]


def test_prediction_preview_rejects_unapproved_extra_field() -> None:
    payload = valid_request()
    payload["hba1c"] = 6.2

    response = client.post("/api/v1/predictions/preview", json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["fields"][0]["field"] == "hba1c"
    assert error["fields"][0]["code"] == "UNSUPPORTED_FIELD"


def test_non_exerciser_must_use_structural_zero_values() -> None:
    payload = valid_request()
    payload["regular_exercise"] = False

    response = client.post("/api/v1/predictions/preview", json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["fields"][0]["code"] == "INVALID_VALUE"
    assert "운동" in error["fields"][0]["reason"]
