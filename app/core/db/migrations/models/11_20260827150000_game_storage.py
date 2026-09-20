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
        CREATE TABLE IF NOT EXISTS `user_wallets` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `user_id` BIGINT NOT NULL UNIQUE,
            `carrot_balance` INT NOT NULL DEFAULT 0,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            CHECK (`carrot_balance` >= 0)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        CREATE TABLE IF NOT EXISTS `reward_transactions` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `user_id` BIGINT NOT NULL,
            `transaction_type` VARCHAR(20) NOT NULL,
            `amount` INT NOT NULL,
            `balance_after` INT NOT NULL,
            `source_type` VARCHAR(40) NOT NULL,
            `source_ref` VARCHAR(100) NOT NULL,
            `idempotency_key` VARCHAR(150) NOT NULL UNIQUE,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            KEY `idx_reward_transactions_user_id` (`user_id`)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        CREATE TABLE IF NOT EXISTS `inventory_items` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `code` VARCHAR(50) NOT NULL UNIQUE,
            `name` VARCHAR(80) NOT NULL,
            `category` VARCHAR(30) NOT NULL,
            `price_carrots` INT NOT NULL DEFAULT 0,
            `asset_ref` VARCHAR(300) NULL,
            `is_active` BOOL NOT NULL DEFAULT TRUE,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        CREATE TABLE IF NOT EXISTS `user_inventory` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `user_id` BIGINT NOT NULL,
            `item_id` BIGINT NOT NULL,
            `quantity` INT NOT NULL DEFAULT 1,
            `acquired_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            KEY `idx_user_inventory_user_id` (`user_id`),
            KEY `idx_user_inventory_item_id` (`item_id`),
            UNIQUE KEY `uid_user_inventory_item` (`user_id`, `item_id`)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        CREATE TABLE IF NOT EXISTS `user_avatars` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `user_id` BIGINT NOT NULL UNIQUE,
            `equipped_item_ids` JSON NOT NULL,
            `version` INT NOT NULL DEFAULT 1,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `user_avatars`;
        DROP TABLE IF EXISTS `user_inventory`;
        DROP TABLE IF EXISTS `inventory_items`;
        DROP TABLE IF EXISTS `reward_transactions`;
        DROP TABLE IF EXISTS `user_wallets`;
        DROP TABLE IF EXISTS `challenge_verification_events`;
    """
