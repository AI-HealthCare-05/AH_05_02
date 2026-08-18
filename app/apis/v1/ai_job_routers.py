import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.redis import redis_client
from app.dtos.ai_jobs import AIJobCreateRequest, AIJobResponse
from app.services.ai_jobs import create_ai_job, get_ai_job, job_channel

ai_job_router = APIRouter(prefix="/ai-jobs", tags=["AI Jobs"])


def to_response(job: object) -> AIJobResponse:
    return AIJobResponse.model_validate(job, from_attributes=True)


@ai_job_router.post("", response_model=AIJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_ai_job(request: AIJobCreateRequest) -> AIJobResponse:
    try:
        job = await create_ai_job(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return to_response(job)


@ai_job_router.get("/{job_id}", response_model=AIJobResponse)
async def read_ai_job(job_id: str) -> AIJobResponse:
    job = await get_ai_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI 작업을 찾을 수 없습니다.")
    return to_response(job)


async def stream_job_events(job_id: str) -> AsyncIterator[str]:
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(job_channel(job_id))
    try:
        current = await get_ai_job(job_id)
        if current is None:
            return
        initial = to_response(current).model_dump(mode="json")
        yield f"event: status\ndata: {json.dumps(initial, ensure_ascii=False)}\n\n"
        if current.status in {"completed", "failed"}:
            return

        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
            if message is None:
                yield ": keep-alive\n\n"
                continue
            data = message["data"]
            event = json.loads(data)
            yield f"event: status\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            if event.get("status") in {"completed", "failed"}:
                return
    finally:
        await pubsub.unsubscribe(job_channel(job_id))
        await pubsub.aclose()


@ai_job_router.get("/{job_id}/events")
async def read_ai_job_events(job_id: str) -> StreamingResponse:
    if await get_ai_job(job_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI 작업을 찾을 수 없습니다.")
    return StreamingResponse(
        stream_job_events(job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
