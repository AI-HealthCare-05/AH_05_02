from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = False


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users`
            MODIFY COLUMN `gender` VARCHAR(6) NULL,
            MODIFY COLUMN `birthday` DATE NULL,
            MODIFY COLUMN `phone_number` VARCHAR(11) NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users`
            MODIFY COLUMN `gender` VARCHAR(6) NOT NULL,
            MODIFY COLUMN `birthday` DATE NOT NULL,
            MODIFY COLUMN `phone_number` VARCHAR(11) NOT NULL;
    """
