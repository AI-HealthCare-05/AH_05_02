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
    ML_RESEARCH_ENDPOINTS_ENABLED: bool = False
    ML_SHARED7_MODEL_URI: str = ""
    ML_FIRST_INTERVAL_MODEL_URI: str = ""
    PREDICTION_TIMEOUT_SECONDS: int = 30
    PREDICTION_MODEL_KEY: str = "diabetes_incidence"
    PREDICTION_MODEL_VERSION: str = "rf25-tuned-spec40-v1.1-sav"
    PREDICTION_FEATURE_SCHEMA_VERSION: str = "klosa_stage3_25features_v1"
    PREDICTION_INPUT_SCHEMA_VERSION: str = "diabetes-incidence-api-25features-v1"
    PREDICTION_PREPROCESSING_VERSION: str = "train-median-indicator-mode-onehot-v1"
    PREDICTION_TARGET_DEFINITION_VERSION: str = "next-observation-new-diabetes-v1"
    PREDICTION_CALIBRATION_VERSION: str = "unapproved"
    PREDICTION_MODEL_ARTIFACT_DIGEST: str = "b96eaf408982399782073fce97977bef874012cf7d90551120da60266df68ddd"
    PREDICTION_THRESHOLD_VERSION: str = "validation-spec043-caution-recall090-sav-repro-v1"
    PREDICTION_DECISION_THRESHOLD: float | None = 0.02120045257343795
    PREDICTION_MODEL_MIN_AGE: int = 45
    PREDICTION_MODEL_MAX_AGE: int | None = 105
    PREDICTION_MODEL_POPULATION: str = "undiagnosed_klosa_age_45_105"
    PREDICTION_PROMOTION_STATUS: str = "candidate_only"
    MODEL_URI: str = "models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1.1-sav/model.joblib"
    MODEL_MANIFEST_URI: str = "models/registry/diabetes_incidence/candidates/rf25-tuned-spec40-v1.1-sav.json"
    CURRENT_SCREENING_MODEL_VERSION: str = "knhanes-current-diabetes-recall-v0.5.0"
    CURRENT_SCREENING_FEATURE_SCHEMA_VERSION: str = "knhanes-current-diabetes-screening-v2"
    CURRENT_SCREENING_INPUT_SCHEMA_VERSION: str = "knhanes-current-diabetes-screening-api-v1"
    CURRENT_SCREENING_PREPROCESSING_VERSION: str = "knhanes-2016-2024-recall-v050"
    CURRENT_SCREENING_TARGET_DEFINITION_VERSION: str = "current-diabetes-signal-v1"
    CURRENT_SCREENING_THRESHOLD_VERSION: str = "validation-2021-2022-spec042-v1"
    CURRENT_SCREENING_DECISION_THRESHOLD: float = 0.023227178771059433
    CURRENT_SCREENING_MODEL_ARTIFACT_DIGEST: str = "c257ebc7785d4a1b36a7cda6d9aeeb107dbfa1b6afbf4c64c806849b8969370e"
    CURRENT_SCREENING_MODEL_URI: str = "models/artifacts/candidates/diabetes_current_screening/v050/model.joblib"
    CURRENT_SCREENING_MANIFEST_URI: str = (
        "models/registry/diabetes_current_screening/candidates/knhanes-current-screening-v050.json"
    )
    SAFETY_COPY_VERSION: str = "2026-08-19-v1"

    # 식사 사진에서 채소 포함 여부만 자동 판별합니다. 칼로리·영양소는 계산하지 않습니다.
    FOOD_VISION_PROVIDER: str = "development"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    FOOD_VISION_TIMEOUT_SECONDS: int = 20
    FOOD_PHOTO_MAX_BYTES: int = 8 * 1024 * 1024

    # 위치 기반 근처 의료기관 조회. 진단·처방을 대신하지 않고, 위치 기반 안내만 제공합니다.
    MEDICAL_FACILITY_SEARCH_PROVIDER: str = "development"
    KAKAO_REST_API_KEY: str = ""
    # 카테고리 검색(HP8, 반경 내 병원 전체) 대신 키워드 검색으로 좁혀서 반환하기로 결정(2026-09-02 팀 회의).
    MEDICAL_FACILITY_SEARCH_KEYWORDS: str = "당뇨"
    MEDICAL_FACILITY_SEARCH_CATEGORY_GROUP_CODE: str = "HP8"
    # 텍스트 매칭 특성상 "내과" 키워드가 "구강내과"(치과 표기)까지 걸려서 치과가 섞여 들어오는 문제가 있어
    # 카테고리 이름에 아래 단어가 포함되면 결과에서 제외합니다(2026-09-02 팀 회의 이후 발견/보완).
    MEDICAL_FACILITY_SEARCH_EXCLUDED_CATEGORY_KEYWORDS: str = "치과,한의원"
    MEDICAL_FACILITY_SEARCH_TIMEOUT_SECONDS: int = 10
    MEDICAL_FACILITY_DEFAULT_RADIUS_METERS: int = 5000
    MEDICAL_FACILITY_MAX_RESULTS: int = 15

    # 국립중앙의료원 전국 응급의료기관 정보 조회 서비스
    EMERGENCY_FACILITY_SEARCH_PROVIDER: str = "nemc"
    NEMC_SERVICE_KEY: str = ""
    NEMC_EMERGENCY_API_URL: str = "https://apis.data.go.kr/B552657/ErmctInfoInqireService/getEgytLcinfoInqire"
    NEMC_EMERGENCY_TIMEOUT_SECONDS: int = 10
    EMERGENCY_FACILITY_MAX_RESULTS: int = 10

    COOKIE_DOMAIN: str = "localhost"

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 14 * 24 * 60
    JWT_LEEWAY: int = 5
