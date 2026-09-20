from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from tortoise import Tortoise


@pytest.mark.asyncio
async def test_optional_legacy_health_fields_are_nullable_without_data_loss(tmp_path: Path) -> None:
    database = tmp_path / "demo.sqlite3"
    await Tortoise.init(db_url=f"sqlite://{database}", modules={"models": ["aerich.models"]})
    connection = Tortoise.get_connection("default")
    try:
        await connection.execute_script(
            """
            CREATE TABLE "health_checkups" (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                "self_rated_health" VARCHAR(20) NOT NULL,
                "meal_count_yesterday" INT NOT NULL
            );
            CREATE INDEX "idx_health_checkups_health" ON "health_checkups" ("self_rated_health");
            INSERT INTO "health_checkups" ("self_rated_health", "meal_count_yesterday")
            VALUES ('good', 3);
            """
        )
        migration = importlib.import_module(
            "app.core.db.migrations.models.27_20260917120000_optional_legacy_health_fields"
        )
        await connection.execute_script(await migration.upgrade(connection))

        columns = await connection.execute_query_dict('PRAGMA table_info("health_checkups")')
        nullable = {column["name"]: column["notnull"] for column in columns}
        rows = await connection.execute_query_dict(
            'SELECT "self_rated_health", "meal_count_yesterday" FROM "health_checkups"'
        )
        indexes = await connection.execute_query_dict(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='health_checkups'"
        )

        assert nullable["self_rated_health"] == 0
        assert nullable["meal_count_yesterday"] == 0
        assert rows == [{"self_rated_health": "good", "meal_count_yesterday": 3}]
        assert {index["name"] for index in indexes} == {"idx_health_checkups_health"}
    finally:
        await Tortoise.close_connections()
