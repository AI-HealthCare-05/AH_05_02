import importlib
from types import SimpleNamespace

import pytest

repair = importlib.import_module("app.core.db.migrations.models.25_20260915160000_repair_user_height_cm")


class FakeDatabase:
    def __init__(self, dialect: str, rows: list[dict[str, object]]) -> None:
        self.capabilities = SimpleNamespace(dialect=dialect)
        self.rows = rows
        self.queries: list[str] = []

    async def execute_query_dict(self, query: str) -> list[dict[str, object]]:
        self.queries.append(query)
        return self.rows


@pytest.mark.asyncio
async def test_sqlite_repair_adds_missing_height_cm() -> None:
    database = FakeDatabase("sqlite", [{"name": "id"}, {"name": "email"}])

    sql = await repair.upgrade(database)

    assert "ADD COLUMN `height_cm` REAL NULL" in sql
    assert database.queries == ["PRAGMA table_info(`users`)"]


@pytest.mark.asyncio
async def test_sqlite_repair_is_idempotent() -> None:
    database = FakeDatabase("sqlite", [{"name": "id"}, {"name": "height_cm"}])

    assert await repair.upgrade(database) == ""


@pytest.mark.asyncio
async def test_mysql_repair_is_idempotent() -> None:
    database = FakeDatabase("mysql", [{"COLUMN_NAME": "height_cm"}])

    assert await repair.upgrade(database) == ""
