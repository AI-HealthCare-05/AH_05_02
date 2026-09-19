"""Health-checkup OCR provider selection.

The source image is only kept in memory while an OCR request is processed.  The
returned text is reduced to an editable, allow-listed draft by WellnessService.
"""

from __future__ import annotations

from typing import Protocol

from app.core import config


class OcrProviderError(RuntimeError):
    """External OCR provider configuration or request failure."""


class HealthCheckupOcrProvider(Protocol):
    provider_kind: str

    async def extract_text(self, *, file_name: str, content_type: str | None, content: bytes) -> str: ...


def get_health_checkup_ocr_provider() -> HealthCheckupOcrProvider:
    provider = config.HEALTH_CHECKUP_OCR_PROVIDER.strip().lower()
    if provider == "clova":
        from app.ocr.clova import ClovaOcrProvider

        return ClovaOcrProvider()
    if provider == "claude":
        from app.ocr.claude import ClaudeOcrProvider

        return ClaudeOcrProvider()
    raise OcrProviderError("지원하지 않는 HEALTH_CHECKUP_OCR_PROVIDER입니다. clova 또는 claude를 설정해 주세요.")
