"""Verify configured external providers without printing credentials."""

from __future__ import annotations

import asyncio
import io
import json
import sys
from pathlib import Path

import httpx
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import config  # noqa: E402
from app.ocr.clova import ClovaOcrError, ClovaOcrProvider  # noqa: E402


async def verify_kakao() -> dict[str, object]:
    if not config.KAKAO_REST_API_KEY.strip():
        return {"status": "not_configured"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://dapi.kakao.com/v2/local/search/keyword.json",
                headers={"Authorization": f"KakaoAK {config.KAKAO_REST_API_KEY}"},
                params={"query": "내과", "x": 127.0276, "y": 37.4979, "radius": 5000, "size": 1},
            )
            response.raise_for_status()
            count = len(response.json().get("documents") or [])
    except httpx.HTTPStatusError as exc:
        try:
            public_error = exc.response.json()
        except ValueError:
            public_error = {}
        return {
            "status": "failed",
            "http_status": exc.response.status_code,
            "provider_error": public_error.get("errorType"),
            "provider_message": public_error.get("message"),
        }
    except (httpx.HTTPError, ValueError) as exc:
        return {"status": "failed", "error_type": type(exc).__name__}
    return {
        "status": "ok",
        "result_count": count,
        "javascript_key_configured": bool(config.KAKAO_JAVASCRIPT_KEY.strip()),
        "note": "JavaScript 키의 등록 도메인은 브라우저에서 별도 확인해야 합니다.",
    }


async def verify_openai() -> dict[str, object]:
    if not config.OPENAI_API_KEY.strip():
        return {"status": "not_configured"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
            )
            response.raise_for_status()
    except (httpx.HTTPError, ValueError) as exc:
        return {"status": "failed", "error_type": type(exc).__name__}
    return {"status": "ok", "configured_model": config.OPENAI_MODEL}


def synthetic_health_check_image() -> bytes:
    image = Image.new("RGB", (1000, 320), "white")
    draw = ImageDraw.Draw(image)
    draw.text((40, 40), "2025 HEALTH CHECK RESULT", fill="black")
    draw.text((40, 105), "HEIGHT 170 cm   WEIGHT 70 kg", fill="black")
    draw.text((40, 170), "FASTING GLUCOSE 110 mg/dL", fill="black")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


async def verify_clova() -> dict[str, object]:
    if not config.CLOVA_OCR_URL.strip() or not config.CLOVA_OCR_SECRET.strip():
        return {"status": "not_configured"}
    try:
        text = await ClovaOcrProvider().extract_text(
            file_name="synthetic-health-check.png",
            content_type="image/png",
            content=synthetic_health_check_image(),
        )
    except (ClovaOcrError, httpx.HTTPError, ValueError) as exc:
        return {"status": "failed", "error_type": type(exc).__name__}
    return {"status": "ok", "text_detected": bool(text.strip())}


async def main() -> int:
    results = {
        "kakao": await verify_kakao(),
        "openai": await verify_openai(),
        "clova_ocr": await verify_clova(),
    }
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(item["status"] == "ok" for item in results.values()) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
