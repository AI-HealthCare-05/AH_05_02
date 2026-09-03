import json
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from app.core import config
from app.core.redis import redis_client
from app.dtos.ai_jobs import AIJobCreateRequest
from app.dtos.health import PredictionJobCreateRequest
from app.models.health import EligibilityCheck, HealthCheckup, Prediction
from app.models.model_registry import ModelRegistry
from app.models.prediction_jobs import PredictionJob
from app.models.users import User
from app.prediction.contracts import (
    ACTIVE_MODEL,
    CURRENT_SCREENING_MODEL,
    CURRENT_SCREENING_MODEL_KEY,
    LIFETIME_RISK_MODEL_KEY,
)
from app.prediction.errors import ModelNotReadyError
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


def _ensure_prediction_eligibility(
    eligibility: EligibilityCheck | None,
    *,
    model_key: str,
    age: int,
) -> None:
    if eligibility is None or eligibility.has_diabetes_diagnosis or eligibility.has_urgent_warning_sign:
        raise PermissionError("PREDICTION_NOT_ALLOWED")
    if model_key == CURRENT_SCREENING_MODEL_KEY:
        if not eligibility.service_eligible or age < CURRENT_SCREENING_MODEL.min_age:
            raise PermissionError("PREDICTION_NOT_ALLOWED")
        return
    if not eligibility.model_eligible:
        raise PermissionError("PREDICTION_NOT_ALLOWED")


