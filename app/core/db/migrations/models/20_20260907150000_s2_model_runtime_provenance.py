from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = False


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `prediction_jobs`
            ADD COLUMN `threshold_scope` VARCHAR(100) NULL AFTER `threshold_version`;
        ALTER TABLE `predictions`
            ADD COLUMN `display_allowed` BOOL NOT NULL DEFAULT 0 AFTER `threshold_scope`,
            ADD COLUMN `operational_model_activated` BOOL NOT NULL DEFAULT 0 AFTER `display_allowed`,
            ADD COLUMN `preview_only` BOOL NOT NULL DEFAULT 0 AFTER `operational_model_activated`,
            ADD COLUMN `preview_signal_level` VARCHAR(20) NULL AFTER `preview_only`;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `predictions`
            DROP COLUMN `preview_signal_level`,
            DROP COLUMN `preview_only`,
            DROP COLUMN `operational_model_activated`,
            DROP COLUMN `display_allowed`;
        ALTER TABLE `prediction_jobs` DROP COLUMN `threshold_scope`;
    """
