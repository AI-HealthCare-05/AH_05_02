#!/usr/bin/env bash
set -euo pipefail

skip_install=false
skip_tests=false

for arg in "$@"; do
  case "$arg" in
    --skip-install) skip_install=true ;;
    --skip-tests) skip_tests=true ;;
    *) echo "지원하지 않는 옵션입니다: $arg" >&2; exit 2 ;;
  esac
done

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
task_uv_cache="$project_root/tmp/uv-cache"
task_venv="$project_root/.venv"
cd "$project_root"

echo "[1/6] 필수 명령 확인"
command -v git >/dev/null 2>&1 || { echo "Git을 먼저 설치하세요." >&2; exit 1; }

echo "[2/6] uv 확인"
if command -v uv >/dev/null 2>&1; then
  uv_command=(uv)
else
  command -v python3 >/dev/null 2>&1 || {
    echo "Python 3 또는 uv를 먼저 설치하세요." >&2
    exit 1
  }
  python3 -m pip install --user uv
  uv_command=(python3 -m uv)
fi

export UV_CACHE_DIR="$task_uv_cache"

if [[ "$skip_install" == false ]]; then
  echo "[3/6] Python 3.13 및 가상환경 구성"
  "${uv_command[@]}" python install 3.13
  "${uv_command[@]}" venv "$task_venv" --python 3.13

  echo "[4/6] 프로젝트 의존성 설치"
  "${uv_command[@]}" sync --all-groups --frozen --python 3.13
else
  echo "[3/6] Python·가상환경 설치 생략"
  echo "[4/6] 의존성 설치 생략"
fi

echo "[5/6] 로컬 환경변수 파일 확인"
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo ".env를 .env.example에서 생성했습니다. 비밀값은 직접 입력하세요."
else
  echo "기존 .env를 보존했습니다."
fi

if [[ "$skip_tests" == false ]]; then
  echo "[6/6] 테스트 실행"
  "$task_venv/bin/python" -m pytest
else
  echo "[6/6] 테스트 생략"
fi

echo
echo "macOS 로컬 초기 설정이 완료되었습니다."
echo "가상환경 활성화: source .venv/bin/activate"
echo "전체 서비스 실행: ./scripts/start-local.sh"
echo "Swagger: http://localhost/api/docs"