async def create_prediction_job(user: User, request: PredictionJobCreateRequest) -> PredictionJob:
    repo = HealthRepository()
    checkup = await repo.get_checkup(request.checkup_id, user.id)
    if checkup is None:
        raise LookupError("건강정보 기록을 찾을 수 없습니다.")
    if await repo.active_consent(user.id) is None:
        raise PermissionError("CONSENT_REQUIRED")
    eligibility = await repo.latest_eligibility(user.id)
    _ensure_prediction_eligibility(eligibility, model_key=request.model_key, age=checkup.age)
    assert eligibility is not None

    if request.model_key == CURRENT_SCREENING_MODEL_KEY:
        return await _create_current_screening_job(user, checkup)

    if request.model_key == LIFETIME_RISK_MODEL_KEY:
        return await _create_lifetime_risk_job()

    if checkup.feature_schema_version != ACTIVE_MODEL.feature_schema_version:
        raise ValueError("FEATURE_SCHEMA_VERSION_MISMATCH")

    as_of_date = checkup.checkup_date
    inference_payload = HealthService.inference_payload(
        user,
        checkup,
        previously_diagnosed_diabetes=eligibility.has_diabetes_diagnosis,
    )
    job_id = str(uuid4())
    now = datetime.now(UTC)
    job = await PredictionJob.create(
        job_id=job_id,
        task_type="diabetes_incidence",
        status="queued",
        request_payload={
            "model_key": ACTIVE_MODEL.model_key,
            "feature_schema_version": ACTIVE_MODEL.feature_schema_version,
            "input_as_of_date": as_of_date.isoformat(),
            "health_checkup_id": checkup.id,
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
        input_as_of_date=as_of_date,
        deadline_at=now + timedelta(seconds=config.PREDICTION_TIMEOUT_SECONDS),
    )
    message = {
        "job_id": job_id,
        "task_type": "diabetes_incidence",
        "payload": json.dumps(
            {"input": inference_payload, "as_of_date": as_of_date.isoformat()},
            ensure_ascii=False,
        ),
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
        await _complete_demo_prediction(job, inference_payload, as_of_date)
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


async def _create_current_screening_job(user: User, checkup: HealthCheckup) -> PredictionJob:
    """Queue the KNHANES current-signal model independently from KLoSA incidence."""
    inference_payload = HealthService.current_screening_payload(checkup)
    job_id = str(uuid4())
    now = datetime.now(UTC)
    job = await PredictionJob.create(
        job_id=job_id,
        task_type=CURRENT_SCREENING_MODEL_KEY,
        status="queued",
        request_payload={
            "model_key": CURRENT_SCREENING_MODEL.model_key,
            "feature_schema_version": CURRENT_SCREENING_MODEL.feature_schema_version,
            "input_as_of_date": checkup.checkup_date.isoformat(),
            "health_checkup_id": checkup.id,
        },
        model_key=CURRENT_SCREENING_MODEL.model_key,
        model_version=CURRENT_SCREENING_MODEL.version,
        feature_schema_version=CURRENT_SCREENING_MODEL.feature_schema_version,
        input_schema_version=CURRENT_SCREENING_MODEL.input_schema_version,
        preprocessing_version=CURRENT_SCREENING_MODEL.preprocessing_version,
        target_definition_version=CURRENT_SCREENING_MODEL.target_definition_version,
        calibration_version=CURRENT_SCREENING_MODEL.calibration_version,
        model_artifact_digest=CURRENT_SCREENING_MODEL.model_artifact_digest,
        threshold_version=CURRENT_SCREENING_MODEL.threshold_version,
        user_id=user.id,
        health_checkup_id=checkup.id,
        input_as_of_date=checkup.checkup_date,
        deadline_at=now + timedelta(seconds=config.PREDICTION_TIMEOUT_SECONDS),
    )
    if config.DEMO_MODE:
        await _complete_demo_current_screening(job, checkup.checkup_date)
        return job
    message = {
        "job_id": job_id,
        "task_type": CURRENT_SCREENING_MODEL_KEY,
        "payload": json.dumps({"input": inference_payload}, ensure_ascii=False),
        "model_version": CURRENT_SCREENING_MODEL.version,
        "feature_schema_version": CURRENT_SCREENING_MODEL.feature_schema_version,
        "input_schema_version": CURRENT_SCREENING_MODEL.input_schema_version,
        "preprocessing_version": CURRENT_SCREENING_MODEL.preprocessing_version,
        "target_definition_version": CURRENT_SCREENING_MODEL.target_definition_version,
        "calibration_version": CURRENT_SCREENING_MODEL.calibration_version,
        "model_artifact_digest": CURRENT_SCREENING_MODEL.model_artifact_digest or "",
        "threshold_version": CURRENT_SCREENING_MODEL.threshold_version,
        "attempt": "0",
        "created_at": now.isoformat(),
    }
    try:
        await redis_client.hset(
            job_cache_key(job_id),
            mapping={"status": "queued", "task_type": CURRENT_SCREENING_MODEL_KEY, "created_at": now.isoformat()},
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


async def _create_lifetime_risk_job() -> PredictionJob:
    """API-LIFE-002 scaffold (연령별 당뇨 위험 전망 / 생존곡선).

    diabetes_incidence(RF25)와 달리 이 model_key에는 아직 학습·승인된 생존모델이
    없다 (모델 소유자: 양준혁). ModelRegistry(model_key="diabetes_lifetime_risk",
    is_active=True) row가 생기기 전까지는 항상 ModelNotReadyError를 던지는 것이
    의도된 동작이다 — 없는 모델을 있는 것처럼 잡(job)을 만들어 큐에 넣지 않기
    위한 안전장치다 (요구사항 정의서 v3.0 핵심 원칙: "위험 곡선은 승인된
    생존모델 결과가 available일 때만 공개한다").

    TODO(생존모델 승인 후): ModelRegistry row가 생기면, 이 함수를
    diabetes_incidence 경로와 동일한 패턴으로 확장한다 — inference_payload
    구성 → PredictionJob(task_type="diabetes_lifetime_risk") 생성 →
    REDIS_STREAM 큐 적재. 지금은 그 구현이 없으므로 모델이 등록되어도
    안전하게 501에 준하는 오류로 막는다.
    """
    active = await ModelRegistry.active_for(LIFETIME_RISK_MODEL_KEY)
    if active is None:
        raise ModelNotReadyError(
            "연령별 당뇨 위험 전망 모델이 아직 등록되지 않았습니다 (model_key=diabetes_lifetime_risk)."
        )
    raise ModelNotReadyError("연령별 당뇨 위험 전망 기능은 아직 준비 중입니다 (작업 큐 연동 미구현).")


async def _complete_demo_prediction(
    job: PredictionJob,
    inference_payload: dict[str, object],
    as_of_date: date,
) -> None:
    """Complete the formal job contract without Redis only in explicit demo mode."""
    job.status = "running"
    job.started_at = datetime.now(UTC)
    job.worker_name = "embedded-demo-worker"
    job.attempts = 1
    await job.save(update_fields=["status", "started_at", "worker_name", "attempts", "updated_at"])
    provider = get_prediction_provider()
    result = await provider.predict(inference_payload, as_of_date=as_of_date)
    prediction = await Prediction.create(
        job_id=job.job_id,
        user_id=job.user_id,
        health_checkup_id=job.health_checkup_id,
        input_as_of_date=as_of_date,
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


async def _complete_demo_current_screening(job: PredictionJob, as_of_date: date) -> None:
    """Complete wiring in demo mode without inventing an individual screening result."""
    job.status = "running"
    job.started_at = datetime.now(UTC)
    job.worker_name = "embedded-demo-worker"
    job.attempts = 1
    await job.save(update_fields=["status", "started_at", "worker_name", "attempts", "updated_at"])
    prediction = await Prediction.create(
        job_id=job.job_id,
        user_id=job.user_id,
        health_checkup_id=job.health_checkup_id,
        input_as_of_date=as_of_date,
        model_key=CURRENT_SCREENING_MODEL.model_key,
        outcome_definition=CURRENT_SCREENING_MODEL.outcome_definition,
        result_status="development_only",
        risk_category=None,
        internal_score=None,
        model_version=CURRENT_SCREENING_MODEL.version,
        feature_schema_version=CURRENT_SCREENING_MODEL.feature_schema_version,
        input_schema_version=CURRENT_SCREENING_MODEL.input_schema_version,
        preprocessing_version=CURRENT_SCREENING_MODEL.preprocessing_version,
        target_definition_version=CURRENT_SCREENING_MODEL.target_definition_version,
        calibration_version=CURRENT_SCREENING_MODEL.calibration_version,
        model_artifact_digest=CURRENT_SCREENING_MODEL.model_artifact_digest,
        threshold_version=CURRENT_SCREENING_MODEL.threshold_version,
        decision_threshold=None,
        class_probabilities=None,
        output_status="screening_model_wiring_only",
        model_population=CURRENT_SCREENING_MODEL.model_population,
        explanation_status="not_available",
        disclaimer="현재 당뇨 관련 위험 신호를 선별하는 건강교육용 흐름이며 진단이 아닙니다.",
    )
    job.status = "succeeded"
    job.prediction_id = prediction.id
    job.completed_at = datetime.now(UTC)
    job.result = {
        "promotion_status": "development_only",
        "screening_signal_detected": None,
        "medical_notice": "개발용 연결 결과이며 개인 위험 신호는 표시하지 않습니다.",
    }
    await job.save(update_fields=["status", "prediction_id", "completed_at", "result", "updated_at"])


async def get_prediction_job(job_id: str, user_id: int) -> PredictionJob | None:
    job = await PredictionJob.get_or_none(job_id=job_id, user_id=user_id)
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
