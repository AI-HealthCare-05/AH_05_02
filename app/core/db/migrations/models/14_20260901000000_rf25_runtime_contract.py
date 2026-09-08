from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = False


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `health_checkups`
            MODIFY COLUMN `depressed_feeling_last_week` VARCHAR(20) NULL,
            MODIFY COLUMN `sleep_difficulty_last_week` VARCHAR(20) NULL;

        ALTER TABLE `prediction_jobs`
            ADD COLUMN `input_as_of_date` DATE NULL AFTER `health_checkup_id`;

        ALTER TABLE `predictions`
            ADD COLUMN `input_as_of_date` DATE NULL AFTER `health_checkup_id`;

        UPDATE `predictions` p
        JOIN `health_checkups` h ON h.id = p.health_checkup_id
        SET p.input_as_of_date = h.checkup_date
        WHERE p.input_as_of_date IS NULL;

        ALTER TABLE `predictions`
            MODIFY COLUMN `input_as_of_date` DATE NOT NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `predictions` DROP COLUMN `input_as_of_date`;
        ALTER TABLE `prediction_jobs` DROP COLUMN `input_as_of_date`;
        ALTER TABLE `health_checkups`
            MODIFY COLUMN `depressed_feeling_last_week` BOOL NULL,
            MODIFY COLUMN `sleep_difficulty_last_week` BOOL NULL;
    """
