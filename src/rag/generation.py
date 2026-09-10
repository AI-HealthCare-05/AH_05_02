from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core import config
from src.rag.chunking import Chunk

_SYSTEM_PROMPT = (
    "당신은 아래 근거(각 줄 맨 앞 대괄호 안 번호가 근거 번호입니다) 안에서만 답변을 작성하는 "
    "건강교육 보조 도구입니다. 근거에 없는 내용, 진단, 처방, 치료 효과는 절대 추가하지 마세요. "
    "답변은 문장 단위로 나누고, 각 문장이 실제로 근거로 삼은 근거 번호를 모두 표시하세요. "
    "제공된 근거만으로 질문에 답할 수 없으면 sentences를 빈 배열로 반환하세요. "
    "반드시 아래 JSON 스키마로만 답하세요. 설명 문장을 추가하지 마세요.\n"
    '{"sentences": [{"text": "문장", "supporting_chunk_ids": ["근거번호", ...]}]}'
)


class AnswerGenerationError(RuntimeError):
    """답변 생성 provider 호출에 실패했을 때 사용하는 예외입니다."""


@dataclass(frozen=True)
class GeneratedSentence:
    text: str
    supporting_chunk_ids: tuple[str, ...]


@dataclass(frozen=True)
class GeneratedAnswer:
    provider_kind: str
    sentences: tuple[GeneratedSentence, ...]


class AnswerGenerationProvider(Protocol):
    provider_kind: str

    async def generate(self, question: str, chunks: tuple[Chunk, ...]) -> GeneratedAnswer: ...


class DevelopmentAnswerGenerationProvider:
    """LLM을 호출하지 않고 상위 근거 문장을 그대로 이어붙이는 개발용 어댑터입니다.

    각 문장은 자기 자신의 chunk_id만 근거로 가지므로 문장별 출처 검사(stage 6)를 항상
    통과하며, 재현 가능한(같은 입력 → 같은 결과) 동작을 보장합니다. 운영 환경에서는
    HEALTH_EDUCATION_GENERATION_PROVIDER=openai로 전환해서 사용하지 않습니다.
    """

    provider_kind = "development_concat"

    async def generate(self, question: str, chunks: tuple[Chunk, ...]) -> GeneratedAnswer:
        del question
        sentences = tuple(
            GeneratedSentence(text=chunk.text, supporting_chunk_ids=(chunk.chunk_id,)) for chunk in chunks
        )
        return GeneratedAnswer(provider_kind=self.provider_kind, sentences=sentences)


class OpenAIAnswerGenerationProvider:
    """OpenAI Chat Completions API로 근거 제한 답변을 생성합니다."""

    provider_kind = "openai_generation"

    def __init__(self) -> None:
        if not config.OPENAI_API_KEY:
            raise AnswerGenerationError("OPENAI_API_KEY가 설정되어 있지 않습니다. .env에 키를 추가한 뒤 다시 시도해주세요.")
        self._api_key = config.OPENAI_API_KEY
        self._model = config.OPENAI_MODEL

    async def generate(self, question: str, chunks: tuple[Chunk, ...]) -> GeneratedAnswer:
        valid_chunk_ids = {chunk.chunk_id for chunk in chunks}
        context = "\n".join(f"[{chunk.chunk_id}] {chunk.text}" for chunk in chunks)
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"질문: {question}\n\n근거:\n{context}"},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "max_tokens": 800,
        }
        try:
            async with httpx.AsyncClient(timeout=config.HEALTH_EDUCATION_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise AnswerGenerationError("답변 생성 요청이 시간 초과되었습니다. 잠시 후 다시 시도해주세요.") from exc
        except httpx.HTTPStatusError as exc:
            raise AnswerGenerationError(f"답변 생성 provider 호출에 실패했습니다: {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise AnswerGenerationError("답변 생성 provider에 연결할 수 없습니다.") from exc

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AnswerGenerationError("답변 생성 결과를 해석하지 못했습니다.") from exc
        sentences = self._parse_sentences(content, valid_chunk_ids)
        return GeneratedAnswer(provider_kind=self.provider_kind, sentences=sentences)

    def _parse_sentences(self, content: str, valid_chunk_ids: set[str]) -> tuple[GeneratedSentence, ...]:
        try:
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise ValueError("The response must be a JSON object")
            raw_sentences = parsed["sentences"]
            if not isinstance(raw_sentences, list):
                raise ValueError("sentences must be a JSON array")
            sentences: list[GeneratedSentence] = []
            for item in raw_sentences:
                if not isinstance(item, dict):
                    raise ValueError("each sentence must be a JSON object")
                text = item.get("text")
                if not isinstance(text, str) or not text.strip():
                    continue
                raw_ids = item.get("supporting_chunk_ids") or []
                if not isinstance(raw_ids, list):
                    raise ValueError("supporting_chunk_ids must be a JSON array")
                ids = tuple(chunk_id for chunk_id in raw_ids if chunk_id in valid_chunk_ids)
                sentences.append(GeneratedSentence(text=text.strip(), supporting_chunk_ids=ids))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AnswerGenerationError("답변 생성 결과를 해석하지 못했습니다.") from exc
        return tuple(sentences)


def get_generation_provider() -> AnswerGenerationProvider:
    if config.HEALTH_EDUCATION_GENERATION_PROVIDER == "development":
        return DevelopmentAnswerGenerationProvider()
    if config.HEALTH_EDUCATION_GENERATION_PROVIDER == "openai":
        return OpenAIAnswerGenerationProvider()
    raise AnswerGenerationError(
        f"지원하지 않는 HEALTH_EDUCATION_GENERATION_PROVIDER입니다: {config.HEALTH_EDUCATION_GENERATION_PROVIDER}"
    )
