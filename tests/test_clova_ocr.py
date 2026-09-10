from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from app.core import config
from app.ocr.clova import ClovaOcrError, ClovaOcrProvider

ROOT = Path(__file__).resolve().parents[1]


class _FakeResponse:
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {
            "images": [
                {
                    "inferResult": "SUCCESS",
                    "fields": [
                        {"inferText": "신장: 168.2 cm"},
                        {"inferText": "혈압: 132 / 84 mmHg"},
                        {"inferText": "공복혈당: 108 mg/dL"},
                    ],
                }
            ]
        }


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


def test_clova_provider_requires_environment_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "CLOVA_OCR_URL", "")
    monkeypatch.setattr(config, "CLOVA_OCR_SECRET", "")

    with pytest.raises(ClovaOcrError, match="설정"):
        ClovaOcrProvider()


@pytest.mark.asyncio
async def test_clova_provider_sends_image_and_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "CLOVA_OCR_URL", "https://example.test/ocr")
    monkeypatch.setattr(config, "CLOVA_OCR_SECRET", "secret-value")
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    text = await ClovaOcrProvider().extract_text(
        file_name="checkup.jpg",
        content_type="image/jpeg",
        content=b"image-bytes",
    )

    request = _FakeAsyncClient.request
    assert "신장: 168.2 cm" in text
    assert request["headers"] == {"X-OCR-SECRET": "secret-value"}
    assert request["files"]["file"][0] == "checkup.jpg"
    message = json.loads(request["data"]["message"])
    assert message["version"] == "V2"
    assert message["images"][0]["format"] == "jpg"


@pytest.mark.asyncio
async def test_clova_provider_rejects_unsupported_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "CLOVA_OCR_URL", "https://example.test/ocr")
    monkeypatch.setattr(config, "CLOVA_OCR_SECRET", "secret-value")

    with pytest.raises(ClovaOcrError, match="JPG"):
        await ClovaOcrProvider().extract_text(
            file_name="checkup.txt",
            content_type="text/plain",
            content=b"not-an-image",
        )


def test_frontend_uploads_image_as_multipart_to_clova_endpoint() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    assert 'accept=".jpg,.jpeg,.png,.pdf,.tif,.tiff' in html
    assert 'formData.append("file", file, file.name)' in script
    assert 'api("/ocr-drafts/from-image", { method: "POST", body: formData })' in script
    assert "await file.text()" not in script
