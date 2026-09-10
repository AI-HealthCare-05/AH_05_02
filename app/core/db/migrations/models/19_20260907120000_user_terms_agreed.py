from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = False


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users`
            ADD COLUMN `terms_agreed` BOOL NOT NULL DEFAULT 0,
            ADD COLUMN `terms_agreed_at` DATETIME(6) NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users`
            DROP COLUMN `terms_agreed`,
            DROP COLUMN `terms_agreed_at`;
    """
