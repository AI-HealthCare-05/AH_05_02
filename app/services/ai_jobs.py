import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core import config
from app.core.redis import redis_client
from app.dtos.ai_jobs import AIJobCreateRequest
from app.dtos.health import PredictionJobCreateRequest
from app.models.health import Prediction
from app.models.prediction_jobs import PredictionJob
from app.models.users import User
from app.prediction.contracts import ACTIVE_MODEL
from app.prediction.providers import get_prediction_provider
from app.repositories.health_repository import HealthRepository
from app.services.health import HealthService


def job_channel(job_id: str) -> str:
    return f"ai:jobs:{job_id}:events"


def job_cache_key(job_id: str) -> str:
    return f"ai:jobs:{job_id}"


async def publish_job_event(job_id: str, event: dict[str, object]) -> None:
    await redis_client.publish(job_channel(job_id), json.dumps(event, ensure_ascii=False, default=str))


async def create_ai_job(request: AIJobCreateRequest) -> PredictionJob:
    job_id = str(uuid4())
    job = await PredictionJob.create(
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


async def get_ai_job(job_id: str) -> PredictionJob | None:
    return await PredictionJob.get_or_none(job_id=job_id)


async def create_prediction_job(user: User, request: PredictionJobCreateRequest) -> PredictionJob:
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
    job = await PredictionJob.create(
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
        input_schema_version=ACTIVE_MODEL.input_schema_version,
        preprocessing_version=ACTIVE_MODEL.preprocessing_version,
        target_definition_version=ACTIVE_MODEL.target_definition_version,
        calibration_version=ACTIVE_MODEL.calibration_version,
        model_artifact_digest=ACTIVE_MODEL.model_artifact_digest,
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
        "input_schema_version": ACTIVE_MODEL.input_schema_version,
        "preprocessing_version": ACTIVE_MODEL.preprocessing_version,
        "target_definition_version": ACTIVE_MODEL.target_definition_version,
        "calibration_version": ACTIVE_MODEL.calibration_version,
        "model_artifact_digest": ACTIVE_MODEL.model_artifact_digest or "",
        "threshold_version": ACTIVE_MODEL.threshold_version,
        "attempt": "0",
        "created_at": now.isoformat(),
    }
    if config.DEMO_MODE:
        await _complete_demo_prediction(job, features)
        return job
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


async def _complete_demo_prediction(job: PredictionJob, features: dict[str, object]) -> None:
    """Complete the formal job contract without Redis only in explicit demo mode."""
    from app.prediction.contracts import PredictionFeatures

    job.status = "running"
    job.started_at = datetime.now(UTC)
    job.worker_name = "embedded-demo-worker"
    job.attempts = 1
    await job.save(update_fields=["status", "started_at", "worker_name", "attempts", "updated_at"])
    provider = get_prediction_provider()
    result = await provider.predict(PredictionFeatures.model_validate(features))
    prediction = await Prediction.create(
        job_id=job.job_id,
        user_id=job.user_id,
        health_checkup_id=job.health_checkup_id,
        model_key=ACTIVE_MODEL.model_key,
        outcome_definition=ACTIVE_MODEL.outcome_definition,
        result_status="development_only",
        risk_category=None,
        internal_score=None,
        model_version=result.model_version,
        feature_schema_version=result.feature_schema_version,
        input_schema_version=result.input_schema_version,
        preprocessing_version=result.preprocessing_version,
        target_definition_version=result.target_definition_version,
        calibration_version=result.calibration_version,
        model_artifact_digest=result.model_artifact_digest,
        threshold_version=result.threshold_version,
        decision_threshold=None,
        class_probabilities=None,
        output_status="uncalibrated_research_probability_only",
        model_population=ACTIVE_MODEL.model_population,
        explanation_status=result.explanation_status,
        disclaimer="이 결과는 당뇨병 진단이 아닌 미래 발병 위험 선별 및 건강교육 정보입니다.",
    )
    job.status = "succeeded"
    job.prediction_id = prediction.id
    job.completed_at = datetime.now(UTC)
    job.result = {
        "promotion_status": "development_only",
        "risk_category": None,
        "internal_score": None,
        "medical_notice": "개발용 연결 결과이며 진단·처방이 아닙니다.",
    }
    await job.save(update_fields=["status", "prediction_id", "completed_at", "result", "updated_at"])


async def get_prediction_job(job_id: str, user_id: int) -> PredictionJob | None:
    job = await PredictionJob.get_or_none(job_id=job_id, user_id=user_id, task_type="diabetes_incidence")
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
