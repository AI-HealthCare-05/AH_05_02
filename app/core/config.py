import os
import uuid
import zoneinfo
from dataclasses import field
from enum import StrEnum
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(StrEnum):
    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    ENV: Env = Env.LOCAL
    SECRET_KEY: str = f"default-secret-key{uuid.uuid4().hex}"
    TIMEZONE: zoneinfo.ZoneInfo = field(default_factory=lambda: zoneinfo.ZoneInfo("Asia/Seoul"))
    TEMPLATE_DIR: str = os.path.join(Path(__file__).resolve().parent.parent, "templates")

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "pw1234"
    DB_NAME: str = "ai_health"
    DB_CONNECT_TIMEOUT: int = 5
    DB_CONNECTION_POOL_MAXSIZE: int = 10
    DB_GENERATE_SCHEMAS: bool = False
    DATABASE_URL: str | None = None
    DEMO_MODE: bool = False
    CHALLENGE_V2_ENABLED: bool = False
    CHALLENGE_V2_CONTENT_APPROVED: bool = False
    # Actual human review is opt-in; never infer availability from a submitted photo.
    CHALLENGE_V2_REVIEWER_IDS: list[int] = []

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_STREAM: str = "ai:jobs"
    REDIS_CONSUMER_GROUP: str = "ai-workers"
    REDIS_JOB_TTL_SECONDS: int = 86400

    PREDICTION_PROVIDER: str = "development"
    PREDICTION_TIMEOUT_SECONDS: int = 30
    PREDICTION_MODEL_KEY: str = "diabetes_incidence"
    PREDICTION_MODEL_VERSION: str = "dev-diabetes-incidence-v0"
    PREDICTION_FEATURE_SCHEMA_VERSION: str = "klosa-diabetes-incident-v1"
    PREDICTION_THRESHOLD_VERSION: str = "unapproved"
    PREDICTION_MODEL_MIN_AGE: int = 45
    PREDICTION_MODEL_MAX_AGE: int | None = None
    PREDICTION_MODEL_POPULATION: str = "baseline_undiagnosed_age_45_plus"
    SAFETY_COPY_VERSION: str = "2026-08-19-v1"

    COOKIE_DOMAIN: str = ""  # Host-only by default; supports localhost and 127.0.0.1 without cross-host cookies.

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 14 * 24 * 60
    JWT_LEEWAY: int = 5
