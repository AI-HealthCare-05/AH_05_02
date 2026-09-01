import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import ResponseError
from redis.exceptions import TimeoutError as RedisTimeoutError

from ai_worker.core import config, logger
from ai_worker.db import ensure_schema, persist_prediction, update_job
from ai_worker.handlers import run_task_with_timeout
from app.prediction.errors import classify_ml_input_error
from src.ml.inference.diabetes_current_screening import (
    CurrentScreeningArtifactUnavailableError,
    CurrentScreeningContractError,
)
from src.ml.inference.diabetes_standard import ModelArtifactUnavailableError, ModelContractError


class StreamWorker:
    def __init__(self) -> None:
        self.redis = Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            decode_responses=True,
            health_check_interval=30,
            socket_timeout=None,
        )
        self.consumer = config.WORKER_NAME

    @staticmethod
    def channel(job_id: str) -> str:
        return f"ai:jobs:{job_id}:events"

    @staticmethod
    def cache_key(job_id: str) -> str:
        return f"ai:jobs:{job_id}"

    async def publish(self, job_id: str, event: dict[str, Any]) -> None:
        payload = json.dumps(event, ensure_ascii=False, default=str)
        await self.redis.publish(self.channel(job_id), payload)

    async def set_status(self, job_id: str, mapping: dict[str, Any]) -> None:
        safe_mapping = {
            key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
            for key, value in mapping.items()
            if value is not None
        }
        await self.redis.hset(self.cache_key(job_id), mapping=safe_mapping)
        await self.redis.expire(self.cache_key(job_id), config.REDIS_JOB_TTL_SECONDS)

    async def ensure_group(self) -> None:
        try:
            await self.redis.xgroup_create(
                name=config.REDIS_STREAM,
                groupname=config.REDIS_CONSUMER_GROUP,
                id="0-0",
                mkstream=True,
            )
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def handle_message(self, message_id: str, fields: dict[str, str]) -> None:
        job_id = fields["job_id"]
        task_type = fields["task_type"]
        attempt = int(fields.get("attempt", "0")) + 1
        started_at = datetime.now(config.TIMEZONE)
        running_event = {
            "job_id": job_id,
            "status": "running",
            "worker_name": self.consumer,
            "attempts": attempt,
            "started_at": started_at.isoformat(),
        }
        await update_job(
            job_id,
            status="running",
            worker_name=self.consumer,
            attempts=attempt,
            started_at=started_at,
        )
        await self.set_status(job_id, running_event)
        await self.publish(job_id, running_event)

        try:
            payload = json.loads(fields.get("payload", "{}"))
            result = await run_task_with_timeout(task_type, payload, config.PREDICTION_TIMEOUT_SECONDS)
            prediction_id = (
                await persist_prediction(job_id, result)
                if task_type in {"diabetes_incidence", "diabetes_current_screening"}
                else None
            )
            completed_at = datetime.now(config.TIMEZONE)
            completed_event = {
                "job_id": job_id,
                "status": "succeeded",
                "prediction_id": prediction_id,
                "worker_name": self.consumer,
                "attempts": attempt,
                "completed_at": completed_at.isoformat(),
            }
            await update_job(
                job_id,
                status="succeeded",
                worker_name=self.consumer,
                attempts=attempt,
                result=result,
                completed_at=completed_at,
                prediction_id=prediction_id,
            )
            await self.set_status(job_id, completed_event)
            await self.publish(job_id, completed_event)
            await self.redis.xack(config.REDIS_STREAM, config.REDIS_CONSUMER_GROUP, message_id)
            await self.redis.xdel(config.REDIS_STREAM, message_id)
        except TimeoutError as exc:
            await self.handle_failure(message_id, fields, config.AI_JOB_MAX_ATTEMPTS, exc, error_code="TIMEOUT")
        except (ValidationError, ValueError) as exc:
            # 모델 입력 계약 위반: 데이터를 고치지 않는 한 재시도해도 계속 실패하므로 즉시 종결한다.
            error_code = classify_ml_input_error(exc)
            await self.handle_failure(message_id, fields, config.AI_JOB_MAX_ATTEMPTS, exc, error_code=error_code)
        except ModelArtifactUnavailableError as exc:
            await self.handle_failure(
                message_id, fields, config.AI_JOB_MAX_ATTEMPTS, exc, error_code="ML_MODEL_UNAVAILABLE"
            )
        except ModelContractError as exc:
            await self.handle_failure(
                message_id, fields, config.AI_JOB_MAX_ATTEMPTS, exc, error_code="ML_MODEL_CONTRACT_ERROR"
            )
        except CurrentScreeningArtifactUnavailableError as exc:
            await self.handle_failure(
                message_id, fields, config.AI_JOB_MAX_ATTEMPTS, exc, error_code="ML_MODEL_UNAVAILABLE"
            )
        except CurrentScreeningContractError as exc:
            await self.handle_failure(
                message_id, fields, config.AI_JOB_MAX_ATTEMPTS, exc, error_code="ML_MODEL_CONTRACT_ERROR"
            )
        except RuntimeError as exc:
            # providers.load_standard_model()/_predict_score()가 던지는 영구적 모델 계약 오류.
            # 배포를 고치지 않는 한 재시도해도 동일하게 실패하므로 즉시 종결하고, 다른 Provider로 자동 전환하지 않는다.
            permanent_model_errors = {
                "MODEL_ARTIFACT_UNAVAILABLE",
                "MODEL_DIGEST_MISMATCH",
                "MODEL_CONTRACT_MISMATCH",
            }
            error_code = str(exc) if str(exc) in permanent_model_errors else None
            if error_code is not None:
                await self.handle_failure(message_id, fields, config.AI_JOB_MAX_ATTEMPTS, exc, error_code=error_code)
            else:
                await self.handle_failure(message_id, fields, attempt, exc)
        except Exception as exc:
            await self.handle_failure(message_id, fields, attempt, exc)

    async def handle_failure(
        self,
        message_id: str,
        fields: dict[str, str],
        attempt: int,
        exc: Exception,
        error_code: str | None = None,
    ) -> None:
        job_id = fields["job_id"]
        if attempt < config.AI_JOB_MAX_ATTEMPTS:
            retry_fields = dict(fields)
            retry_fields["attempt"] = str(attempt)
            await self.redis.xadd(config.REDIS_STREAM, retry_fields)
            await self.redis.xack(config.REDIS_STREAM, config.REDIS_CONSUMER_GROUP, message_id)
            await self.redis.xdel(config.REDIS_STREAM, message_id)
            retry_event = {"job_id": job_id, "status": "running", "attempts": attempt}
            await update_job(
                job_id,
                status="running",
                worker_name=self.consumer,
                attempts=attempt,
                error=str(exc),
            )
            await self.set_status(job_id, retry_event)
            await self.publish(job_id, retry_event)
            return

        completed_at = datetime.now(config.TIMEZONE)
        failed_event = {
            "job_id": job_id,
            "status": "failed",
            "error": str(exc),
            "error_code": error_code or "INFERENCE_FAILED",
            "retryable": error_code == "TIMEOUT",
            "retry_after_seconds": 30 if error_code == "TIMEOUT" else None,
            "attempts": attempt,
            "completed_at": completed_at.isoformat(),
        }
        await update_job(
            job_id,
            status="failed",
            worker_name=self.consumer,
            attempts=attempt,
            error=str(exc),
            completed_at=completed_at,
            error_code=error_code or "INFERENCE_FAILED",
            retryable=error_code == "TIMEOUT",
            retry_after_seconds=30 if error_code == "TIMEOUT" else None,
        )
        await self.set_status(job_id, failed_event)
        await self.publish(job_id, failed_event)
        await self.redis.xack(config.REDIS_STREAM, config.REDIS_CONSUMER_GROUP, message_id)
        await self.redis.xdel(config.REDIS_STREAM, message_id)

    async def reclaim_pending(self) -> None:
        claimed = await self.redis.xautoclaim(
            config.REDIS_STREAM,
            config.REDIS_CONSUMER_GROUP,
            self.consumer,
            min_idle_time=config.REDIS_CLAIM_IDLE_MS,
            start_id="0-0",
            count=10,
        )
        for message_id, fields in claimed[1]:
            await self.handle_message(message_id, fields)

    async def run(self) -> None:
        await self.redis.ping()
        await ensure_schema()
        await self.ensure_group()
        await self.reclaim_pending()
        Path("/tmp/ai-worker-ready").touch()
        logger.info("AI Worker ready: consumer=%s stream=%s", self.consumer, config.REDIS_STREAM)
        try:
            while True:
                messages = await self.redis.xreadgroup(
                    groupname=config.REDIS_CONSUMER_GROUP,
                    consumername=self.consumer,
                    streams={config.REDIS_STREAM: ">"},
                    count=1,
                    block=5000,
                )
                for _, entries in messages:
                    for message_id, fields in entries:
                        await self.handle_message(message_id, fields)
        finally:
            await self.redis.aclose()


async def run_worker() -> None:
    worker = StreamWorker()
    while True:
        try:
            await worker.run()
            return
        except (RedisConnectionError, RedisTimeoutError, ConnectionError, OSError) as exc:
            logger.warning("Worker dependency unavailable; retrying in 3 seconds: %s", exc)
            await asyncio.sleep(3)
