import pytest

from ai_worker import handlers
from ai_worker.handlers import run_task, run_task_with_timeout


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


@pytest.mark.asyncio
async def test_worker_timeout_is_raised_for_status_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    async def slow_task(task_type: str, payload: dict[str, object]) -> dict[str, object]:
        await handlers.asyncio.sleep(0.05)
        return {"task_type": task_type, "payload": payload}

    monkeypatch.setattr(handlers, "run_task", slow_task)
    with pytest.raises(TimeoutError):
        await run_task_with_timeout("diabetes_incidence", {}, timeout_seconds=0.001)
