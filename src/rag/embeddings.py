from __future__ import annotations

import hashlib
import math
from typing import Protocol

import httpx

from app.core import config


class EmbeddingError(RuntimeError):
    """임베딩 provider 호출에 실패했을 때 사용하는 예외입니다."""


class EmbeddingProvider(Protocol):
    provider_kind: str

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class DevelopmentEmbeddingProvider:
    """실제 임베딩 모델을 호출하지 않는 개발용 어댑터입니다.

    문자 2~3그램 해싱 트릭(hashing trick)으로 결정적인 벡터를 만들어, 완전히 같은 키워드가
    아니어도 글자가 겹치면 코사인 유사도가 어느 정도 올라가는 근사치를 제공합니다. 실제 의미
    이해(동의어·문맥 이해)는 하지 못하므로, 운영 환경에서는
    HEALTH_EDUCATION_EMBEDDING_PROVIDER=openai로 전환해서 사용하지 않습니다.
    """

    provider_kind = "development_hashing"
    dimensions = 256

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        normalized = "".join(text.casefold().split())
        vector = [0.0] * self.dimensions
        grams: set[str] = set()
        for size in (2, 3):
            for start in range(len(normalized) - size + 1):
                grams.add(normalized[start : start + size])
        for gram in grams:
            digest = hashlib.md5(gram.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class OpenAIEmbeddingProvider:
    """OpenAI Embeddings API로 실제 의미 기반 벡터를 계산합니다."""

    provider_kind = "openai_embedding"

    def __init__(self) -> None:
        if not config.OPENAI_API_KEY:
            raise EmbeddingError("OPENAI_API_KEY가 설정되어 있지 않습니다. .env에 키를 추가한 뒤 다시 시도해주세요.")
        self._api_key = config.OPENAI_API_KEY
        self._model = config.HEALTH_EDUCATION_EMBEDDING_MODEL

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            async with httpx.AsyncClient(timeout=config.HEALTH_EDUCATION_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                    json={"model": self._model, "input": texts},
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise EmbeddingError("임베딩 요청이 시간 초과되었습니다. 잠시 후 다시 시도해주세요.") from exc
        except httpx.HTTPStatusError as exc:
            raise EmbeddingError(f"임베딩 provider 호출에 실패했습니다: {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise EmbeddingError("임베딩 provider에 연결할 수 없습니다.") from exc
        try:
            body = response.json()
            items = sorted(body["data"], key=lambda item: item["index"])
            return [item["embedding"] for item in items]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise EmbeddingError("임베딩 결과를 해석하지 못했습니다.") from exc


def get_embedding_provider() -> EmbeddingProvider:
    if config.HEALTH_EDUCATION_EMBEDDING_PROVIDER == "development":
        return DevelopmentEmbeddingProvider()
    if config.HEALTH_EDUCATION_EMBEDDING_PROVIDER == "openai":
        return OpenAIEmbeddingProvider()
    raise EmbeddingError(f"지원하지 않는 HEALTH_EDUCATION_EMBEDDING_PROVIDER입니다: {config.HEALTH_EDUCATION_EMBEDDING_PROVIDER}")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
