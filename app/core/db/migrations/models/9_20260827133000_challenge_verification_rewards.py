from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = False


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `challenge_verifications` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `user_id` BIGINT NOT NULL,
            `user_challenge_id` BIGINT NOT NULL,
            `verification_date` DATE NOT NULL,
            `verification_type` VARCHAR(20) NOT NULL,
            `evidence_ref` VARCHAR(500) NULL,
            `evidence_digest` VARCHAR(64) NULL,
            `location_accuracy_m` DOUBLE NULL,
            `review_status` VARCHAR(20) NOT NULL DEFAULT 'accepted',
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            KEY `idx_challenge_verifications_user_id` (`user_id`),
            KEY `idx_challenge_verifications_user_challenge_id` (`user_challenge_id`),
            KEY `idx_challenge_verifications_date` (`verification_date`),
            KEY `idx_challenge_verifications_review_status` (`review_status`),
            UNIQUE KEY `uid_challenge_verification_day` (`user_challenge_id`, `verification_date`)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

        CREATE TABLE IF NOT EXISTS `daily_challenge_rewards` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `user_id` BIGINT NOT NULL,
            `reward_date` DATE NOT NULL,
            `carrot_amount` INT NOT NULL DEFAULT 55,
            `claimed_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            KEY `idx_daily_challenge_rewards_user_id` (`user_id`),
            KEY `idx_daily_challenge_rewards_date` (`reward_date`),
            UNIQUE KEY `uid_daily_challenge_reward` (`user_id`, `reward_date`)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `daily_challenge_rewards`;
        DROP TABLE IF EXISTS `challenge_verifications`;
    """
