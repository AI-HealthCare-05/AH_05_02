from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = False


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `challenge_verification_events` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `verification_id` BIGINT NOT NULL,
            `user_id` BIGINT NOT NULL,
            `event_type` VARCHAR(30) NOT NULL,
            `review_status` VARCHAR(20) NOT NULL,
            `evidence_digest` VARCHAR(64) NULL,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            KEY `idx_verification_events_verification_id` (`verification_id`),
            KEY `idx_verification_events_user_id` (`user_id`)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

        ALTER TABLE `health_checkups`
            MODIFY COLUMN `weight_kg` DOUBLE NOT NULL,
            MODIFY COLUMN `current_smoker` BOOL NULL,
            ADD COLUMN `smoking_status` VARCHAR(10) NULL AFTER `current_smoker`,
            ADD COLUMN `exercise_days_per_week` DOUBLE NULL AFTER `current_drinker`,
            ADD COLUMN `exercise_minutes` DOUBLE NULL AFTER `exercise_days_per_week`,
            ADD COLUMN `annual_household_income_10k_krw` DOUBLE NULL,
            ADD COLUMN `health_satisfaction_score` DOUBLE NULL,
            ADD COLUMN `economic_satisfaction_score` DOUBLE NULL,
            ADD COLUMN `overall_quality_of_life_score` DOUBLE NULL,
            ADD COLUMN `hypertension_diagnosis` BOOL NULL,
            ADD COLUMN `cancer_diagnosis` BOOL NULL,
            ADD COLUMN `chronic_lung_disease_diagnosis` BOOL NULL,
            ADD COLUMN `liver_disease_diagnosis` BOOL NULL,
            ADD COLUMN `heart_disease_diagnosis` BOOL NULL,
            ADD COLUMN `cerebrovascular_disease_diagnosis` BOOL NULL,
            ADD COLUMN `psychiatric_disease_diagnosis` BOOL NULL,
            ADD COLUMN `arthritis_rheumatism_diagnosis` BOOL NULL,
            ADD COLUMN `education_level` VARCHAR(50) NULL,
            ADD COLUMN `marital_status` VARCHAR(50) NULL,
            ADD COLUMN `household_structure` VARCHAR(50) NULL,
            ADD COLUMN `depressed_feeling_last_week` BOOL NULL,
            ADD COLUMN `sleep_difficulty_last_week` BOOL NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `health_checkups`
            DROP COLUMN `sleep_difficulty_last_week`,
            DROP COLUMN `depressed_feeling_last_week`,
            DROP COLUMN `household_structure`,
            DROP COLUMN `marital_status`,
            DROP COLUMN `education_level`,
            DROP COLUMN `arthritis_rheumatism_diagnosis`,
            DROP COLUMN `psychiatric_disease_diagnosis`,
            DROP COLUMN `cerebrovascular_disease_diagnosis`,
            DROP COLUMN `heart_disease_diagnosis`,
            DROP COLUMN `liver_disease_diagnosis`,
            DROP COLUMN `chronic_lung_disease_diagnosis`,
            DROP COLUMN `cancer_diagnosis`,
            DROP COLUMN `hypertension_diagnosis`,
            DROP COLUMN `overall_quality_of_life_score`,
            DROP COLUMN `economic_satisfaction_score`,
            DROP COLUMN `health_satisfaction_score`,
            DROP COLUMN `annual_household_income_10k_krw`,
            DROP COLUMN `exercise_minutes`,
            DROP COLUMN `exercise_days_per_week`,
            DROP COLUMN `smoking_status`;
        DROP TABLE IF EXISTS `challenge_verification_events`;
    """
