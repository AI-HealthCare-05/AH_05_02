from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import boto3
import joblib

from ai_worker.core import config


def _download_s3_model(uri: str) -> Path:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path:
        raise ValueError("MODEL_URI는 로컬 경로 또는 s3://bucket/key 형식이어야 합니다.")
    cache_dir = Path(config.MODEL_CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)
    destination = cache_dir / Path(parsed.path).name
    client = boto3.client(
        "s3",
        region_name=config.AWS_REGION,
        endpoint_url=config.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
    )
    client.download_file(parsed.netloc, parsed.path.lstrip("/"), str(destination))
    return destination


@lru_cache(maxsize=1)
def load_model():
    if not config.MODEL_URI:
        raise RuntimeError("MODEL_URI가 설정되지 않았습니다. demo_inference로 파이프라인을 먼저 확인하세요.")
    model_path = (
        _download_s3_model(config.MODEL_URI) if config.MODEL_URI.startswith("s3://") else Path(config.MODEL_URI)
    )
    if not model_path.exists():
        raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {model_path}")
    return joblib.load(model_path)
