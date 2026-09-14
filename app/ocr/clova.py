from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import httpx

from app.core import config


class ClovaOcrError(RuntimeError):
    """Clova OCR 요청 또는 응답 처리 실패."""


class ClovaOcrProvider:
    _FORMAT_BY_CONTENT_TYPE = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "application/pdf": "pdf",
        "image/tiff": "tif",
    }
    _FORMAT_BY_SUFFIX = {".jpg": "jpg", ".jpeg": "jpg", ".png": "png", ".pdf": "pdf", ".tif": "tif", ".tiff": "tif"}

    def __init__(self) -> None:
        if not config.CLOVA_OCR_URL.strip() or not config.CLOVA_OCR_SECRET.strip():
            raise ClovaOcrError("Clova OCR 연결 정보가 설정되어 있지 않습니다.")

    def _validate_file(self, *, file_name: str, content_type: str | None, content: bytes) -> str:
        if not content:
            raise ClovaOcrError("비어 있는 파일은 인식할 수 없습니다.")
        if len(content) > config.CLOVA_OCR_MAX_BYTES:
            raise ClovaOcrError("OCR 파일은 10MB 이하만 업로드할 수 있습니다.")
        image_format = self._FORMAT_BY_CONTENT_TYPE.get(content_type or "")
        if image_format is None:
            image_format = self._FORMAT_BY_SUFFIX.get(Path(file_name).suffix.lower())
        if image_format is None:
            raise ClovaOcrError("JPG, PNG, PDF 또는 TIFF 파일만 업로드할 수 있습니다.")
        return image_format

    @staticmethod
    def _parse_text(payload: dict[str, object]) -> str:
        try:
            images = payload.get("images") or []
            if not images:
                raise ValueError("images missing")
            image = images[0]
            if image.get("inferResult") not in (None, "SUCCESS"):
                raise ValueError(str(image.get("message") or image.get("inferResult")))
            words = [str(field.get("inferText") or "").strip() for field in image.get("fields") or []]
            text = "\n".join(word for word in words if word)
        except (AttributeError, TypeError, ValueError, KeyError) as exc:
            raise ClovaOcrError("OCR 응답 형식을 해석하지 못했습니다.") from exc
        if not text:
            raise ClovaOcrError("문서에서 읽을 수 있는 글자를 찾지 못했습니다.")
        return text

    async def extract_text(self, *, file_name: str, content_type: str | None, content: bytes) -> str:
        image_format = self._validate_file(file_name=file_name, content_type=content_type, content=content)
        message = {
            "version": "V2",
            "requestId": str(uuid.uuid4()),
            "timestamp": int(time.time() * 1000),
            "images": [{"format": image_format, "name": Path(file_name).stem[:100] or "health-checkup"}],
        }
        try:
            async with httpx.AsyncClient(timeout=config.CLOVA_OCR_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    config.CLOVA_OCR_URL,
                    headers={"X-OCR-SECRET": config.CLOVA_OCR_SECRET},
                    data={"message": json.dumps(message, ensure_ascii=False)},
                    files={"file": (file_name, content, content_type or "application/octet-stream")},
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ClovaOcrError("OCR 처리 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.") from exc
        except httpx.HTTPStatusError as exc:
            raise ClovaOcrError(f"OCR 서비스가 요청을 처리하지 못했습니다({exc.response.status_code}).") from exc
        except httpx.HTTPError as exc:
            raise ClovaOcrError("OCR 서비스에 연결할 수 없습니다.") from exc
        return self._parse_text(response.json())
