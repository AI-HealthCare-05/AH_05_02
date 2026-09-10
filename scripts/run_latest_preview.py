"""Run the upstream integration preview with an isolated local SQLite database.

This mode uses upstream demo behavior; it does not run the missing model artifacts.
The original 8022 service and its database are not touched.
"""

import argparse
import os
from pathlib import Path
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8023)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    (root / "storage").mkdir(exist_ok=True)
    os.environ.update(
        DEMO_MODE="true",
        DATABASE_URL="sqlite://storage/local-latest-preview.sqlite3",
    )
    print("Latest frontend/forest preview. Model inference pending artifact delivery.", flush=True)
    os.execv(sys.executable, [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(args.port)])


if __name__ == "__main__":
    main()
