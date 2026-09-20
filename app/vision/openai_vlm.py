from __future__ import annotations

import base64
import json
import math
from dataclasses import replace

import httpx

from app.core import config
from app.vision.food_vision import FoodVisionError, FoodVisionResult


class VLMUnavailableError(FoodVisionError):
    """VLM failure carrying a stable, non-sensitive public reason code."""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


class OpenAIVegetableVerifier:
    """Semantic fallback for borderline local-CV results; never estimates ratios."""

    def __init__(self) -> None:
        if not config.OPENAI_API_KEY:
            raise VLMUnavailableError("vlm_configuration_incomplete", "OpenAI VLM 설정이 완료되지 않았습니다.")

    async def verify(self, image_bytes: bytes) -> dict[str, object]:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "is_meal_photo": {"type": "boolean"},
                "challenge_relevant": {"type": "boolean"},
                "vegetables_clearly_visible": {"type": "boolean"},
                "image_quality_adequate": {"type": "boolean"},
                "multiple_images_or_screen_capture": {"type": "boolean"},
                "uncertainty_reasons": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
            },
            "required": [
                "is_meal_photo",
                "challenge_relevant",
                "vegetables_clearly_visible",
                "image_quality_adequate",
                "multiple_images_or_screen_capture",
                "uncertainty_reasons",
            ],
        }
        encoded = base64.b64encode(image_bytes).decode("ascii")
        payload = {
            "model": config.OPENAI_VLM_MODEL,
            "store": False,
            "instructions": (
                "채소 식사 인증 사진의 육안 확인 가능성만 판정하세요. 비율, 중량, 영양소, 혈당 영향, "
                "실제 섭취, 치료 효과를 추정하지 마세요. 불명확하면 false와 사유를 반환하세요."
            ),
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "이 사진이 채소 식사 인증 초안으로 확인 가능한가요?"},
                        {"type": "input_image", "image_url": f"data:image/jpeg;base64,{encoded}", "detail": "high"},
                    ],
                }
            ],
            "text": {
                "format": {"type": "json_schema", "name": "vegetable_photo_review", "strict": True, "schema": schema}
            },
            "max_output_tokens": 250,
        }
        try:
            async with httpx.AsyncClient(timeout=config.FOOD_VISION_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    "https://api.openai.com/v1/responses",
                    headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise VLMUnavailableError("vlm_timeout", "OpenAI VLM 요청 시간이 초과되었습니다.") from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code in {401, 403}:
                reason = "vlm_configuration_incomplete"
            elif status_code == 429:
                reason = "vlm_rate_limited"
            else:
                reason = "vlm_service_unavailable"
            raise VLMUnavailableError(reason, "OpenAI VLM 요청을 완료하지 못했습니다.") from exc
        except httpx.HTTPError as exc:
            raise VLMUnavailableError("vlm_connection_failed", "OpenAI VLM에 연결하지 못했습니다.") from exc
        try:
            body = response.json()
            text = next(
                part["text"]
                for item in body["output"]
                for part in item.get("content", [])
                if part.get("type") == "output_text"
            )
            result = json.loads(text)
        except (KeyError, StopIteration, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise VLMUnavailableError("vlm_response_invalid", "OpenAI VLM 응답을 확인하지 못했습니다.") from exc
        if not isinstance(result, dict) or any(type(result.get(key)) is not bool for key in schema["required"][:-1]):
            raise VLMUnavailableError("vlm_response_invalid", "OpenAI VLM 응답 형식이 올바르지 않습니다.")
        reasons = result.get("uncertainty_reasons")
        if not isinstance(reasons, list) or not all(isinstance(reason, str) for reason in reasons):
            raise VLMUnavailableError("vlm_response_invalid", "OpenAI VLM 응답 형식이 올바르지 않습니다.")
        return result


def needs_vlm(result: FoodVisionResult) -> bool:
    food = result.food_coverage_percent
    vegetable = result.vegetable_ratio_percent
    if not all(type(value) in (int, float) and math.isfinite(value) for value in (food, vegetable)):
        return True
    return not result.reliable or 40 <= food < 50 or 20 <= vegetable < 30


async def supplement_with_vlm(result: FoodVisionResult, image_bytes: bytes) -> FoodVisionResult:
    if not needs_vlm(result):
        return result
    try:
        review = await OpenAIVegetableVerifier().verify(image_bytes)
    except FoodVisionError as exc:
        reason_code = getattr(exc, "reason_code", "vlm_service_unavailable")
        return replace(
            result,
            reliable=False,
            decision_status="uncertain",
            uncertainty_reasons=[*result.uncertainty_reasons, reason_code],
        )
    if review["multiple_images_or_screen_capture"] or not review["is_meal_photo"] or not review["challenge_relevant"]:
        decision = "invalid_food_ratio"
    elif not review["image_quality_adequate"]:
        decision = "uncertain"
    elif review["vegetables_clearly_visible"]:
        decision = "valid"
    else:
        decision = "invalid_vegetable_ratio"
    return replace(
        result,
        provider_kind="local_kfood_openai_vlm",
        reliable=decision == "valid",
        decision_status=decision,
        uncertainty_reasons=[str(reason) for reason in review["uncertainty_reasons"]],
        model_version=f"{result.model_version}+{config.OPENAI_VLM_MODEL}",
    )
