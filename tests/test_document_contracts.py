from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_prediction_job_path_is_consistent() -> None:
    api = read("docs/API_SPEC.md")
    requirements = read("docs/REQUIREMENTS.md")
    backlog = read("docs/SPRINT2_BACKLOG.md")
    backend = read("app/apis/v1/prediction_routers.py")
    frontend = read("src/frontend/app.js")

    assert "/ai-jobs" not in api
    assert "/ai-jobs" not in requirements
    assert "`/ai-jobs`" not in backlog
    assert "/prediction-jobs" in api
    assert "/prediction-jobs" in requirements
    assert '@prediction_router.post("/prediction-jobs"' in backend
    assert "/prediction-jobs" in frontend
    assert "검증 전 확률·개선율은 표시하지 않습니다." in frontend


def test_async_timeout_contract_is_documented() -> None:
    api = read("docs/API_SPEC.md")
    assert "status: failed" in api
    assert "error_code: TIMEOUT" in api
    assert '"retry_after_seconds": 30' in api


def test_privacy_lifecycle_policy_is_not_tbd() -> None:
    requirements = read("docs/REQUIREMENTS.md")
    safety = read("docs/SERVICE_SCOPE_AND_SAFETY_COPY.md")
    assert "보관·삭제·익명화 정책 TBD" not in requirements
    assert "30일 이내 삭제" in requirements
    assert "동의 철회 즉시" in safety
    assert "복구 불가능한 익명화" in safety
