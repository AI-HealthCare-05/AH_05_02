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
