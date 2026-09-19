from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    del db
    return """
        CREATE TABLE IF NOT EXISTS `current_screening_inputs` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `user_id` BIGINT NOT NULL,
            `health_checkup_id` BIGINT NOT NULL,
            `input_as_of_date` DATE NOT NULL,
            `walking_days` DOUBLE NULL,
            `energy_kcal` DOUBLE NULL,
            `protein_g` DOUBLE NULL,
            `fat_g` DOUBLE NULL,
            `carbohydrate_g` DOUBLE NULL,
            `sodium_mg` DOUBLE NULL,
            `region` VARCHAR(20) NULL,
            `urban` VARCHAR(20) NULL,
            `education` VARCHAR(30) NULL,
            `income_quartile` VARCHAR(10) NULL,
            `household_income_quartile` VARCHAR(10) NULL,
            `hypertension_family_history` BOOL NULL,
            `diabetes_family_history` BOOL NULL,
            `alcohol_frequency` VARCHAR(30) NULL,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            KEY `idx_current_screening_user` (`user_id`),
            KEY `idx_current_screening_checkup` (`health_checkup_id`)
        ) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    del db
    return "DROP TABLE IF EXISTS `current_screening_inputs`;"
