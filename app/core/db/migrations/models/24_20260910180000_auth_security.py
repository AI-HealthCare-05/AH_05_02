from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` ADD `auth_version` INT NOT NULL DEFAULT 0;
        CREATE TABLE IF NOT EXISTS `auth_throttles` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `scope` VARCHAR(30) NOT NULL,
            `key_hash` VARCHAR(64) NOT NULL,
            `failure_count` INT NOT NULL DEFAULT 0,
            `lock_level` INT NOT NULL DEFAULT 0,
            `locked_until` DATETIME(6) NULL,
            `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            UNIQUE KEY `uid_auth_throttle_scope_key` (`scope`, `key_hash`)
        ) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `password_reset_tokens` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `token_hash` VARCHAR(64) NOT NULL UNIQUE,
            `expires_at` DATETIME(6) NOT NULL,
            `used_at` DATETIME(6) NULL,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `user_id` BIGINT NOT NULL,
            KEY `idx_password_reset_user` (`user_id`),
            CONSTRAINT `fk_password_reset_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
        ) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `password_reset_tokens`;
        DROP TABLE IF EXISTS `auth_throttles`;
        ALTER TABLE `users` DROP COLUMN `auth_version`;"""
