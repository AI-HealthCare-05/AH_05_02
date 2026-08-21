import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core import config
from app.core.redis import redis_client
from app.dtos.ai_jobs import AIJobCreateRequest
from app.dtos.health import PredictionJobCreateRequest
from app.models.ai_jobs import AIJob
from app.models.users import User
from app.prediction.contracts import ACTIVE_MODEL
from app.repositories.health_repository import HealthRepository
from app.services.health import HealthService


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


async def create_prediction_job(user: User, request: PredictionJobCreateRequest) -> AIJob:
    repo = HealthRepository()
    checkup = await repo.get_checkup(request.checkup_id, user.id)
    if checkup is None:
        raise LookupError("건강정보 기록을 찾을 수 없습니다.")
    if await repo.active_consent(user.id) is None:
        raise PermissionError("CONSENT_REQUIRED")
    eligibility = await repo.latest_eligibility(user.id)
    if eligibility is None or not eligibility.model_eligible:
        raise PermissionError("PREDICTION_NOT_ALLOWED")
    if checkup.feature_schema_version != ACTIVE_MODEL.feature_schema_version:
        raise ValueError("FEATURE_SCHEMA_VERSION_MISMATCH")

    features = HealthService.features_for(checkup).as_model_record()
    job_id = str(uuid4())
    now = datetime.now(UTC)
    job = await AIJob.create(
        job_id=job_id,
        task_type="diabetes_incidence",
        status="queued",
        request_payload={
            "model_key": ACTIVE_MODEL.model_key,
            "feature_schema_version": ACTIVE_MODEL.feature_schema_version,
            "feature_names": list(features),
        },
        model_key=ACTIVE_MODEL.model_key,
        model_version=ACTIVE_MODEL.version,
        feature_schema_version=ACTIVE_MODEL.feature_schema_version,
        threshold_version=ACTIVE_MODEL.threshold_version,
        user_id=user.id,
        health_checkup_id=checkup.id,
        deadline_at=now + timedelta(seconds=config.PREDICTION_TIMEOUT_SECONDS),
    )
    message = {
        "job_id": job_id,
        "task_type": "diabetes_incidence",
        "payload": json.dumps({"features": features}, ensure_ascii=False),
        "model_version": ACTIVE_MODEL.version,
        "feature_schema_version": ACTIVE_MODEL.feature_schema_version,
        "threshold_version": ACTIVE_MODEL.threshold_version,
        "attempt": "0",
        "created_at": now.isoformat(),
    }
    try:
        await redis_client.hset(
            job_cache_key(job_id),
            mapping={"status": "queued", "task_type": "diabetes_incidence", "created_at": now.isoformat()},
        )
        await redis_client.expire(job_cache_key(job_id), config.REDIS_JOB_TTL_SECONDS)
        await redis_client.xadd(config.REDIS_STREAM, message)
        await publish_job_event(job_id, {"job_id": job_id, "status": "queued", "created_at": now.isoformat()})
    except Exception as exc:
        job.status = "failed"
        job.error = "작업 큐 연결에 실패했습니다."
        job.error_code = "QUEUE_UNAVAILABLE"
        job.completed_at = datetime.now(UTC)
        await job.save(update_fields=["status", "error", "error_code", "completed_at", "updated_at"])
        raise RuntimeError("Redis 작업 큐에 연결할 수 없습니다.") from exc
    return job


async def get_prediction_job(job_id: str, user_id: int) -> AIJob | None:
    job = await AIJob.get_or_none(job_id=job_id, user_id=user_id, task_type="diabetes_incidence")
    if job is None:
        return None
    now = datetime.now(UTC)
    deadline = job.deadline_at
    if deadline is not None and deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    if job.status in {"queued", "running"} and deadline is not None and now > deadline:
        job.status = "failed"
        job.error = "예측 작업 제한 시간을 초과했습니다."
        job.error_code = "TIMEOUT"
        job.retryable = True
        job.retry_after_seconds = 30
        job.completed_at = now
        await job.save(
            update_fields=[
                "status",
                "error",
                "error_code",
                "retryable",
                "retry_after_seconds",
                "completed_at",
                "updated_at",
            ]
        )
    return job
