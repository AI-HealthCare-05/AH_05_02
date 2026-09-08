from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `health_checkups`
            MODIFY COLUMN `self_rated_health` VARCHAR(20) NULL,
            MODIFY COLUMN `meal_count_yesterday` INT NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `health_checkups`
            MODIFY COLUMN `self_rated_health` VARCHAR(20) NOT NULL,
            MODIFY COLUMN `meal_count_yesterday` INT NOT NULL;
    """
