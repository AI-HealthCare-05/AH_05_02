"""Apply compatibility migrations to the persistent demo SQLite database."""

from __future__ import annotations

import asyncio
import importlib

from tortoise import Tortoise

from app.core.db.databases import TORTOISE_ORM

MIGRATIONS = ("app.core.db.migrations.models.27_20260917120000_optional_legacy_health_fields",)


async def upgrade_demo_sqlite() -> None:
    """Upgrade an existing demo database without deleting stored user records."""
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        connection = Tortoise.get_connection("default")
        if connection.capabilities.dialect != "sqlite":
            raise RuntimeError("Demo schema repair requires a SQLite database")
        for module_name in MIGRATIONS:
            migration = importlib.import_module(module_name)
            sql = await migration.upgrade(connection)
            await connection.execute_script(sql)
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(upgrade_demo_sqlite())
