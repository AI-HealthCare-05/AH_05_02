import pytest

from ai_worker.handlers import run_task


@pytest.mark.asyncio
async def test_demo_inference_proves_pipeline_without_medical_prediction() -> None:
    result = await run_task("demo_inference", {"source": "test", "value": 1})

    assert result["is_demo"] is True
    assert result["pipeline"] == "redis-stream-consumer-group"
    assert result["received_fields"] == ["source", "value"]
    assert "진단·처방이 아닙니다" in result["medical_notice"]


@pytest.mark.asyncio
async def test_model_inference_requires_feature_array() -> None:
    with pytest.raises(ValueError, match="features 배열"):
        await run_task("model_inference", {"features": []})


@pytest.mark.asyncio
async def test_unknown_task_type_is_rejected() -> None:
    with pytest.raises(ValueError, match="지원하지 않는 task_type"):
        await run_task("unknown", {})
