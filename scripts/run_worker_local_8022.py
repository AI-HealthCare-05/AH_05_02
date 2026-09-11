"""Run matching 8022 research worker on an isolated stream, without schema DDL.

Uses the same private DB-loading helper as the existing server launcher.
Never prints credentials. Display/operational approval is not enabled.
"""

import asyncio
import os
import sys
from pathlib import Path

from run_frontend_local_8022 import database_environment, local_queue_environment


async def main() -> None:
    from ai_worker.db import connect_db
    from ai_worker.worker import run_worker

    connection = await connect_db()
    try:
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT job_id, task_type, status, result FROM prediction_jobs LIMIT 0")
            await cursor.execute(
                "SELECT id, task_type, display_allowed, operational_model_activated FROM predictions LIMIT 0"
            )
    finally:
        connection.close()
    await run_worker(prepare_schema=False)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    sys.path.insert(0, str(root))
    os.environ.update(database_environment(root.parent / "AH_05_02" / ".env"))
    os.environ.update(local_queue_environment())
    os.environ["WORKER_NAME"] = "local8022-matching-worker"
    # Use the hash-verified shared8 current model and the standard RF25 future model.
    # Both remain research candidates and never enable public probability display.
    os.environ["S2_MODEL_RUNTIME_ENABLED"] = "false"
    os.environ["CURRENT_SCREENING_RUNTIME"] = "shared8-waist"
    os.environ["ML_SHARED8_MODEL_URI"] = str(
        root / "models/artifacts/candidates/diabetes_current_screening/knhanes-shared8-waist-sk180-v1/model.joblib"
    )
    os.environ["ML_SHARED7_MODEL_URI"] = str(
        root / "models/artifacts/candidates/diabetes_current_screening/knhanes-shared7-sk180-v1/model.joblib"
    )
    os.environ["ML_FIRST_INTERVAL_MODEL_URI"] = str(
        root / "models/artifacts/candidates/diabetes_incidence/rf25-first-interval-survival-ensemble-v1/model.joblib"
    )
    os.environ["MODEL_URI"] = str(
        root / "models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1/model.joblib"
    )
    try:
        asyncio.run(main())
    except Exception as error:
        # Logs may include DB credentials or task payloads; emit only the type.
        print(f"S2 local worker stopped: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1) from None
