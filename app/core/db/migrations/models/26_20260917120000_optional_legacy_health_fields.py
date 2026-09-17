from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    if db.capabilities.dialect == "mysql":
        return """
            ALTER TABLE `health_checkups`
                MODIFY `self_rated_health` VARCHAR(20) NULL,
                MODIFY `meal_count_yesterday` INT NULL;
        """
    if db.capabilities.dialect == "sqlite":
        rows = await db.execute_query_dict(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='health_checkups'"
        )
        if not rows:
            return "SELECT 1;"
        original = rows[0]["sql"]
        updated = original.replace('"self_rated_health" VARCHAR(20) NOT NULL', '"self_rated_health" VARCHAR(20)')
        updated = updated.replace('"meal_count_yesterday" INT NOT NULL', '"meal_count_yesterday" INT')
        if updated == original:
            return "SELECT 1;"
        columns = await db.execute_query_dict('PRAGMA table_info("health_checkups")')
        names = ", ".join('"' + column["name"].replace('"', '""') + '"' for column in columns)
        indexes = await db.execute_query_dict(
            "SELECT sql FROM sqlite_master WHERE tbl_name='health_checkups' AND type='index' AND sql IS NOT NULL"
        )
        create = updated.replace('"health_checkups"', '"health_checkups_legacy_nullable"', 1)
        return f"""
            {create};
            INSERT INTO "health_checkups_legacy_nullable" ({names}) SELECT {names} FROM "health_checkups";
            DROP TABLE "health_checkups";
            ALTER TABLE "health_checkups_legacy_nullable" RENAME TO "health_checkups";
            {"".join(index["sql"] + ";" for index in indexes)}
        """
    raise RuntimeError("Unsupported database dialect for optional legacy health fields")


async def downgrade(db: BaseDBAsyncClient) -> str:
    # Restoring NOT NULL would require inventing answers for newer records.
    del db
    return "SELECT 1;"
