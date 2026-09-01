from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AIJobCreateRequest(BaseModel):
    task_type: Literal["demo_inference", "model_inference"] = "demo_inference"
    payload: dict[str, Any] = Field(default_factory=dict)
    model_version: str | None = Field(default=None, max_length=100)


class AIJobResponse(BaseModel):
    job_id: str
    task_type: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    worker_name: str | None = None
    attempts: int
    model_version: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class PredictionJobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    model_key: str
    model_version: str | None = None
    feature_schema_version: str | None = None
    input_schema_version: str | None = None
    preprocessing_version: str | None = None
    target_definition_version: str | None = None
    calibration_version: str | None = None
    model_artifact_digest: str | None = None
    threshold_version: str | None = None
    prediction_id: int | None = None
    error_code: str | None = None
    retryable: bool = False
    retry_after_seconds: int | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


def prediction_job_response(job: object) -> PredictionJobResponse:
    return PredictionJobResponse(
        job_id=job.job_id,
        status=job.status,
        model_key=job.model_key,
        model_version=job.model_version,
        feature_schema_version=job.feature_schema_version,
        input_schema_version=job.input_schema_version,
        preprocessing_version=job.preprocessing_version,
        target_definition_version=job.target_definition_version,
        calibration_version=job.calibration_version,
        model_artifact_digest=job.model_artifact_digest,
        threshold_version=job.threshold_version,
        prediction_id=job.prediction_id,
        error_code=job.error_code,
        retryable=job.retryable,
        retry_after_seconds=job.retry_after_seconds,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.completed_at,
    )
