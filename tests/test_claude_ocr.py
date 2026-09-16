from __future__ import annotations

import httpx
import pytest

from app.core import config
from app.ocr.claude import ClaudeOcrProvider
from app.ocr.providers import OcrProviderError, get_health_checkup_ocr_provider


class _FakeResponse:
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {"content": [{"type": "text", "text": "신장: 168.2 cm\n혈압: 132 / 84 mmHg"}]}


class _FakeAsyncClient:
    request: dict[str, object] = {}

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.request["timeout"] = kwargs.get("timeout")

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None

    async def post(self, url: str, **kwargs: object) -> _FakeResponse:
        self.request.update({"url": url, **kwargs})
        return _FakeResponse()


def test_claude_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    with pytest.raises(OcrProviderError, match="ANTHROPIC_API_KEY"):
        ClaudeOcrProvider()


@pytest.mark.asyncio
async def test_claude_provider_transcribes_image_without_diagnostic_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    text = await ClaudeOcrProvider().extract_text(
        file_name="health-checkup.jpg", content_type="image/jpeg", content=b"image-bytes"
    )

    request = _FakeAsyncClient.request
    content = request["json"]["messages"][0]["content"]
    assert text.startswith("신장")
    assert request["headers"]["anthropic-version"] == "2023-06-01"
    assert request["headers"]["x-api-key"] == "test-key"
    assert content[0]["type"] == "image"
    assert content[1]["type"] == "text"
    assert "diagnose" in content[1]["text"]


@pytest.mark.asyncio
async def test_claude_provider_accepts_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    await ClaudeOcrProvider().extract_text(
        file_name="health-checkup.pdf", content_type="application/pdf", content=b"pdf-bytes"
    )

    content = _FakeAsyncClient.request["json"]["messages"][0]["content"]
    assert content[0]["type"] == "document"
    assert content[0]["source"]["media_type"] == "application/pdf"


def test_provider_factory_selects_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "HEALTH_CHECKUP_OCR_PROVIDER", "claude")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
    assert get_health_checkup_ocr_provider().provider_kind == "claude_vision_api"
