from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.apis.v1 import research_model_routers as routes
from app.dependencies.security import get_request_user
from src.ml.inference import research_models


@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    app.include_router(routes.research_model_router)
    app.dependency_overrides[get_request_user] = lambda: SimpleNamespace(is_active=True, is_admin=True)
    monkeypatch.setattr(routes.config, "ML_RESEARCH_ENDPOINTS_ENABLED", True)
    return TestClient(app)


def test_disabled_endpoint(client, monkeypatch):
    monkeypatch.setattr(routes.config, "ML_RESEARCH_ENDPOINTS_ENABLED", False)
    assert (
        client.post("/research/models/shared7/predict", json={"as_of_date": "2026-08-31", "input": {}}).status_code
        == 404
    )


def test_requires_admin(client):
    client.app.dependency_overrides[get_request_user] = lambda: SimpleNamespace(is_active=True, is_admin=False)
    assert (
        client.post("/research/models/shared7/predict", json={"as_of_date": "2026-08-31", "input": {}}).status_code
        == 403
    )


def test_requires_authentication(client):
    client.app.dependency_overrides.clear()
    assert client.post(
        "/research/models/shared7/predict", json={"as_of_date": "2026-08-31", "input": {}}
    ).status_code in (401, 403)


@pytest.mark.parametrize("model", ["shared7", "first-interval"])
def test_route_calls_correct_model(client, monkeypatch, model):
    def predict(selected, payload, *, as_of_date, model_path):
        assert selected == model and payload == {"example": 1}
        assert as_of_date.isoformat() == "2026-08-31"
        return {"model": model, "display_allowed": False}

    monkeypatch.setattr(research_models, "predict_research_model", predict)
    r = client.post(f"/research/models/{model}/predict", json={"as_of_date": "2026-08-31", "input": {"example": 1}})
    assert r.status_code == 200 and r.json()["data"]["display_allowed"] is False
    assert r.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "error,status,code",
    [
        (ValueError("height_cm required"), 422, "ML_INPUT_MISSING"),
        (ValueError("outside the model-supported range"), 422, "ML_POPULATION_UNSUPPORTED"),
        (research_models.ResearchArtifactUnavailableError("private/path"), 503, "ML_MODEL_UNAVAILABLE"),
        (research_models.ResearchModelContractError("private/path"), 503, "ML_MODEL_CONTRACT_ERROR"),
    ],
)
def test_error_contract(client, monkeypatch, error, status, code):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(research_models, "predict_research_model", fail)
    r = client.post("/research/models/shared7/predict", json={"as_of_date": "2026-08-31", "input": {}})
    assert r.status_code == status and r.json()["detail"] == {"code": code}
