import json
from datetime import datetime
from typing import Any

import asyncmy

from ai_worker.core import config

CREATE_PREDICTION_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS prediction_jobs (
    job_id VARCHAR(36) NOT NULL PRIMARY KEY,
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    request_payload JSON NOT NULL,
    result JSON NULL,
    error TEXT NULL,
    worker_name VARCHAR(100) NULL,
    attempts INT NOT NULL DEFAULT 0,
    model_version VARCHAR(100) NULL,
    model_key VARCHAR(100) NOT NULL DEFAULT 'diabetes_incidence',
    feature_schema_version VARCHAR(100) NULL,
    input_schema_version VARCHAR(100) NULL,
    preprocessing_version VARCHAR(100) NULL,
    target_definition_version VARCHAR(100) NULL,
    calibration_version VARCHAR(100) NULL,
    model_artifact_digest VARCHAR(128) NULL,
    threshold_version VARCHAR(100) NULL,
    user_id BIGINT NULL,
    health_checkup_id BIGINT NULL,
    input_as_of_date DATE NULL,
    prediction_id BIGINT NULL,
    error_code VARCHAR(50) NULL,
    retryable BOOL NOT NULL DEFAULT 0,
    retry_after_seconds INT NULL,
    deadline_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    started_at DATETIME(6) NULL,
    completed_at DATETIME(6) NULL,
    INDEX idx_prediction_jobs_status (status)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
"""

CREATE_PREDICTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS predictions (
    id BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    job_id VARCHAR(36) NOT NULL UNIQUE,
    user_id BIGINT NOT NULL,
    health_checkup_id BIGINT NOT NULL,
    input_as_of_date DATE NOT NULL,
    model_key VARCHAR(100) NOT NULL,
    outcome_definition VARCHAR(120) NOT NULL,
    result_status VARCHAR(40) NOT NULL,
    risk_category VARCHAR(20) NULL,
    internal_score DOUBLE NULL,
    model_version VARCHAR(100) NOT NULL,
    feature_schema_version VARCHAR(100) NOT NULL,
    input_schema_version VARCHAR(100) NOT NULL,
    preprocessing_version VARCHAR(100) NOT NULL,
    target_definition_version VARCHAR(100) NOT NULL,
    calibration_version VARCHAR(100) NOT NULL,
    model_artifact_digest VARCHAR(128) NULL,
    threshold_version VARCHAR(100) NOT NULL,
    decision_threshold DOUBLE NULL,
    class_probabilities JSON NULL,
    output_status VARCHAR(80) NOT NULL DEFAULT 'uncalibrated_research_probability_only',
    model_population VARCHAR(120) NOT NULL,
    explanation_status VARCHAR(40) NOT NULL DEFAULT 'not_available',
    disclaimer TEXT NOT NULL,
    predicted_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX idx_predictions_user_id (user_id),
    INDEX idx_predictions_health_checkup_id (health_checkup_id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
"""

CREATE_FOLLOW_UP_ACTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS follow_up_actions (
    id BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    trigger_source VARCHAR(30) NOT NULL,
    trigger_entity_id BIGINT NOT NULL,
    action_type VARCHAR(50) NOT NULL DEFAULT 'medical_guidance',
    reason_code VARCHAR(80) NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'high',
    safety_copy_version VARCHAR(50) NOT NULL,
    acknowledged_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX idx_follow_up_actions_user_id (user_id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
"""

PREDICTION_JOB_COLUMNS = {
    "model_key": "VARCHAR(100) NOT NULL DEFAULT 'diabetes_incidence'",
    "feature_schema_version": "VARCHAR(100) NULL",
    "input_schema_version": "VARCHAR(100) NULL",
    "preprocessing_version": "VARCHAR(100) NULL",
    "target_definition_version": "VARCHAR(100) NULL",
    "calibration_version": "VARCHAR(100) NULL",
    "model_artifact_digest": "VARCHAR(128) NULL",
    "threshold_version": "VARCHAR(100) NULL",
    "user_id": "BIGINT NULL",
    "health_checkup_id": "BIGINT NULL",
    "input_as_of_date": "DATE NULL",
    "prediction_id": "BIGINT NULL",
    "error_code": "VARCHAR(50) NULL",
    "retryable": "BOOL NOT NULL DEFAULT 0",
    "retry_after_seconds": "INT NULL",
    "deadline_at": "DATETIME(6) NULL",
}


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
            await cursor.execute(CREATE_PREDICTION_JOBS_TABLE)
            await cursor.execute(CREATE_PREDICTIONS_TABLE)
            await cursor.execute(CREATE_FOLLOW_UP_ACTIONS_TABLE)
            await cursor.execute(
                "SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='prediction_jobs'",
                (config.DB_NAME,),
            )
            existing = {row[0] for row in await cursor.fetchall()}
            for column, definition in PREDICTION_JOB_COLUMNS.items():
                if column not in existing:
                    await cursor.execute(f"ALTER TABLE prediction_jobs ADD COLUMN {column} {definition}")
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
    prediction_id: int | None = None,
    error_code: str | None = None,
    retryable: bool = False,
    retry_after_seconds: int | None = None,
) -> None:
    connection = await connect_db()
    try:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                UPDATE prediction_jobs
                SET status=%s, worker_name=%s, attempts=%s, result=%s, error=%s,
                    started_at=COALESCE(%s, started_at), completed_at=%s,
                    prediction_id=COALESCE(%s, prediction_id), error_code=%s,
                    retryable=%s, retry_after_seconds=%s
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
                    prediction_id,
                    error_code,
                    retryable,
                    retry_after_seconds,
                    job_id,
                ),
            )
    finally:
        connection.close()


async def persist_prediction(job_id: str, result: dict[str, Any]) -> int:
    connection = await connect_db()
    try:
        async with connection.cursor() as cursor:
            await cursor.execute(
                "SELECT user_id, health_checkup_id, input_as_of_date FROM prediction_jobs WHERE job_id=%s",
                (job_id,),
            )
            row = await cursor.fetchone()
            if row is None or row[0] is None or row[1] is None:
                raise RuntimeError("예측 작업의 사용자 또는 건강정보 연결값이 없습니다.")
            result_status = "approved" if result.get("promotion_status") == "approved" else "development_only"
            risk_category = result.get("risk_category") if result_status == "approved" else None
            output_status = result.get("output_status") or (
                "approved" if result_status == "approved" else "uncalibrated_research_probability_only"
            )
            model_population = result.get("model_population", config.PREDICTION_MODEL_POPULATION)
            disclaimer = result.get("medical_notice") or (
                "이 결과는 당뇨병 진단이 아닌 위험 선별 및 건강교육 정보입니다."
            )
            await cursor.execute(
                """
                INSERT INTO predictions (
                    job_id, user_id, health_checkup_id, input_as_of_date, model_key, outcome_definition,
                    result_status, risk_category, internal_score, model_version,
                    feature_schema_version, input_schema_version, preprocessing_version,
                    target_definition_version, calibration_version, model_artifact_digest,
                    threshold_version, decision_threshold, class_probabilities, output_status,
                    model_population, explanation_status, disclaimer
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    job_id,
                    row[0],
                    row[1],
                    row[2],
                    result["model_key"],
                    result["outcome_definition"],
                    result_status,
                    risk_category,
                    result.get("internal_score"),
                    result["model_version"],
                    result["feature_schema_version"],
                    result["input_schema_version"],
                    result["preprocessing_version"],
                    result["target_definition_version"],
                    result["calibration_version"],
                    result.get("model_artifact_digest"),
                    result["threshold_version"],
                    result.get("decision_threshold"),
                    None,
                    output_status,
                    model_population,
                    result.get("explanation_status", "not_available"),
                    disclaimer,
                ),
            )
            prediction_id = int(cursor.lastrowid)
            if result_status == "approved" and risk_category == "high":
                await cursor.execute(
                    """
                    INSERT INTO follow_up_actions (
                        user_id, trigger_source, trigger_entity_id, reason_code, safety_copy_version
                    ) VALUES (%s, 'prediction', %s, 'HIGH_RISK_CATEGORY', '2026-08-19-v1')
                    """,
                    (row[0], prediction_id),
                )
            return prediction_id
    finally:
        connection.close()
