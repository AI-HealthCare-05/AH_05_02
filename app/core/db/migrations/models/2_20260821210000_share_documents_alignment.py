from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
ALTER TABLE `users` MODIFY COLUMN `name` VARCHAR(20) NULL;
ALTER TABLE `users` MODIFY COLUMN `phone_number` VARCHAR(11) NULL;
CREATE TABLE IF NOT EXISTS `feedbacks` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `context_type` VARCHAR(30) NOT NULL,
    `prediction_id` BIGINT,
    `recommendation_id` BIGINT,
    `rating` INT NOT NULL,
    `comment` VARCHAR(500),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY `idx_feedbacks_user_id_03a5eb` (`user_id`),
    KEY `idx_feedbacks_predict_ea3fb1` (`prediction_id`),
    KEY `idx_feedbacks_recomme_83af17` (`recommendation_id`)
) CHARACTER SET utf8mb4;
"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
DROP TABLE IF EXISTS `feedbacks`;
ALTER TABLE `users` MODIFY COLUMN `name` VARCHAR(20) NOT NULL;
ALTER TABLE `users` MODIFY COLUMN `phone_number` VARCHAR(11) NOT NULL;
"""
