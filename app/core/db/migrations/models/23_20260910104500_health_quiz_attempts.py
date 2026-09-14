from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `health_quiz_attempts` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `user_id` BIGINT NOT NULL,
            `quiz_id` VARCHAR(120) NOT NULL,
            `document_id` VARCHAR(120) NOT NULL,
            `submitted_answer` VARCHAR(100) NOT NULL,
            `is_correct` BOOL NOT NULL,
            `attempted_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            KEY `idx_quiz_attempt_user` (`user_id`),
            KEY `idx_quiz_attempt_quiz` (`quiz_id`),
            KEY `idx_quiz_attempt_document` (`document_id`)
        ) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return "DROP TABLE IF EXISTS `health_quiz_attempts`;"
