#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
frontend_root="$project_root/src/frontend"
port="${PORT:-8765}"

if [[ ! -d "$frontend_root" ]]; then
  echo "프론트엔드 폴더를 찾을 수 없습니다: $frontend_root" >&2
  exit 1
fi

command -v python3 >/dev/null 2>&1 || {
  echo "python3를 찾을 수 없습니다. Python 3를 설치한 뒤 다시 실행하세요." >&2
  exit 1
}

cd "$frontend_root"

echo "프론트 미리보기 서버를 시작합니다."
echo "홈:      http://127.0.0.1:$port/"
echo "서비스:  http://127.0.0.1:$port/service"
echo "회원가입: http://127.0.0.1:$port/?auth=signup"
echo "종료:    Ctrl+C"
echo

python3 -c '
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import os
import urllib.parse

ROOT = os.getcwd()


class PreviewHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        parsed_path = urllib.parse.urlparse(path).path
        if parsed_path in ("/", "/service"):
            parsed_path = "/index.html" if parsed_path == "/" else "/suin/index.html"
        elif parsed_path.startswith("/static/suin/"):
            parsed_path = parsed_path[len("/static"):]
        elif parsed_path.startswith("/static/"):
            parsed_path = parsed_path[len("/static"):]
        return os.path.join(ROOT, parsed_path.lstrip("/"))


ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("PORT", "'"$port"'"))), PreviewHandler).serve_forever()
'
