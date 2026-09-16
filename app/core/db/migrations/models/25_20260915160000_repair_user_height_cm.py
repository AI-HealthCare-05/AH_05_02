from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = False
# Aerich unconditionally passes the returned SQL to ``execute_script()``.
# Returning an empty string therefore reaches asyncmy/MySQL as an empty query
# and aborts startup with error 1065 on databases that already have the column.
NO_OP_SQL = "SELECT 1;"


async def upgrade(db: BaseDBAsyncClient) -> str:
    """Repair deployments whose migration history and users table drifted apart."""

    dialect = db.capabilities.dialect
    if dialect == "sqlite":
        columns = await db.execute_query_dict("PRAGMA table_info(`users`)")
        if any(column.get("name") == "height_cm" for column in columns):
            return NO_OP_SQL
        return "ALTER TABLE `users` ADD COLUMN `height_cm` REAL NULL;"

    if dialect == "mysql":
        columns = await db.execute_query_dict(
            """
            SELECT `COLUMN_NAME`
            FROM `INFORMATION_SCHEMA`.`COLUMNS`
            WHERE `TABLE_SCHEMA` = DATABASE()
              AND `TABLE_NAME` = 'users'
              AND `COLUMN_NAME` = 'height_cm'
            """
        )
        if columns:
            return NO_OP_SQL
        return "ALTER TABLE `users` ADD COLUMN `height_cm` DOUBLE NULL;"

    raise RuntimeError(f"Unsupported database dialect for height_cm repair: {dialect}")


async def downgrade(db: BaseDBAsyncClient) -> str:
    # This is a repair migration for a column required by the current User model.
    # Removing it during rollback would recreate the production signup failure.
    del db
    return NO_OP_SQL
