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
    PREDICTION_TIMEOUT_SECONDS: int = 30

    PREDICTION_PROVIDER: str = "development"
    PREDICTION_MODEL_KEY: str = "diabetes_incidence"
    PREDICTION_MODEL_VERSION: str = "dev-diabetes-incidence-v0"
    PREDICTION_FEATURE_SCHEMA_VERSION: str = "klosa-diabetes-incident-v1"
    PREDICTION_THRESHOLD_VERSION: str = "unapproved"
    PREDICTION_MODEL_MIN_AGE: int = 45
    PREDICTION_MODEL_MAX_AGE: int | None = None
    PREDICTION_MODEL_POPULATION: str = "baseline_undiagnosed_age_45_plus"

    MODEL_URI: str = ""
    MODEL_CACHE_DIR: str = "/app/storage/models"
    AWS_REGION: str = "ap-northeast-2"
    AWS_S3_ENDPOINT_URL: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None

    WORKER_NAME: str = field(default_factory=lambda: os.getenv("HOSTNAME", "ai-worker"))
