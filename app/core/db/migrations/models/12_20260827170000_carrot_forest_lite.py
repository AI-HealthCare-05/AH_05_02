from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `forest_spaces` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `group_id` BIGINT NOT NULL UNIQUE,
            `name` VARCHAR(40) NOT NULL DEFAULT '당근의 숲',
            `created_by_user_id` BIGINT NOT NULL,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            KEY `idx_forest_space_group` (`group_id`),
            KEY `idx_forest_space_creator` (`created_by_user_id`)
        );
        CREATE TABLE IF NOT EXISTS `forest_avatars` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `user_id` BIGINT NOT NULL UNIQUE,
            `display_name` VARCHAR(20) NOT NULL,
            `hair_code` VARCHAR(40) NOT NULL DEFAULT 'midnight_short',
            `outfit_code` VARCHAR(40) NOT NULL DEFAULT 'orange_hoodie',
            `accessory_code` VARCHAR(40) NOT NULL DEFAULT 'none',
            `carrot_balance` INT NOT NULL DEFAULT 100,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            KEY `idx_forest_avatar_user` (`user_id`)
        );
        CREATE TABLE IF NOT EXISTS `forest_inventories` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `user_id` BIGINT NOT NULL,
            `item_code` VARCHAR(40) NOT NULL,
            `acquired_source` VARCHAR(40) NOT NULL,
            `acquired_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            UNIQUE KEY `uid_forest_inventory_item` (`user_id`, `item_code`),
            KEY `idx_forest_inventory_user` (`user_id`)
        );
        CREATE TABLE IF NOT EXISTS `forest_objects` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `forest_space_id` BIGINT NOT NULL,
            `placed_by_user_id` BIGINT NOT NULL,
            `object_code` VARCHAR(40) NOT NULL,
            `position_x` INT NOT NULL,
            `position_y` INT NOT NULL,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            KEY `idx_forest_object_space` (`forest_space_id`),
            KEY `idx_forest_object_user` (`placed_by_user_id`)
        );
        CREATE TABLE IF NOT EXISTS `forest_rewards` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `user_id` BIGINT NOT NULL,
            `forest_space_id` BIGINT NOT NULL,
            `source_key` VARCHAR(100) NOT NULL UNIQUE,
            `reward_date` DATE NOT NULL,
            `carrot_amount` INT NOT NULL,
            `item_code` VARCHAR(40) NULL,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            KEY `idx_forest_reward_user` (`user_id`),
            KEY `idx_forest_reward_space` (`forest_space_id`),
            KEY `idx_forest_reward_date` (`reward_date`)
        );
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `forest_rewards`;
        DROP TABLE IF EXISTS `forest_objects`;
        DROP TABLE IF EXISTS `forest_inventories`;
        DROP TABLE IF EXISTS `forest_avatars`;
        DROP TABLE IF EXISTS `forest_spaces`;
    """
