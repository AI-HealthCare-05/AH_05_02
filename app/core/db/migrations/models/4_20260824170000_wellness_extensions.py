from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `wearable_connections` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `user_id` BIGINT NOT NULL,
            `provider` VARCHAR(40) NOT NULL,
            `status` VARCHAR(20) NOT NULL DEFAULT 'active',
            `scopes` JSON NOT NULL,
            `connected_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `disconnected_at` DATETIME(6) NULL,
            UNIQUE KEY `uid_wearable_user_prv` (`user_id`, `provider`),
            KEY `idx_wearable_user` (`user_id`), KEY `idx_wearable_status` (`status`)
        );
        CREATE TABLE IF NOT EXISTS `wearable_daily_summaries` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `user_id` BIGINT NOT NULL, `connection_id` BIGINT NOT NULL, `summary_date` DATE NOT NULL,
            `steps` INT NULL, `active_minutes` INT NULL, `sleep_minutes` INT NULL,
            `resting_heart_rate` INT NULL, `source` VARCHAR(40) NOT NULL,
            `quality` VARCHAR(20) NOT NULL DEFAULT 'user_confirmed',
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            UNIQUE KEY `uid_wearable_summary` (`user_id`, `connection_id`, `summary_date`),
            KEY `idx_wsummary_user` (`user_id`), KEY `idx_wsummary_connection` (`connection_id`)
        );
        CREATE TABLE IF NOT EXISTS `food_analyses` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT, `user_id` BIGINT NOT NULL,
            `image_name` VARCHAR(200) NOT NULL, `provider` VARCHAR(40) NOT NULL DEFAULT 'development_mock',
            `predicted_category` VARCHAR(50) NOT NULL, `confidence` DOUBLE NULL,
            `confirmed_category` VARCHAR(50) NULL, `status` VARCHAR(30) NOT NULL DEFAULT 'needs_confirmation',
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6), `confirmed_at` DATETIME(6) NULL,
            KEY `idx_food_user` (`user_id`)
        );
        CREATE TABLE IF NOT EXISTS `ocr_drafts` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT, `user_id` BIGINT NOT NULL,
            `document_name` VARCHAR(200) NOT NULL, `provider` VARCHAR(40) NOT NULL DEFAULT 'development_mock',
            `extracted_fields` JSON NOT NULL, `status` VARCHAR(30) NOT NULL DEFAULT 'needs_confirmation',
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6), `confirmed_at` DATETIME(6) NULL,
            KEY `idx_ocr_user` (`user_id`)
        );
        CREATE TABLE IF NOT EXISTS `notification_preferences` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT, `user_id` BIGINT NOT NULL UNIQUE,
            `in_app_enabled` BOOL NOT NULL DEFAULT 1, `challenge_reminder_enabled` BOOL NOT NULL DEFAULT 1,
            `weekly_report_enabled` BOOL NOT NULL DEFAULT 1, `quiet_start_hour` INT NOT NULL DEFAULT 21,
            `quiet_end_hour` INT NOT NULL DEFAULT 8,
            `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
        );
        CREATE TABLE IF NOT EXISTS `in_app_notifications` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT, `user_id` BIGINT NOT NULL,
            `notification_type` VARCHAR(40) NOT NULL, `title` VARCHAR(100) NOT NULL,
            `message` VARCHAR(300) NOT NULL, `is_read` BOOL NOT NULL DEFAULT 0,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6), `read_at` DATETIME(6) NULL,
            KEY `idx_notification_user` (`user_id`)
        );
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `in_app_notifications`;
        DROP TABLE IF EXISTS `notification_preferences`;
        DROP TABLE IF EXISTS `ocr_drafts`;
        DROP TABLE IF EXISTS `food_analyses`;
        DROP TABLE IF EXISTS `wearable_daily_summaries`;
        DROP TABLE IF EXISTS `wearable_connections`;
    """
