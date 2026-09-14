import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _service_block(compose: str, name: str) -> str:
    match = re.search(rf"^  {re.escape(name)}:\n(?P<body>.*?)(?=^  \w|^volumes:|^networks:|\Z)", compose, re.M | re.S)
    assert match, f"service not found: {name}"
    return match.group(0)


def test_production_compose_keeps_data_and_application_services_private() -> None:
    compose = (ROOT / "infra" / "docker" / "docker-compose.prod.yml").read_text(encoding="utf-8")
    for service in ("redis", "mysql", "fastapi", "ai-worker"):
        assert "ports:" not in _service_block(compose, service)
        assert "restart: unless-stopped" in _service_block(compose, service)
    assert '"80:80"' in _service_block(compose, "nginx")
    assert '"443:443"' in _service_block(compose, "nginx")


def test_production_assets_require_migrations_and_rendered_nginx_config() -> None:
    compose = (ROOT / "infra" / "docker" / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert 'DB_GENERATE_SCHEMAS: "false"' in compose
    assert "../nginx/runtime/default.conf" in compose
    assert (ROOT / "scripts" / "preflight-production.sh").exists()
    assert (ROOT / "scripts" / "prepare-ec2-release.sh").exists()
