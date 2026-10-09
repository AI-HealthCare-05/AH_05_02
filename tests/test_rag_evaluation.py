from __future__ import annotations

import pytest

from src.rag.evaluation import DEFAULT_DATASET, evaluate, load_cases


def test_golden_dataset_has_retrieval_and_medical_safety_cases() -> None:
    cases = load_cases(DEFAULT_DATASET)

    assert len(cases) >= 10
    assert any(case["expected_status"] == "medical_safety_refusal" for case in cases)
    assert any(case["expected_status"] == "emergency_redirect" for case in cases)


@pytest.mark.asyncio
async def test_development_rag_meets_quality_floor() -> None:
    metrics = await evaluate(load_cases(DEFAULT_DATASET), top_k=6)

    assert metrics.recall_at_k >= 0.90
    assert metrics.mrr >= 0.80
    assert metrics.status_accuracy == 1.0
