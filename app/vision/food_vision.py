from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.core import config

_ALLOWED_CATEGORIES: set[str] = {"곡류", "채소", "과일", "단백질", "유제품", "혼합식", "확인불가"}

_SYSTEM_PROMPT = (
    "당신은 식사 사진을 보고 음식 카테고리, 채소 포함 여부, 접시에서 채소가 차지하는 "
    "대략적인 시각적 비율만 판별하는 보조 도구입니다. "
    "칼로리, 영양소 함량(g/mg 등), 체중 감량 효과, 치료 효과는 절대 계산하거나 언급하지 마세요. "
    "vegetable_ratio_percent는 무게나 열량이 아니라 사진에 보이는 면적 기준의 대략적인 시각적 추정치입니다. "
    "반드시 아래 JSON 스키마로만 답하세요. 설명 문장을 추가하지 마세요.\n"
    '{"predicted_category": "곡류|채소|과일|단백질|유제품|혼합식|확인불가", '
    '"contains_vegetable": true 또는 false, '
    '"vegetable_confidence": 0과 1 사이 숫자, '
    '"vegetable_ratio_percent": 0과 100 사이 숫자(접시에서 채소로 보이는 면적 비율 추정치), '
    '"detected_items": ["사진에서 보이는 음식 이름들"]}'
)


class FoodVisionError(RuntimeError):
    """이미지 인식 provider 호출에 실패했을 때 사용하는 예외입니다."""


@dataclass(frozen=True)
class FoodVisionResult:
    provider_kind: str
    predicted_category: str
    contains_vegetable: bool | None
    vegetable_confidence: float | None
    vegetable_ratio_percent: float | None = None
    detected_items: list[str] = field(default_factory=list)


class FoodVisionProvider(Protocol):
    provider_kind: str

    async def analyze(self, image_bytes: bytes, mime_type: str, filename: str) -> FoodVisionResult: ...


class DevelopmentFoodVisionProvider:
    """실제 이미지 픽셀을 분석하지 않는 개발용 어댑터입니다.

    기존 /food-analyses 목업과 동일하게 파일명 키워드로 결정적인 결과를 돌려주어,
    provider 인터페이스와 챌린지 연동을 실제 Vision API 없이도 검증할 수 있게 합니다.
    운영 환경에서는 FOOD_VISION_PROVIDER=openai로 전환해서 사용하지 않습니다.
    """

    provider_kind = "development_mock"

    _KEYWORDS: dict[str, tuple[str, ...]] = {
        "곡류": ("rice", "bap", "bread", "noodle", "밥", "빵", "면"),
        "채소": ("vegetable", "salad", "greens", "veggie", "채소", "샐러드", "나물"),
        "과일": ("fruit", "apple", "banana", "과일", "사과", "바나나"),
        "단백질": ("meat", "fish", "egg", "tofu", "고기", "생선", "달걀", "두부"),
        "유제품": ("milk", "yogurt", "cheese", "우유", "요거트", "치즈"),
    }

    async def analyze(self, image_bytes: bytes, mime_type: str, filename: str) -> FoodVisionResult:
        del image_bytes, mime_type  # 실제 픽셀은 보지 않는 개발용 어댑터입니다.
        normalized = filename.casefold()
        matches = [category for category, words in self._KEYWORDS.items() if any(word in normalized for word in words)]
        category = matches[0] if len(matches) == 1 else "확인불가"
        contains_vegetable = category == "채소"
        confidence = 0.55 if matches else None
        ratio = 65.0 if contains_vegetable else (15.0 if matches else None)
        return FoodVisionResult(
            provider_kind=self.provider_kind,
            predicted_category=category,
            contains_vegetable=contains_vegetable,
            vegetable_confidence=confidence,
            vegetable_ratio_percent=ratio,
            detected_items=[category] if category != "확인불가" else [],
        )


class OpenAIFoodVisionProvider:
    """OpenAI의 이미지 인식 가능한 Chat Completions API로 채소 포함 여부만 판별합니다."""

    provider_kind = "openai_vision"

    def __init__(self) -> None:
        if not config.OPENAI_API_KEY:
            raise FoodVisionError("OPENAI_API_KEY가 설정되어 있지 않습니다. .env에 키를 추가한 뒤 다시 시도해주세요.")
        self._api_key = config.OPENAI_API_KEY
        self._model = config.OPENAI_MODEL

    _SUPPORTED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

    async def analyze(self, image_bytes: bytes, mime_type: str, filename: str) -> FoodVisionResult:
        del filename
        if mime_type not in self._SUPPORTED_MIME_TYPES:
            raise FoodVisionError(
                "이 이미지 형식은 AI 인식이 지원하지 않습니다(HEIC 등). jpg·png·webp로 변환해서 다시 업로드해주세요."
            )
        encoded = base64.b64encode(image_bytes).decode("ascii")
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "이 식사 사진에 채소가 포함되어 있는지 판별해줘."},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}},
                    ],
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "max_tokens": 300,
        }
        try:
            async with httpx.AsyncClient(timeout=config.FOOD_VISION_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise FoodVisionError("이미지 인식 요청이 시간 초과되었습니다. 잠시 후 다시 시도해주세요.") from exc
        except httpx.HTTPStatusError as exc:
            raise FoodVisionError(f"이미지 인식 provider 호출에 실패했습니다: {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise FoodVisionError("이미지 인식 provider에 연결할 수 없습니다.") from exc

        body = response.json()
        try:
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            category = parsed.get("predicted_category", "확인불가")
            if category not in _ALLOWED_CATEGORIES:
                category = "확인불가"
            contains_vegetable = parsed.get("contains_vegetable")
            confidence = parsed.get("vegetable_confidence")
            ratio = parsed.get("vegetable_ratio_percent")
            detected_items = parsed.get("detected_items") or []
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise FoodVisionError("이미지 인식 결과를 해석하지 못했습니다.") from exc

        return FoodVisionResult(
            provider_kind=self.provider_kind,
            predicted_category=category,
            contains_vegetable=bool(contains_vegetable) if contains_vegetable is not None else None,
            vegetable_confidence=float(confidence) if isinstance(confidence, int | float) else None,
            vegetable_ratio_percent=max(0.0, min(100.0, float(ratio))) if isinstance(ratio, int | float) else None,
            detected_items=[str(item) for item in detected_items][:10],
        )


def get_food_vision_provider() -> FoodVisionProvider:
    if config.FOOD_VISION_PROVIDER == "development":
        return DevelopmentFoodVisionProvider()
    if config.FOOD_VISION_PROVIDER == "openai":
        return OpenAIFoodVisionProvider()
    raise FoodVisionError(f"지원하지 않는 FOOD_VISION_PROVIDER입니다: {config.FOOD_VISION_PROVIDER}")


def sha256_digest(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()
