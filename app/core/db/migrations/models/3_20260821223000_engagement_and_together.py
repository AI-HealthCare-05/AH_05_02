from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
CREATE TABLE IF NOT EXISTS `challenge_barriers` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `user_challenge_id` BIGINT NOT NULL,
    `log_date` DATE NOT NULL,
    `reason_code` VARCHAR(40) NOT NULL,
    `adjustment_code` VARCHAR(40),
    `note` VARCHAR(200),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY `idx_barriers_user` (`user_id`),
    KEY `idx_barriers_challenge` (`user_challenge_id`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `education_contents` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `slug` VARCHAR(80) NOT NULL UNIQUE,
    `week_number` INT NOT NULL,
    `title` VARCHAR(120) NOT NULL,
    `summary` LONGTEXT NOT NULL,
    `quiz_question` VARCHAR(300) NOT NULL,
    `quiz_answer` VARCHAR(100) NOT NULL,
    `source_title` VARCHAR(200) NOT NULL,
    `source_url` VARCHAR(500) NOT NULL,
    `is_active` BOOL NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `content_progress` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL,
    `content_id` BIGINT NOT NULL,
    `quiz_answer` VARCHAR(100) NOT NULL,
    `is_correct` BOOL NOT NULL,
    `completed_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY `uid_content_progress_user_content` (`user_id`, `content_id`),
    KEY `idx_content_progress_user` (`user_id`),
    KEY `idx_content_progress_content` (`content_id`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `invitations` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `inviter_user_id` BIGINT NOT NULL,
    `invitee_email` VARCHAR(255) NOT NULL,
    `token_hash` VARCHAR(64) NOT NULL UNIQUE,
    `relation_type` VARCHAR(20) NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'pending',
    `expires_at` DATETIME(6) NOT NULL,
    `accepted_by_user_id` BIGINT,
    `accepted_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY `idx_invitations_inviter` (`inviter_user_id`),
    KEY `idx_invitations_email` (`invitee_email`),
    KEY `idx_invitations_status` (`status`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `connections` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `user_a_id` BIGINT NOT NULL,
    `user_b_id` BIGINT NOT NULL,
    `relation_type` VARCHAR(20) NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'active',
    `sharing_scope` JSON NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `disconnected_at` DATETIME(6),
    UNIQUE KEY `uid_connections_pair` (`user_a_id`, `user_b_id`),
    KEY `idx_connections_user_a` (`user_a_id`),
    KEY `idx_connections_user_b` (`user_b_id`),
    KEY `idx_connections_status` (`status`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `shared_challenge_groups` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `owner_user_id` BIGINT NOT NULL,
    `challenge_id` BIGINT NOT NULL,
    `title` VARCHAR(100) NOT NULL,
    `common_goal` VARCHAR(150) NOT NULL,
    `start_date` DATE NOT NULL,
    `end_date` DATE NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'active',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY `idx_shared_groups_owner` (`owner_user_id`),
    KEY `idx_shared_groups_challenge` (`challenge_id`),
    KEY `idx_shared_groups_status` (`status`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `shared_challenge_members` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `group_id` BIGINT NOT NULL,
    `user_id` BIGINT NOT NULL,
    `personal_goal` VARCHAR(100) NOT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'pending',
    `joined_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `accepted_at` DATETIME(6),
    UNIQUE KEY `uid_shared_members_group_user` (`group_id`, `user_id`),
    KEY `idx_shared_members_group` (`group_id`),
    KEY `idx_shared_members_user` (`user_id`),
    KEY `idx_shared_members_status` (`status`)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `encouragements` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `group_id` BIGINT NOT NULL,
    `sender_user_id` BIGINT NOT NULL,
    `recipient_user_id` BIGINT NOT NULL,
    `template_code` VARCHAR(30) NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY `idx_encouragements_group` (`group_id`),
    KEY `idx_encouragements_sender` (`sender_user_id`),
    KEY `idx_encouragements_recipient` (`recipient_user_id`)
) CHARACTER SET utf8mb4;
"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
DROP TABLE IF EXISTS `encouragements`;
DROP TABLE IF EXISTS `shared_challenge_members`;
DROP TABLE IF EXISTS `shared_challenge_groups`;
DROP TABLE IF EXISTS `connections`;
DROP TABLE IF EXISTS `invitations`;
DROP TABLE IF EXISTS `content_progress`;
DROP TABLE IF EXISTS `education_contents`;
DROP TABLE IF EXISTS `challenge_barriers`;
"""
