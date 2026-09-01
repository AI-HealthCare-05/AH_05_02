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

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_STREAM: str = "ai:jobs"
    REDIS_CONSUMER_GROUP: str = "ai-workers"
    REDIS_JOB_TTL_SECONDS: int = 86400

    PREDICTION_PROVIDER: str = "development"
    PREDICTION_TIMEOUT_SECONDS: int = 30
    PREDICTION_MODEL_KEY: str = "diabetes_incidence"
    PREDICTION_MODEL_VERSION: str = "rf25-tuned-spec40-v1"
    PREDICTION_FEATURE_SCHEMA_VERSION: str = "klosa_stage3_25features_v1"
    PREDICTION_INPUT_SCHEMA_VERSION: str = "diabetes-incidence-api-25features-v1"
    PREDICTION_PREPROCESSING_VERSION: str = "train-median-indicator-mode-onehot-v1"
    PREDICTION_TARGET_DEFINITION_VERSION: str = "next-observation-new-diabetes-v1"
    PREDICTION_CALIBRATION_VERSION: str = "unapproved"
    PREDICTION_MODEL_ARTIFACT_DIGEST: str = "e5067dacd50006b8d7681ef9e558a2a3488913ae1db58d15632c842623c05bf8"
    PREDICTION_THRESHOLD_VERSION: str = "validation-spec043-caution-recall090-v1"
    PREDICTION_DECISION_THRESHOLD: float | None = 0.021153602801262862
    PREDICTION_MODEL_MIN_AGE: int = 45
    PREDICTION_MODEL_MAX_AGE: int | None = 105
    PREDICTION_MODEL_POPULATION: str = "undiagnosed_klosa_age_45_105"
    PREDICTION_PROMOTION_STATUS: str = "candidate_only"
    MODEL_URI: str = "models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1/model.joblib"
    MODEL_MANIFEST_URI: str = "models/registry/diabetes_incidence/candidates/rf25-tuned-spec40-v1.json"
    SAFETY_COPY_VERSION: str = "2026-08-19-v1"

    # 식사 사진에서 채소 포함 여부만 자동 판별합니다. 칼로리·영양소는 계산하지 않습니다.
    FOOD_VISION_PROVIDER: str = "development"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    FOOD_VISION_TIMEOUT_SECONDS: int = 20
    FOOD_PHOTO_MAX_BYTES: int = 8 * 1024 * 1024

    COOKIE_DOMAIN: str = "localhost"

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 14 * 24 * 60
    JWT_LEEWAY: int = 5
