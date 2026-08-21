from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
CREATE TABLE IF NOT EXISTS `challenges` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `code` VARCHAR(50) NOT NULL UNIQUE,
    `title` VARCHAR(100) NOT NULL,
    `category` VARCHAR(30) NOT NULL,
    `daily_goal` VARCHAR(50) NOT NULL,
    `description` LONGTEXT NOT NULL,
    `safety_copy` LONGTEXT NOT NULL,
    `source_title` VARCHAR(200) NOT NULL,
    `source_url` VARCHAR(500) NOT NULL,
    `is_active` BOOL NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `challenge_cycles` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `prediction_id` BIGINT,
    `cycle_number` INT NOT NULL,
    `start_date` DATE NOT NULL,
    `end_date` DATE NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'active',
    `ended_reason` VARCHAR(80),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    KEY `idx_challenge_c_user_id_18f46d` (`user_id`),
    KEY `idx_challenge_c_predict_7a6e37` (`prediction_id`),
    KEY `idx_challenge_c_status_e63001` (`status`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `challenge_logs` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `user_challenge_id` BIGINT NOT NULL,
    `log_date` DATE NOT NULL,
    `is_completed` BOOL NOT NULL,
    `value` DOUBLE,
    `source` VARCHAR(30) NOT NULL DEFAULT 'self_report',
    `note` VARCHAR(200),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY `uid_challenge_l_user_ch_739c98` (`user_challenge_id`, `log_date`),
    KEY `idx_challenge_l_user_id_269ef3` (`user_id`),
    KEY `idx_challenge_l_user_ch_0c6766` (`user_challenge_id`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `consents` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `consent_item` VARCHAR(50) NOT NULL DEFAULT 'health_data',
    `version` VARCHAR(30) NOT NULL,
    `is_agreed` BOOL NOT NULL DEFAULT 1,
    `agreed_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `withdrawn_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    KEY `idx_consents_user_id_c3b500` (`user_id`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `eligibility_checks` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `age` INT NOT NULL,
    `has_diabetes_diagnosis` BOOL NOT NULL DEFAULT 0,
    `has_urgent_warning_sign` BOOL NOT NULL DEFAULT 0,
    `population_in_scope` BOOL NOT NULL DEFAULT 1,
    `service_eligible` BOOL NOT NULL,
    `target_segment` VARCHAR(50) NOT NULL,
    `model_eligible` BOOL NOT NULL,
    `reason_codes` JSON NOT NULL,
    `next_action` VARCHAR(80) NOT NULL,
    `model_key` VARCHAR(100) NOT NULL,
    `model_version` VARCHAR(100) NOT NULL,
    `feature_schema_version` VARCHAR(100) NOT NULL,
    `threshold_version` VARCHAR(100) NOT NULL,
    `safety_copy_version` VARCHAR(50) NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY `idx_eligibility_user_id_fba453` (`user_id`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `follow_up_actions` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `trigger_source` VARCHAR(30) NOT NULL,
    `trigger_entity_id` BIGINT NOT NULL,
    `action_type` VARCHAR(50) NOT NULL DEFAULT 'medical_guidance',
    `reason_code` VARCHAR(80) NOT NULL,
    `priority` VARCHAR(20) NOT NULL DEFAULT 'high',
    `safety_copy_version` VARCHAR(50) NOT NULL,
    `acknowledged_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY `idx_follow_up_a_user_id_2bc511` (`user_id`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `health_checkups` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `eligibility_check_id` BIGINT NOT NULL,
    `checkup_type` VARCHAR(20) NOT NULL DEFAULT 'initial',
    `checkup_date` DATE NOT NULL,
    `age` INT NOT NULL,
    `sex` VARCHAR(10) NOT NULL,
    `height_cm` DOUBLE NOT NULL,
    `weight_kg` DOUBLE NOT NULL,
    `bmi` DOUBLE NOT NULL,
    `waist_cm` DOUBLE,
    `systolic_bp` INT,
    `diastolic_bp` INT,
    `self_rated_health` VARCHAR(20) NOT NULL,
    `meal_count_yesterday` INT NOT NULL,
    `regular_exercise` BOOL NOT NULL,
    `current_smoker` BOOL NOT NULL,
    `current_drinker` BOOL NOT NULL,
    `feature_schema_version` VARCHAR(100) NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    KEY `idx_health_chec_user_id_bc656b` (`user_id`),
    KEY `idx_health_chec_eligibi_a58e14` (`eligibility_check_id`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `predictions` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `job_id` VARCHAR(36) NOT NULL UNIQUE,
    `user_id` BIGINT NOT NULL,
    `health_checkup_id` BIGINT NOT NULL,
    `model_key` VARCHAR(100) NOT NULL,
    `outcome_definition` VARCHAR(120) NOT NULL,
    `result_status` VARCHAR(40) NOT NULL,
    `risk_category` VARCHAR(20),
    `internal_score` DOUBLE,
    `model_version` VARCHAR(100) NOT NULL,
    `feature_schema_version` VARCHAR(100) NOT NULL,
    `threshold_version` VARCHAR(100) NOT NULL,
    `model_population` VARCHAR(120) NOT NULL,
    `explanation_status` VARCHAR(40) NOT NULL DEFAULT 'not_available',
    `disclaimer` LONGTEXT NOT NULL,
    `predicted_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY `idx_predictions_user_id_a35821` (`user_id`),
    KEY `idx_predictions_health__9e8baa` (`health_checkup_id`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `user_challenges` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `cycle_id` BIGINT NOT NULL,
    `challenge_id` BIGINT NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY `idx_user_challe_user_id_f4ea60` (`user_id`),
    KEY `idx_user_challe_cycle_i_f7c158` (`cycle_id`),
    KEY `idx_user_challe_challen_3e63d3` (`challenge_id`)
) CHARACTER SET utf8mb4;
"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
DROP TABLE IF EXISTS `challenge_logs`;
DROP TABLE IF EXISTS `user_challenges`;
DROP TABLE IF EXISTS `challenge_cycles`;
DROP TABLE IF EXISTS `challenges`;
DROP TABLE IF EXISTS `follow_up_actions`;
DROP TABLE IF EXISTS `predictions`;
DROP TABLE IF EXISTS `health_checkups`;
DROP TABLE IF EXISTS `eligibility_checks`;
DROP TABLE IF EXISTS `consents`;
"""
