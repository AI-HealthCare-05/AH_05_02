from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_fastapi_image_contains_runtime_modules_and_catalog() -> None:
    dockerfile = (ROOT / "app" / "Dockerfile").read_text(encoding="utf-8")
    for required in (
        "COPY ./src/frontend ./src/frontend",
        "COPY ./src/rag ./src/rag",
        "COPY ./src/ocr ./src/ocr",
        "COPY ./src/quiz ./src/quiz",
        "COPY ./src/wearables ./src/wearables",
        "COPY ./docs/CHALLENGE_CATALOG_V2_20260903.json",
    ):
        assert required in dockerfile


def test_worker_image_does_not_require_gitignored_model_during_build() -> None:
    dockerfile = (ROOT / "ai_worker" / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY ./models/registry ./models/registry" in dockerfile
    assert "COPY ./models/artifacts" not in dockerfile


def test_production_compose_mounts_models_and_reuses_worker_image() -> None:
    compose = (ROOT / "infra" / "docker" / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert compose.count("/app/models/artifacts:ro") == 3
    assert "ai-current-${AI_CURRENT_WORKER_VERSION}" not in compose
    assert '"127.0.0.1:${REDIS_PORT}:6379"' in compose
    assert '"127.0.0.1:${DB_EXPOSE_PORT}:${DB_PORT}"' in compose


def test_nginx_exposes_frontend_and_api_through_fastapi() -> None:
    for name in ("prod_http.conf", "prod_https.conf"):
        config = (ROOT / "infra" / "nginx" / name).read_text(encoding="utf-8")
        assert "proxy_pass http://fastapi;" in config
        assert "return 404;" not in config
        assert "client_max_body_size 10m;" in config


def test_windows_environment_setup_writes_non_secret_deployment_contract() -> None:
    setup = (ROOT / "scripts" / "configure-env-windows.ps1").read_text(encoding="utf-8")
    for required in (
        'ENV = "prod"',
        'DB_GENERATE_SCHEMAS = "false"',
        'PREDICTION_PROVIDER = "artifact"',
        'MODEL_ARTIFACTS_PATH = "/opt/ah05/models/artifacts"',
        'CURRENT_SCREENING_REDIS_STREAM = "ai:jobs:current-screening"',
    ):
        assert required in setup
