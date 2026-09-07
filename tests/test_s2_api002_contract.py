from pathlib import Path

from app.dtos.health import PredictionJobCreateRequest

ROOT = Path(__file__).resolve().parents[1]


def test_prediction_job_request_accepts_current_and_future_model_keys() -> None:
    current = PredictionJobCreateRequest(
        checkup_id=1,
        model_key="diabetes_current_screening",
    )
    future = PredictionJobCreateRequest(
        checkup_id=1,
        model_key="diabetes_incidence",
    )

    assert current.model_key == "diabetes_current_screening"
    assert future.model_key == "diabetes_incidence"


def test_localhost_does_not_automatically_bypass_prediction_jobs() -> None:
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert "const canUseLocalModelPreview = () => {" in script
    assert 'params.get("preview") === "forecast"' in script
    assert 'params.get("model_preview") === "junhyuk"' in script
    assert 'requestPredictionModel("diabetes_current_screening")' in script
    assert 'requestPredictionModel("diabetes_incidence")' in script
