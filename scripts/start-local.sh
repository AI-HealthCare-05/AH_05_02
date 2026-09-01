#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

command -v docker >/dev/null 2>&1 || {
  echo "Docker CLI를 찾을 수 없습니다. Docker Desktop을 설치·실행한 뒤 다시 시도하세요." >&2
  exit 1
}

docker info >/dev/null 2>&1 || {
  echo "Docker가 실행 중이 아닙니다. Docker Desktop을 실행한 뒤 다시 시도하세요." >&2
  exit 1
}

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo ".env를 .env.example에서 생성했습니다. 필요한 비밀값을 확인하세요."
fi

docker compose build fastapi
docker compose build ai-worker
docker compose up -d --no-build --remove-orphans
docker compose up -d --no-build --force-recreate --no-deps fastapi ai-worker nginx
docker compose ps

echo "Swagger: http://localhost/api/docs"
echo "중지: docker compose down"
