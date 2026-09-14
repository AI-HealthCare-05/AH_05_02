from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    CREATE TABLE `challenge_v2_enrollments` (
      `id` BIGINT PRIMARY KEY AUTO_INCREMENT, `user_id` BIGINT NOT NULL UNIQUE,
      `mode` VARCHAR(20) NOT NULL, `starts_on` DATE NOT NULL, `preferences` JSON NOT NULL,
      `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6));
    CREATE TABLE `challenge_v2_days` (
      `id` BIGINT PRIMARY KEY AUTO_INCREMENT, `user_id` BIGINT NOT NULL,
      `assigned_date` DATE NOT NULL, `cycle_id` BIGINT NULL, `policy_version` VARCHAR(30) NOT NULL DEFAULT '2.1',
      `eligibility_snapshot` JSON NOT NULL, `exception_reasons` JSON NOT NULL,
      `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
      UNIQUE KEY `v2_user_date` (`user_id`, `assigned_date`));
    CREATE TABLE `challenge_v2_assignments` (
      `id` BIGINT PRIMARY KEY AUTO_INCREMENT, `day_id` BIGINT NOT NULL, `slot` INT NOT NULL,
      `revision` INT NOT NULL DEFAULT 1, `replacement_reason` VARCHAR(30) NULL, `goal` JSON NOT NULL,
      `status` VARCHAR(20) NOT NULL DEFAULT 'assigned', `verification_status` VARCHAR(20) NOT NULL DEFAULT 'not_required',
      UNIQUE KEY `v2_day_slot_revision` (`day_id`, `slot`, `revision`));
    CREATE TABLE `challenge_v2_sessions` (
      `id` BIGINT PRIMARY KEY AUTO_INCREMENT, `assignment_id` BIGINT NOT NULL, `session_index` INT NOT NULL,
      `performed_at` DATETIME(6) NOT NULL, `values` JSON NOT NULL,
      `recorded_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
      UNIQUE KEY `v2_session` (`assignment_id`, `session_index`));
    CREATE TABLE `challenge_v2_evidence` (
      `id` BIGINT PRIMARY KEY AUTO_INCREMENT, `user_id` BIGINT NOT NULL, `day_id` BIGINT NOT NULL,
      `assignment_id` BIGINT NOT NULL, `evidence_index` INT NOT NULL, `content_hash` VARCHAR(64) NOT NULL,
      `mime` VARCHAR(30) NOT NULL DEFAULT 'image/jpeg', `content` LONGBLOB NULL,
      `submitted_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6), `deletion_due_at` DATETIME(6) NOT NULL,
      `verification_status` VARCHAR(20) NOT NULL DEFAULT 'not_required', `generation` INT NOT NULL DEFAULT 1,
      UNIQUE KEY `v2_day_hash` (`day_id`, `content_hash`), UNIQUE KEY `v2_evidence_slot` (`assignment_id`, `evidence_index`),
      KEY `v2_evidence_owner` (`user_id`), KEY `v2_evidence_expiry` (`deletion_due_at`));
    CREATE TABLE `challenge_v2_reviews` (
      `id` BIGINT PRIMARY KEY AUTO_INCREMENT, `evidence_id` BIGINT NOT NULL, `evidence_generation` INT NOT NULL,
      `reviewer_id` BIGINT NOT NULL, `status` VARCHAR(20) NOT NULL, `criteria_results` JSON NOT NULL,
      `reason` VARCHAR(500) NOT NULL, `reviewed_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
      UNIQUE KEY `v2_review_generation` (`evidence_id`, `evidence_generation`));
    CREATE TABLE `challenge_v2_rewards` (
      `id` BIGINT PRIMARY KEY AUTO_INCREMENT, `user_id` BIGINT NOT NULL, `day_id` BIGINT NOT NULL,
      `source_key` VARCHAR(100) NOT NULL UNIQUE, `carrot_amount` INT NOT NULL, `item_code` VARCHAR(40) NULL,
      `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6), KEY `v2_reward_day` (`day_id`),
      KEY `v2_reward_owner` (`user_id`));
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    raise RuntimeError("V2 history and earned rewards require a reviewed, non-destructive rollback plan.")
