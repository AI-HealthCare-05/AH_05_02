"""Claude Vision adapter for health-checkup text transcription.

This adapter deliberately returns transcription only.  Field extraction,
allow-listing and the user's final confirmation remain inside this service.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import httpx

from app.core import config
from app.ocr.providers import OcrProviderError


class ClaudeOcrProvider:
    provider_kind = "claude_vision_api"
    _API_URL = "https://api.anthropic.com/v1/messages"
    _SUPPORTED_TYPES = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
    }
    _TYPE_BY_SUFFIX = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
    }
    _PROMPT = """You transcribe Korean general health-checkup result notices.
Return only literal, readable measurement lines for these labels when present:
검진일, 신장, 체중, 허리둘레, BMI, 혈압, 공복혈당, 총콜레스테롤,
HDL 콜레스테롤, 중성지방, LDL 콜레스테롤, 크레아티닌, AST, ALT, 감마GTP.
Keep the printed number and unit. Do not calculate, infer, diagnose, recommend,
or fill in missing values. Do not return name, resident number, address, phone,
health institution number, barcode, or any other identifier. If a value is not
clearly readable, omit it instead of guessing."""

    def __init__(self) -> None:
        if not config.ANTHROPIC_API_KEY.strip():
            raise OcrProviderError("ANTHROPIC_API_KEY가 설정되어 있지 않습니다.")

    @classmethod
    def _media_type(cls, file_name: str, content_type: str | None) -> str:
        media_type = (content_type or "").split(";", maxsplit=1)[0].strip().lower()
        media_type = (
            media_type
            if media_type in cls._SUPPORTED_TYPES
            else cls._TYPE_BY_SUFFIX.get(Path(file_name).suffix.lower(), "")
        )
        if media_type not in cls._SUPPORTED_TYPES:
            raise OcrProviderError("Claude OCR은 JPG, PNG, WebP 또는 PDF 파일만 지원합니다.")
        return media_type

    @classmethod
    def _document_block(cls, *, media_type: str, content: bytes) -> dict[str, Any]:
        encoded = base64.b64encode(content).decode("ascii")
        if media_type == "application/pdf":
            return {
                "type": "document",
                "source": {"type": "base64", "media_type": media_type, "data": encoded},
            }
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": encoded},
        }

    @staticmethod
    def _parse_text(payload: dict[str, Any]) -> str:
        content = payload.get("content")
        if not isinstance(content, list):
            raise OcrProviderError("Claude OCR 응답 형식을 해석하지 못했습니다.")
        text = "\n".join(
            item.get("text", "").strip()
            for item in content
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str)
        )
        if not text:
            raise OcrProviderError("문서에서 읽을 수 있는 건강검진 수치를 찾지 못했습니다.")
        return text

    async def extract_text(self, *, file_name: str, content_type: str | None, content: bytes) -> str:
        if not content:
            raise OcrProviderError("비어 있는 파일은 인식할 수 없습니다.")
        if len(content) > config.CLAUDE_OCR_MAX_BYTES:
            raise OcrProviderError("Claude OCR 파일은 10MB 이하만 업로드할 수 있습니다.")
        media_type = self._media_type(file_name, content_type)
        request_body = {
            "model": config.CLAUDE_OCR_MODEL,
            "max_tokens": 1_200,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        self._document_block(media_type=media_type, content=content),
                        {"type": "text", "text": self._PROMPT},
                    ],
                }
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=config.CLAUDE_OCR_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    self._API_URL,
                    headers={
                        "x-api-key": config.ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json=request_body,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise OcrProviderError("Claude OCR 처리 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.") from exc
        except httpx.HTTPStatusError as exc:
            raise OcrProviderError(
                f"Claude OCR 서비스가 요청을 처리하지 못했습니다({exc.response.status_code})."
            ) from exc
        except httpx.HTTPError as exc:
            raise OcrProviderError("Claude OCR 서비스에 연결할 수 없습니다.") from exc
        return self._parse_text(response.json())
