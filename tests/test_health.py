from fastapi.testclient import TestClient

from src.backend.main import app


def test_health_check() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_docs_are_exposed_under_api_path() -> None:
    response = TestClient(app).get("/api/docs")

    assert response.status_code == 200
    assert "/api/openapi.json" in response.text
