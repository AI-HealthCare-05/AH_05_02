#!/bin/sh
set -eu

# Apply committed schema changes before accepting API traffic. Aerich 0.9.3
# remains backward-compatible with the migration files created by <= 0.9.1.
uv run --no-sync aerich upgrade

exec uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
