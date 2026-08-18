import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from ai_worker.core import config, logger
from ai_worker.db import ensure_schema, update_job
from ai_worker.handlers import run_task


class StreamWorker:
    def __init__(self) -> None:
        self.redis = Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            decode_responses=True,
            health_check_interval=30,
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
            result = await run_task(task_type, payload)
            completed_at = datetime.now(config.TIMEZONE)
            completed_event = {
                "job_id": job_id,
                "status": "completed",
                "result": result,
                "worker_name": self.consumer,
                "attempts": attempt,
                "completed_at": completed_at.isoformat(),
            }
            await update_job(
                job_id,
                status="completed",
                worker_name=self.consumer,
                attempts=attempt,
                result=result,
                completed_at=completed_at,
            )
            await self.set_status(job_id, completed_event)
            await self.publish(job_id, completed_event)
            await self.redis.xack(config.REDIS_STREAM, config.REDIS_CONSUMER_GROUP, message_id)
        except Exception as exc:
            await self.handle_failure(message_id, fields, attempt, exc)

    async def handle_failure(self, message_id: str, fields: dict[str, str], attempt: int, exc: Exception) -> None:
        job_id = fields["job_id"]
        if attempt < config.AI_JOB_MAX_ATTEMPTS:
            retry_fields = dict(fields)
            retry_fields["attempt"] = str(attempt)
            await self.redis.xadd(config.REDIS_STREAM, retry_fields)
            await self.redis.xack(config.REDIS_STREAM, config.REDIS_CONSUMER_GROUP, message_id)
            retry_event = {"job_id": job_id, "status": "retrying", "attempts": attempt}
            await update_job(
                job_id,
                status="retrying",
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
        )
        await self.set_status(job_id, failed_event)
        await self.publish(job_id, failed_event)
        await self.redis.xack(config.REDIS_STREAM, config.REDIS_CONSUMER_GROUP, message_id)

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
        except (ConnectionError, OSError) as exc:
            logger.warning("Worker dependency unavailable; retrying in 3 seconds: %s", exc)
            await asyncio.sleep(3)
