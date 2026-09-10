from __future__ import annotations

import re
from dataclasses import dataclass

# 문장 끝 부호(.!?) 뒤에 공백이 오는 지점에서만 자른다. "6.5%"처럼 숫자 뒤 공백 없이
# 이어지는 마침표는 문장 경계로 취급하지 않는다.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_MIN_CHUNK_LENGTH = 8


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    index: int
    text: str


def split_sentences(text: str) -> tuple[str, ...]:
    """본문을 문장 단위로 나눈다. 너무 짧은 조각은 바로 앞 문장에 합친다."""
    raw_sentences = [sentence.strip() for sentence in _SENTENCE_BOUNDARY.split(text.strip()) if sentence.strip()]
    if not raw_sentences:
        return ()
    merged: list[str] = [raw_sentences[0]]
    for sentence in raw_sentences[1:]:
        if len(sentence) < _MIN_CHUNK_LENGTH:
            merged[-1] = f"{merged[-1]} {sentence}"
        else:
            merged.append(sentence)
    return tuple(merged)


def split_into_chunks(document_id: str, text: str) -> tuple[Chunk, ...]:
    """문서 하나(document_id, text)를 문장 단위 청크로 나눈다.

    engine.KnowledgeDocument에 의존하지 않고 document_id/text만 받는 이유는, engine.py가
    이 모듈을 import해서 APPROVED_DOCUMENTS로부터 청크를 만들기 때문이다(순환 import 방지).
    """
    sentences = split_sentences(text) or (text.strip(),)
    return tuple(
        Chunk(chunk_id=f"{document_id}#{index}", document_id=document_id, index=index, text=sentence)
        for index, sentence in enumerate(sentences)
    )
