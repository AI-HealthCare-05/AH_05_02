import os
import zoneinfo
from dataclasses import field

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    TIMEZONE: zoneinfo.ZoneInfo = field(default_factory=lambda: zoneinfo.ZoneInfo("Asia/Seoul"))

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "ai_health"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_STREAM: str = "ai:jobs"
    REDIS_CONSUMER_GROUP: str = "ai-workers"
    REDIS_JOB_TTL_SECONDS: int = 86400
    REDIS_CLAIM_IDLE_MS: int = 60000
    AI_JOB_MAX_ATTEMPTS: int = 3

    MODEL_URI: str = ""
    MODEL_CACHE_DIR: str = "/app/storage/models"
    AWS_REGION: str = "ap-northeast-2"
    AWS_S3_ENDPOINT_URL: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None

    WORKER_NAME: str = field(default_factory=lambda: os.getenv("HOSTNAME", "ai-worker"))
