"""Run the local frontend/API against the existing project's published DB port.

Read only database credentials from the sibling project's private .env; do not
copy secrets, change database contents, or override model/approval settings.
Run from the repository root using .venv/bin/python.
"""

import hashlib
import json
import os
from pathlib import Path

from dotenv import dotenv_values


def database_environment(source: Path) -> dict[str, str]:
    if not source.is_file():
        raise RuntimeError("Project database configuration file is missing")
    values = dotenv_values(source)
    required = ("DB_USER", "DB_PASSWORD", "DB_NAME", "DB_EXPOSE_PORT")
    if any(not values.get(key) for key in required):
        raise RuntimeError("Project database configuration is incomplete")
    return {
        "DB_HOST": "127.0.0.1",
        "DB_PORT": values["DB_EXPOSE_PORT"],
        "DB_USER": values["DB_USER"],
        "DB_PASSWORD": values["DB_PASSWORD"],
        "DB_NAME": values["DB_NAME"],
        # Explicitly choose MySQL without automatic schema generation.
        "DATABASE_URL": "",
        "DEMO_MODE": "false",
        "DB_GENERATE_SCHEMAS": "false",
    }


def local_queue_environment() -> dict[str, str]:
    """Use the project Redis and isolate 8022 from outdated Docker workers."""
    return {
        "REDIS_HOST": "127.0.0.1",
        "REDIS_PORT": "6380",
        "REDIS_DB": "0",
        "REDIS_STREAM": "ai:jobs:local8022:pr41-future",
        "CURRENT_SCREENING_REDIS_STREAM": "ai:jobs:local8022:pr41-current",
        "REDIS_CONSUMER_GROUP": "local8022-workers",
    }


def local_model_environment(root: Path) -> dict[str, str]:
    """Keep the explicitly selected local shared7 model until v061 is provisioned.

    No automatic model fallback: v061 must be selected explicitly and have its
    verified artifact available before launch. Run v061 with its dedicated
    worker image; it requires a different scikit-learn version from shared7.
    """
    runtime = os.environ.get("LOCAL_CURRENT_SCREENING_RUNTIME", "shared7")
    if runtime not in {"shared7", "v061"}:
        raise ValueError("LOCAL_CURRENT_SCREENING_RUNTIME must be shared7 or v061")
    name = "knhanes-shared7-sk180-v1" if runtime == "shared7" else "knhanes-current-screening-v061"
    manifest_path = root / f"models/registry/diabetes_current_screening/candidates/{name}.json"
    manifest = json.loads(manifest_path.read_text())
    artifact = root / manifest["artifact_local_path"]
    if not artifact.is_file():
        raise RuntimeError(f"Selected current screening model artifact is missing ({runtime})")
    with artifact.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != manifest["artifact_sha256"]:
        raise RuntimeError(f"Selected current screening artifact checksum does not match ({runtime})")
    return {
        "CURRENT_SCREENING_RUNTIME": runtime,
        "CURRENT_SCREENING_MODEL_VERSION": manifest["model_version"],
        "CURRENT_SCREENING_FEATURE_SCHEMA_VERSION": manifest["feature_schema_version"],
        "CURRENT_SCREENING_INPUT_SCHEMA_VERSION": manifest.get("input_schema_version", "knhanes-current-diabetes-screening-api-v1"),
        "CURRENT_SCREENING_THRESHOLD_VERSION": manifest["threshold_version"],
        "CURRENT_SCREENING_DECISION_THRESHOLD": str(manifest["threshold"]),
        "CURRENT_SCREENING_MODEL_ARTIFACT_DIGEST": manifest["artifact_sha256"],
        "CURRENT_SCREENING_MODEL_URI": str(root / manifest["artifact_local_path"]),
        "CURRENT_SCREENING_MANIFEST_URI": str(manifest_path),
        "CURRENT_SCREENING_PREPROCESSING_VERSION": "shared7-standard-api-frame-v1" if runtime == "shared7" else "knhanes-2016-2024-recall-v061",
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    os.environ.update(database_environment(root.parent / "AH_05_02" / ".env"))
    os.environ.update(local_queue_environment())
    os.environ.update(local_model_environment(root))
    os.execv(
        root / ".venv/bin/python",
        [
            str(root / ".venv/bin/python"),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8022",
        ],
    )
