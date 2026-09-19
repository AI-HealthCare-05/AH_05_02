from __future__ import annotations

from tortoise import Tortoise, connections
from tortoise.exceptions import ConfigurationError

from app.core.db.databases import TORTOISE_APP_MODELS


async def reset_tortoise() -> None:
    try:
        await connections.close_all(discard=True)
    except ConfigurationError:
        pass
    connections._clear_storage()
    await Tortoise._reset_apps()
    Tortoise._inited = False


async def init_sqlite_test_db() -> None:
    await reset_tortoise()
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": TORTOISE_APP_MODELS}, timezone="Asia/Seoul")
    await Tortoise.generate_schemas()
