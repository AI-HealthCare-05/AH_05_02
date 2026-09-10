from __future__ import annotations

import re

from src.rag.chunking import Chunk
from src.rag.generation import GeneratedAnswer

_TOKEN_PATTERN = re.compile(r"[\s,·/()\[\]]+")
_MIN_TOKEN_LENGTH = 2
_OVERLAP_RATIO_THRESHOLD = 0.5


def _tokens(text: str) -> set[str]:
    normalized = text.casefold()
    return {token for token in _TOKEN_PATTERN.split(normalized) if len(token) >= _MIN_TOKEN_LENGTH}


def _has_lexical_support(sentence: str, source_texts: list[str]) -> bool:
    sentence_tokens = _tokens(sentence)
    if not sentence_tokens:
        return False
    for source in source_texts:
        source_normalized = source.casefold()
        overlap = sum(1 for token in sentence_tokens if token in source_normalized)
        if overlap / len(sentence_tokens) >= _OVERLAP_RATIO_THRESHOLD:
            return True
    return False


def verify_sentences(generated: GeneratedAnswer, chunks_by_id: dict[str, Chunk]) -> tuple[str, ...]:
    """문장별 출처 검사(stage 6).

    LLM이 스스로 표시한 근거 번호(supporting_chunk_ids)를 무조건 신뢰하지 않고, 그 근거의
    실제 텍스트와 문장 사이에 어휘 중복이 충분한지 다시 확인한다. 근거 번호가 없거나, 넘겨준
    근거 목록에 없는 번호이거나, 실제로 그 근거에서 확인되지 않는 문장은 제거한다.
    """
    verified: list[str] = []
    for sentence in generated.sentences:
        source_texts = [chunks_by_id[chunk_id].text for chunk_id in sentence.supporting_chunk_ids if chunk_id in chunks_by_id]
        if not source_texts:
            continue
        if _has_lexical_support(sentence.text, source_texts):
            verified.append(sentence.text)
    return tuple(verified)


def cited_document_ids(generated: GeneratedAnswer, chunks_by_id: dict[str, Chunk], verified_sentences: tuple[str, ...]) -> tuple[str, ...]:
    """검증을 통과한 문장이 실제로 인용한 문서 id를, 처음 등장한 순서대로 중복 없이 반환한다."""
    verified_set = set(verified_sentences)
    ordered: list[str] = []
    seen: set[str] = set()
    for sentence in generated.sentences:
        if sentence.text not in verified_set:
            continue
        for chunk_id in sentence.supporting_chunk_ids:
            chunk = chunks_by_id.get(chunk_id)
            if chunk is None or chunk.document_id in seen:
                continue
            seen.add(chunk.document_id)
            ordered.append(chunk.document_id)
    return tuple(ordered)
