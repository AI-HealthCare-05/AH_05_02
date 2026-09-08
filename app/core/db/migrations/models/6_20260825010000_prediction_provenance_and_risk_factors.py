from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = False


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `prediction_jobs` ADD COLUMN `input_schema_version` VARCHAR(100) NULL;
        ALTER TABLE `prediction_jobs` ADD COLUMN `preprocessing_version` VARCHAR(100) NULL;
        ALTER TABLE `prediction_jobs` ADD COLUMN `target_definition_version` VARCHAR(100) NULL;
        ALTER TABLE `prediction_jobs` ADD COLUMN `calibration_version` VARCHAR(100) NULL;
        ALTER TABLE `prediction_jobs` ADD COLUMN `model_artifact_digest` VARCHAR(128) NULL;

        ALTER TABLE `predictions` ADD COLUMN `input_schema_version` VARCHAR(100) NOT NULL DEFAULT 'unrecorded';
        ALTER TABLE `predictions` ADD COLUMN `preprocessing_version` VARCHAR(100) NOT NULL DEFAULT 'unrecorded';
        ALTER TABLE `predictions` ADD COLUMN `target_definition_version` VARCHAR(100) NOT NULL DEFAULT 'unrecorded';
        ALTER TABLE `predictions` ADD COLUMN `calibration_version` VARCHAR(100) NOT NULL DEFAULT 'unrecorded';
        ALTER TABLE `predictions` ADD COLUMN `model_artifact_digest` VARCHAR(128) NULL;
        ALTER TABLE `predictions` ADD COLUMN `class_probabilities` JSON NULL;
        ALTER TABLE `predictions` ADD COLUMN `output_status` VARCHAR(80) NOT NULL DEFAULT 'uncalibrated_research_probability_only';
        ALTER TABLE `predictions` ADD COLUMN `decision_threshold` DOUBLE NULL;

        CREATE TABLE IF NOT EXISTS `risk_factors` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `prediction_id` BIGINT NOT NULL,
            `factor_name` VARCHAR(100) NOT NULL,
            `display_name` VARCHAR(100) NOT NULL,
            `impact_direction` VARCHAR(20) NOT NULL,
            `importance_score` DOUBLE NOT NULL,
            `display_order` INT NOT NULL,
            `is_modifiable` BOOL NOT NULL DEFAULT 0,
            `message` LONGTEXT NOT NULL,
            `explanation_version` VARCHAR(100) NOT NULL,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            KEY `idx_risk_factors_prediction_id` (`prediction_id`)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `risk_factors`;
        ALTER TABLE `predictions` DROP COLUMN IF EXISTS `decision_threshold`;
        ALTER TABLE `predictions` DROP COLUMN IF EXISTS `output_status`;
        ALTER TABLE `predictions` DROP COLUMN IF EXISTS `class_probabilities`;
        ALTER TABLE `predictions` DROP COLUMN IF EXISTS `model_artifact_digest`;
        ALTER TABLE `predictions` DROP COLUMN IF EXISTS `calibration_version`;
        ALTER TABLE `predictions` DROP COLUMN IF EXISTS `target_definition_version`;
        ALTER TABLE `predictions` DROP COLUMN IF EXISTS `preprocessing_version`;
        ALTER TABLE `predictions` DROP COLUMN IF EXISTS `input_schema_version`;
        ALTER TABLE `prediction_jobs` DROP COLUMN IF EXISTS `model_artifact_digest`;
        ALTER TABLE `prediction_jobs` DROP COLUMN IF EXISTS `calibration_version`;
        ALTER TABLE `prediction_jobs` DROP COLUMN IF EXISTS `target_definition_version`;
        ALTER TABLE `prediction_jobs` DROP COLUMN IF EXISTS `preprocessing_version`;
        ALTER TABLE `prediction_jobs` DROP COLUMN IF EXISTS `input_schema_version`;
    """
