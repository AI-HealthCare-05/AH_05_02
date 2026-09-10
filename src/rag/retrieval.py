from __future__ import annotations

from dataclasses import dataclass

from app.core import config
from src.rag.chunking import Chunk
from src.rag.embeddings import EmbeddingProvider, cosine_similarity

# provider_kind -> {chunk_id: vector}. 승인 문서(APPROVED_DOCUMENTS)는 프로세스 실행 중 바뀌지
# 않으므로, provider별로 한 번만 계산해서 재사용한다(재계산 비용·지연시간 절약).
_embedding_cache: dict[str, dict[str, list[float]]] = {}


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    keyword_score: float
    embedding_score: float
    combined_score: float


async def _corpus_embeddings(chunks: tuple[Chunk, ...], provider: EmbeddingProvider) -> dict[str, list[float]]:
    cached = _embedding_cache.get(provider.provider_kind)
    if cached is not None:
        return cached
    vectors = await provider.embed([chunk.text for chunk in chunks])
    mapping = {chunk.chunk_id: vector for chunk, vector in zip(chunks, vectors)}
    _embedding_cache[provider.provider_kind] = mapping
    return mapping


def _keyword_scores(chunks: tuple[Chunk, ...], keyword_lookup: dict[str, tuple[str, ...]], normalized_question: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    for chunk in chunks:
        keywords = keyword_lookup.get(chunk.document_id, ())
        scores[chunk.chunk_id] = float(sum(1 for keyword in keywords if keyword.casefold() in normalized_question))
    return scores


# 질문마다 후보 안에서 min-max 정규화를 하면, 진짜 관련 있는 문서가 하나도 없어도 "그나마 제일
# 덜 무관한" 청크의 점수가 항상 1.0 근처로 튀어 올라 관련도 임계값(threshold)이 무력화된다.
# 그래서 배치 내 정규화 대신, 절대 척도로 두 점수를 0~1 사이로 눌러서(saturate) 합친다.
_KEYWORD_SATURATION_COUNT = 2.0  # 키워드 2개 이상 겹치면 이미 충분한 신호로 보고 1.0으로 포화시킨다.


def _keyword_feature(raw_score: float) -> float:
    return min(raw_score / _KEYWORD_SATURATION_COUNT, 1.0)


def _embedding_feature(raw_score: float) -> float:
    return max(0.0, min(raw_score, 1.0))


async def hybrid_search(
    question: str,
    *,
    chunks: tuple[Chunk, ...],
    keyword_lookup: dict[str, tuple[str, ...]],
    embedding_provider: EmbeddingProvider,
) -> tuple[ScoredChunk, ...]:
    """② 키워드 + 임베딩 혼합 검색, ④ 상위 근거 재정렬(rerank)까지 한 번에 수행한다.

    키워드 점수(문서에 등록된 keywords가 질문 문자열에 포함되는 개수)와 임베딩 코사인 유사도를
    절대 척도로 0~1 사이로 눌러(saturate) 가중합해서 결합 점수(combined_score)를 만들고, 그 점수
    내림차순(동점이면 document_id, chunk 순서로 결정적 tie-break)으로 정렬해 반환한다. 질문 하나의
    후보 집합 안에서만 상대적으로 정규화하지 않는 이유는 관련도 임계값(③)이 항상 의미를 갖게 하기
    위해서다 — 절대 무관한 질문이라도 배치 내 정규화를 쓰면 "그나마 나은" 청크가 1.0에 가까워진다.
    """
    normalized_question = question.strip().casefold()
    keyword_raw = _keyword_scores(chunks, keyword_lookup, normalized_question)

    corpus_vectors = await _corpus_embeddings(chunks, embedding_provider)
    question_vectors = await embedding_provider.embed([normalized_question])
    question_vector = question_vectors[0] if question_vectors else []
    embedding_raw = {
        chunk.chunk_id: cosine_similarity(question_vector, corpus_vectors.get(chunk.chunk_id, []))
        for chunk in chunks
    }

    keyword_weight = config.HEALTH_EDUCATION_KEYWORD_WEIGHT
    embedding_weight = config.HEALTH_EDUCATION_EMBEDDING_WEIGHT
    scored = [
        ScoredChunk(
            chunk=chunk,
            keyword_score=keyword_raw[chunk.chunk_id],
            embedding_score=embedding_raw[chunk.chunk_id],
            combined_score=(
                keyword_weight * _keyword_feature(keyword_raw[chunk.chunk_id])
                + embedding_weight * _embedding_feature(embedding_raw[chunk.chunk_id])
            ),
        )
        for chunk in chunks
    ]
    scored.sort(key=lambda item: (-item.combined_score, item.chunk.document_id, item.chunk.index))
    return tuple(scored)


def top_chunks(scored: tuple[ScoredChunk, ...], limit: int = 0) -> tuple[Chunk, ...]:
    count = limit or config.HEALTH_EDUCATION_TOP_K
    return tuple(item.chunk for item in scored[:count])
