from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `predictions`
            ADD COLUMN `task_type` VARCHAR(50) NOT NULL DEFAULT 'binary_incidence_risk_screening' AFTER `model_key`,
            ADD COLUMN `threshold_scope` VARCHAR(100) NOT NULL DEFAULT 'future_incidence_2y' AFTER `threshold_version`;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `predictions`
            DROP COLUMN `threshold_scope`,
            DROP COLUMN `task_type`;
    """
