from pathlib import Path

from app.main import app
from app.prediction.contracts import ACTIVE_MODEL

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_entrypoint_uses_formal_application() -> None:
    from src.backend.main import app as compatibility_app

    assert compatibility_app is app
    paths = app.openapi()["paths"]
    assert "/api/v1/prediction-jobs" in paths
    assert "/api/v1/ai-jobs" not in paths


def test_home_has_accessibility_and_medical_notice() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert "본문으로 바로가기" in html
    assert "진단·처방" in html
    assert "DEVELOPMENT" in html
    assert "확률 비공개" in html
    assert "약을 끊으세요" not in html + script
    assert "약을 시작하세요" not in html + script


def test_reviewed_eligibility_and_failure_guidance_is_user_specific() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    for screen_code in ("E02", "E03", "D01", "E05"):
        assert screen_code in script
    for reason_code in (
        "UNDER_MINIMUM_SERVICE_AGE",
        "URGENT_MEDICAL_ATTENTION",
        "DIAGNOSED_DIABETES",
        "MODEL_AGE_OUT_OF_RANGE",
    ):
        assert reason_code in script
    assert "분석 실패는 당뇨병 위험도가 높다는 의미가 아닙니다." in html
    assert "입력정보 확인하기" in html
    assert "다시 시도하기" in html


def test_high_risk_prioritizes_medical_guidance_and_hides_internal_versions() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert "검사·의료기관 안내 보기" in script
    assert "medical-guidance-detail" in html + script
    assert 'id="model-version"' not in html
    assert "prediction.model_version" not in script
    assert "prediction.feature_schema_version" not in script
    assert "약 2년 뒤" not in html


def test_service_and_model_age_are_separately_explained() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")

    assert "서비스는 만 19세 이상 이용" in html
    assert "현재 예측 모델은 만 45세 이상" in html


def test_only_reviewed_diabetes_contract_is_active() -> None:
    assert ACTIVE_MODEL.model_key == "diabetes_incidence"
    assert ACTIVE_MODEL.outcome_definition == "next_observation_new_diabetes_diagnosis"
    assert ACTIVE_MODEL.observation_horizon == "approximately_2_years_next_klosa_wave"
    assert ACTIVE_MODEL.threshold_is_approved is False
