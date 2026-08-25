"""Print the Tortoise schema SQL for migration review without modifying tables."""

import asyncio

from tortoise import Tortoise, connections
from tortoise.utils import get_schema_sql

from app.core.db.databases import TORTOISE_ORM


async def main() -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    print(get_schema_sql(connections.get("default"), safe=True))
    await connections.close_all()


if __name__ == "__main__":
    asyncio.run(main())
