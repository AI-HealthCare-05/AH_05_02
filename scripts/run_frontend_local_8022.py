"""Run the local frontend/API against the existing project's published DB port.

Read only database credentials from the sibling project's private .env; do not
copy secrets, change database contents, or override model/approval settings.
Run from the repository root using .venv/bin/python.
"""

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
        "REDIS_STREAM": "ai:jobs:local8022",
        "REDIS_CONSUMER_GROUP": "local8022-workers",
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    os.environ.update(database_environment(root.parent / "AH_05_02" / ".env"))
    os.environ.update(local_queue_environment())
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
