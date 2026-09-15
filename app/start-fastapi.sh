#!/bin/sh
set -eu

# Apply committed schema changes before accepting API traffic. The demo stack
# uses a disposable SQLite schema generated at startup, while committed Aerich
# migrations target the production MySQL dialect.
if [ "${DEMO_MODE:-false}" != "true" ]; then
    uv run --no-sync aerich upgrade
fi

exec uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
