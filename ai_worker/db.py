import json
from datetime import datetime
from typing import Any

import asyncmy

from ai_worker.core import config

CREATE_AI_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS ai_jobs (
    job_id VARCHAR(36) NOT NULL PRIMARY KEY,
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    request_payload JSON NOT NULL,
    result JSON NULL,
    error TEXT NULL,
    worker_name VARCHAR(100) NULL,
    attempts INT NOT NULL DEFAULT 0,
    model_version VARCHAR(100) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    started_at DATETIME(6) NULL,
    completed_at DATETIME(6) NULL,
    INDEX idx_ai_jobs_status (status)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
"""


async def connect_db() -> asyncmy.Connection:
    return await asyncmy.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        autocommit=True,
    )


async def ensure_schema() -> None:
    connection = await connect_db()
    try:
        async with connection.cursor() as cursor:
            await cursor.execute(CREATE_AI_JOBS_TABLE)
    finally:
        connection.close()


async def update_job(
    job_id: str,
    *,
    status: str,
    worker_name: str,
    attempts: int,
    result: dict[str, Any] | None = None,
    error: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> None:
    connection = await connect_db()
    try:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                UPDATE ai_jobs
                SET status=%s, worker_name=%s, attempts=%s, result=%s, error=%s,
                    started_at=COALESCE(%s, started_at), completed_at=%s
                WHERE job_id=%s
                """,
                (
                    status,
                    worker_name,
                    attempts,
                    json.dumps(result, ensure_ascii=False) if result is not None else None,
                    error,
                    started_at,
                    completed_at,
                    job_id,
                ),
            )
    finally:
        connection.close()
