from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = False


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `predictions`
            ADD COLUMN `age_risk_forecast` JSON NULL AFTER `output_definition_version`;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `predictions`
            DROP COLUMN IF EXISTS `age_risk_forecast`;
    """
