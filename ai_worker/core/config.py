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
    PREDICTION_MODEL_VERSION: str = "rf25-tuned-spec40-v1.1-sav"
    PREDICTION_FEATURE_SCHEMA_VERSION: str = "klosa_stage3_25features_v1"
    PREDICTION_THRESHOLD_VERSION: str = "validation-spec043-caution-recall090-sav-repro-v1"
    PREDICTION_MODEL_MIN_AGE: int = 45
    PREDICTION_MODEL_MAX_AGE: int | None = 105
    PREDICTION_MODEL_POPULATION: str = "undiagnosed_klosa_age_45_105"
    PREDICTION_PROMOTION_STATUS: str = "candidate_only"
    PREDICTION_INPUT_SCHEMA_VERSION: str = "diabetes-incidence-api-25features-v1"
    PREDICTION_PREPROCESSING_VERSION: str = "train-median-indicator-mode-onehot-v1"
    PREDICTION_TARGET_DEFINITION_VERSION: str = "next-observation-new-diabetes-v1"
    PREDICTION_CALIBRATION_VERSION: str = "unapproved"
    PREDICTION_MODEL_ARTIFACT_DIGEST: str = "b96eaf408982399782073fce97977bef874012cf7d90551120da60266df68ddd"
    PREDICTION_DECISION_THRESHOLD: float | None = 0.02120045257343795

    MODEL_URI: str = "models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1.1-sav/model.joblib"
    MODEL_MANIFEST_URI: str = "models/registry/diabetes_incidence/candidates/rf25-tuned-spec40-v1.1-sav.json"
    CURRENT_SCREENING_MODEL_URI: str = "models/artifacts/candidates/diabetes_current_screening/v050/model.joblib"
    CURRENT_SCREENING_MANIFEST_URI: str = (
        "models/registry/diabetes_current_screening/candidates/knhanes-current-screening-v050.json"
    )
    MODEL_CACHE_DIR: str = "/app/storage/models"
    AWS_REGION: str = "ap-northeast-2"
    AWS_S3_ENDPOINT_URL: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None

    WORKER_NAME: str = field(default_factory=lambda: os.getenv("HOSTNAME", "ai-worker"))
