from fastapi import FastAPI
from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise

from app.core import config

TORTOISE_APP_MODELS = [
    "aerich.models",
    "app.models.users",
    "app.models.prediction_jobs",
    "app.models.health",
    "app.models.engagement",
    "app.models.wellness",
    "app.models.game",
    "app.models.forest",
]

DEFAULT_CONNECTION = (
    config.DATABASE_URL
    if config.DATABASE_URL
    else "sqlite://storage/gandang_mvp.sqlite3"
    if config.DEMO_MODE
    else {
        "engine": "tortoise.backends.mysql",
        "dialect": "asyncmy",
        "credentials": {
            "host": config.DB_HOST,
            "port": config.DB_PORT,
            "user": config.DB_USER,
            "password": config.DB_PASSWORD,
            "database": config.DB_NAME,
            "connect_timeout": config.DB_CONNECT_TIMEOUT,
            "maxsize": config.DB_CONNECTION_POOL_MAXSIZE,
        },
    }
)

TORTOISE_ORM = {
    "connections": {"default": DEFAULT_CONNECTION},
    "apps": {
        "models": {
            "models": TORTOISE_APP_MODELS,
        },
    },
    "timezone": "Asia/Seoul",
}


def initialize_tortoise(app: FastAPI) -> None:
    Tortoise.init_models(TORTOISE_APP_MODELS, "models")
    register_tortoise(app, config=TORTOISE_ORM, generate_schemas=config.DB_GENERATE_SCHEMAS or config.DEMO_MODE)
