from redis.asyncio import Redis

from app.core import config

redis_client = Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    db=config.REDIS_DB,
    decode_responses=True,
    health_check_interval=30,
)


async def close_redis() -> None:
    await redis_client.aclose()
