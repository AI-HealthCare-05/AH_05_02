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

echo "[1/8] macOS 및 필수 명령 확인"
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "이 스크립트는 macOS 전용입니다." >&2
  exit 1
fi
command -v git >/dev/null 2>&1 || { echo "Git을 먼저 설치하세요." >&2; exit 1; }

echo "[2/8] OpenMP 런타임 확인"
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew를 찾을 수 없습니다. https://brew.sh 에서 Homebrew를 설치한 뒤 다시 실행하세요." >&2
  exit 1
fi
if ! brew list --versions libomp >/dev/null 2>&1; then
  echo "LightGBM·XGBoost용 libomp를 설치합니다."
  brew install libomp
fi
libomp_prefix="$(brew --prefix libomp)"
if [[ ! -f "$libomp_prefix/lib/libomp.dylib" ]]; then
  echo "libomp 설치 파일을 확인할 수 없습니다: $libomp_prefix/lib/libomp.dylib" >&2
  exit 1
fi
export CPPFLAGS="-I$libomp_prefix/include ${CPPFLAGS:-}"
export LDFLAGS="-L$libomp_prefix/lib ${LDFLAGS:-}"
export DYLD_FALLBACK_LIBRARY_PATH="$libomp_prefix/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
echo "libomp 확인 완료: $libomp_prefix"

echo "[3/8] uv 확인"
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
  echo "[4/8] Python 3.13 및 가상환경 구성"
  "${uv_command[@]}" python install 3.13
  "${uv_command[@]}" venv "$task_venv" --python 3.13

  echo "[5/8] 프로젝트 의존성 설치"
  "${uv_command[@]}" sync --all-groups --frozen --python 3.13
else
  echo "[4/8] Python·가상환경 설치 생략"
  echo "[5/8] 의존성 설치 생략"
fi

if [[ ! -x "$task_venv/bin/python" ]]; then
  echo "가상환경 Python이 없습니다. --skip-install 없이 다시 실행하세요." >&2
  exit 1
fi

echo "[6/8] LightGBM·XGBoost 로딩 확인"
"$task_venv/bin/python" -c 'import lightgbm, xgboost; print(f"LightGBM {lightgbm.__version__}, XGBoost {xgboost.__version__}: OK")'

echo "[7/8] 로컬 환경변수 파일 확인"
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo ".env를 .env.example에서 생성했습니다. 비밀값은 직접 입력하세요."
else
  echo "기존 .env를 보존했습니다."
fi

if [[ "$skip_tests" == false ]]; then
  echo "[8/8] 테스트 실행"
  "$task_venv/bin/python" -m pytest
else
  echo "[8/8] 테스트 생략"
fi

echo
echo "macOS 로컬 초기 설정이 완료되었습니다."
echo "가상환경 활성화: source .venv/bin/activate"
echo "전체 서비스 실행: ./scripts/start-local.sh"
echo "Swagger: http://localhost/api/docs"
