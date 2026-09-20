#!/bin/sh
set -eu

# Apply committed schema changes before accepting API traffic. Demo SQLite is
# persisted between container replacements, so repair its legacy schema too.
if [ "${DEMO_MODE:-false}" = "true" ]; then
    uv run --no-sync python -m app.core.db.upgrade_demo_sqlite
else
    uv run --no-sync aerich upgrade
fi

# Public Drive delivery is optional. When configured, download once at startup,
# verify the pinned bundle and model digests, then load only the local files.
uv run --no-sync python -m app.vision.kfood_bundle

exec uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
