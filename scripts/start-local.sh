#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

required_models=(
  "models/artifacts/candidates/diabetes_current_screening/v050/model.joblib"
  "models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1.1-sav/model.joblib"
)
for model in "${required_models[@]}"; do
  if [[ ! -f "$model" ]]; then
    echo "필수 모델 파일이 없습니다: $model" >&2
    echo "docs/MODEL_LOCAL_SETUP.md에 따라 scripts/provision-models.py를 먼저 실행하세요." >&2
    exit 1
  fi
done

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
