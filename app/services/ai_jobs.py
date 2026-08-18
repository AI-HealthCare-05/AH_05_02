import json
from datetime import UTC, datetime
from uuid import uuid4

from app.core import config
from app.core.redis import redis_client
from app.dtos.ai_jobs import AIJobCreateRequest
from app.models.ai_jobs import AIJob


def job_channel(job_id: str) -> str:
    return f"ai:jobs:{job_id}:events"


def job_cache_key(job_id: str) -> str:
    return f"ai:jobs:{job_id}"


async def publish_job_event(job_id: str, event: dict[str, object]) -> None:
    await redis_client.publish(job_channel(job_id), json.dumps(event, ensure_ascii=False, default=str))


async def create_ai_job(request: AIJobCreateRequest) -> AIJob:
    job_id = str(uuid4())
    job = await AIJob.create(
        job_id=job_id,
        task_type=request.task_type,
        status="queued",
        request_payload=request.payload,
        model_version=request.model_version,
    )
    created_at = datetime.now(UTC).isoformat()
    message = {
        "job_id": job_id,
        "task_type": request.task_type,
        "payload": json.dumps(request.payload, ensure_ascii=False),
        "model_version": request.model_version or "",
        "attempt": "0",
        "created_at": created_at,
    }
    try:
        await redis_client.hset(
            job_cache_key(job_id),
            mapping={"status": "queued", "task_type": request.task_type, "created_at": created_at},
        )
        await redis_client.expire(job_cache_key(job_id), config.REDIS_JOB_TTL_SECONDS)
        await redis_client.xadd(config.REDIS_STREAM, message)
        await publish_job_event(job_id, {"job_id": job_id, "status": "queued", "created_at": created_at})
    except Exception as exc:
        job.status = "failed"
        job.error = "작업 큐 연결에 실패했습니다."
        job.completed_at = datetime.now(UTC)
        await job.save(update_fields=["status", "error", "completed_at", "updated_at"])
        raise RuntimeError("Redis 작업 큐에 연결할 수 없습니다.") from exc
    return job


async def get_ai_job(job_id: str) -> AIJob | None:
    return await AIJob.get_or_none(job_id=job_id)
