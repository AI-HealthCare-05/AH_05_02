from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = False


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `predictions`
            ADD COLUMN `risk_curve_status` VARCHAR(20) NOT NULL DEFAULT 'not_applicable' AFTER `disclaimer`,
            ADD COLUMN `output_definition_version` VARCHAR(100) NULL AFTER `risk_curve_status`;

        CREATE TABLE IF NOT EXISTS `model_registry` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `model_key` VARCHAR(100) NOT NULL,
            `model_version` VARCHAR(100) NOT NULL,
            `model_type` VARCHAR(40) NOT NULL DEFAULT 'binary_classifier',
            `promotion_status` VARCHAR(40) NOT NULL DEFAULT 'candidate_only',
            `artifact_local_path` VARCHAR(255) NULL,
            `artifact_sha256` VARCHAR(128) NULL,
            `feature_schema_version` VARCHAR(100) NOT NULL,
            `target_definition_version` VARCHAR(100) NULL,
            `calibration_version` VARCHAR(100) NULL,
            `threshold_version` VARCHAR(100) NULL,
            `min_age` INT NOT NULL,
            `max_age` INT NULL,
            `model_population` VARCHAR(120) NOT NULL,
            `outcome_definition` VARCHAR(200) NULL,
            `is_active` BOOL NOT NULL DEFAULT 0,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            UNIQUE KEY `uq_model_registry_key_version` (`model_key`, `model_version`),
            KEY `idx_model_registry_key_active` (`model_key`, `is_active`)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

        CREATE TABLE IF NOT EXISTS `prediction_risk_curve_points` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `prediction_id` BIGINT NOT NULL,
            `age` INT NOT NULL,
            `cumulative_risk` DOUBLE NOT NULL,
            `lower` DOUBLE NOT NULL,
            `upper` DOUBLE NOT NULL,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            UNIQUE KEY `uq_risk_curve_prediction_age` (`prediction_id`, `age`)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

        CREATE TABLE IF NOT EXISTS `prediction_scenarios` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `prediction_id` BIGINT NOT NULL,
            `scenario` VARCHAR(30) NOT NULL,
            `scenario_definition_version` VARCHAR(100) NOT NULL,
            `is_active` BOOL NOT NULL DEFAULT 0,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            KEY `idx_prediction_scenarios_prediction_id` (`prediction_id`)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `prediction_scenarios`;
        DROP TABLE IF EXISTS `prediction_risk_curve_points`;
        DROP TABLE IF EXISTS `model_registry`;
        ALTER TABLE `predictions`
            DROP COLUMN IF EXISTS `output_definition_version`,
            DROP COLUMN IF EXISTS `risk_curve_status`;
    """
