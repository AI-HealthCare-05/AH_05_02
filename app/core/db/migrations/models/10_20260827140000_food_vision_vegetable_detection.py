from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `food_analyses`
            ADD COLUMN `contains_vegetable` BOOL NULL,
            ADD COLUMN `vegetable_confidence` DOUBLE NULL,
            ADD COLUMN `vegetable_ratio_percent` DOUBLE NULL,
            ADD COLUMN `detected_items` JSON NULL,
            ADD COLUMN `user_challenge_id` BIGINT NULL,
            ADD COLUMN `verification_date` DATE NULL,
            ADD KEY `idx_food_analyses_user_challenge_id` (`user_challenge_id`);
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `food_analyses`
            DROP KEY `idx_food_analyses_user_challenge_id`,
            DROP COLUMN `contains_vegetable`,
            DROP COLUMN `vegetable_confidence`,
            DROP COLUMN `vegetable_ratio_percent`,
            DROP COLUMN `detected_items`,
            DROP COLUMN `user_challenge_id`,
            DROP COLUMN `verification_date`;
    """
