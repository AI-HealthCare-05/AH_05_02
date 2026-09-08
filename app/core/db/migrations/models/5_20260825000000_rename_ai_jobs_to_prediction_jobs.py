from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = False


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `prediction_jobs` (
            `job_id` VARCHAR(36) NOT NULL PRIMARY KEY,
            `task_type` VARCHAR(50) NOT NULL,
            `status` VARCHAR(20) NOT NULL DEFAULT 'queued',
            `request_payload` JSON NOT NULL,
            `result` JSON NULL,
            `error` TEXT NULL,
            `worker_name` VARCHAR(100) NULL,
            `attempts` INT NOT NULL DEFAULT 0,
            `model_version` VARCHAR(100) NULL,
            `model_key` VARCHAR(100) NOT NULL DEFAULT 'diabetes_incidence',
            `feature_schema_version` VARCHAR(100) NULL,
            `threshold_version` VARCHAR(100) NULL,
            `user_id` BIGINT NULL,
            `health_checkup_id` BIGINT NULL,
            `prediction_id` BIGINT NULL,
            `error_code` VARCHAR(50) NULL,
            `retryable` BOOL NOT NULL DEFAULT 0,
            `retry_after_seconds` INT NULL,
            `deadline_at` DATETIME(6) NULL,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            `started_at` DATETIME(6) NULL,
            `completed_at` DATETIME(6) NULL,
            INDEX `idx_prediction_jobs_status` (`status`)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `prediction_jobs`;
    """
