from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TypedDict

from src.rag.embeddings import DevelopmentEmbeddingProvider
from src.rag.engine import ALL_CHUNKS, KEYWORDS_BY_DOCUMENT, answer_with_sources
from src.rag.retrieval import hybrid_search

DEFAULT_DATASET = Path("experiments/rag_evaluation/golden_questions.json")


class EvaluationCase(TypedDict):
    question: str
    expected_document_ids: list[str]
    expected_status: str


@dataclass(frozen=True)
class EvaluationMetrics:
    retrieval_cases: int
    status_cases: int
    recall_at_k: float
    mrr: float
    status_accuracy: float


def load_cases(path: Path) -> list[EvaluationCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("RAG 평가셋은 비어 있지 않은 JSON 배열이어야 합니다.")
    return raw


async def evaluate(cases: list[EvaluationCase], *, top_k: int = 6) -> EvaluationMetrics:
    recalls: list[float] = []
    reciprocal_ranks: list[float] = []
    correct_statuses = 0
    provider = DevelopmentEmbeddingProvider()

    for case in cases:
        expected = set(case["expected_document_ids"])
        if expected and case["expected_status"] == "grounded":
            scored = await hybrid_search(
                case["question"],
                chunks=ALL_CHUNKS,
                keyword_lookup=KEYWORDS_BY_DOCUMENT,
                embedding_provider=provider,
            )
            ranked_documents: list[str] = []
            for item in scored:
                if item.chunk.document_id not in ranked_documents:
                    ranked_documents.append(item.chunk.document_id)
                if len(ranked_documents) == top_k:
                    break
            hits = expected.intersection(ranked_documents)
            recalls.append(len(hits) / len(expected))
            first_rank = next(
                (rank for rank, document_id in enumerate(ranked_documents, start=1) if document_id in expected),
                None,
            )
            reciprocal_ranks.append(0.0 if first_rank is None else 1.0 / first_rank)

        result = await answer_with_sources(case["question"])
        correct_statuses += result["answer_status"] == case["expected_status"]

    return EvaluationMetrics(
        retrieval_cases=len(recalls),
        status_cases=len(cases),
        recall_at_k=sum(recalls) / len(recalls) if recalls else 0.0,
        mrr=sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0,
        status_accuracy=correct_statuses / len(cases),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate health-education RAG retrieval and safety routing.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--min-recall", type=float, default=0.90)
    parser.add_argument("--min-mrr", type=float, default=0.80)
    parser.add_argument("--min-status-accuracy", type=float, default=1.0)
    args = parser.parse_args()

    metrics = asyncio.run(evaluate(load_cases(args.dataset), top_k=args.top_k))
    print(json.dumps(asdict(metrics), ensure_ascii=False, indent=2))
    if (
        metrics.recall_at_k < args.min_recall
        or metrics.mrr < args.min_mrr
        or metrics.status_accuracy < args.min_status_accuracy
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
