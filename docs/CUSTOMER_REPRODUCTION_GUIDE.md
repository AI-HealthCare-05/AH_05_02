# 고객용 컴퓨터 재현 가이드

PR #51이 포함된 통합 기준에서 새 Windows 또는 macOS 컴퓨터가 서비스 코드를 재현하는 절차다. 비밀키와 모델 바이너리는 Git에 포함하지 않는다.

## 1. 최초 설치 검증

Windows:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1
```

macOS:

```bash
./scripts/setup-macos.sh
```

초기 설치 검사는 SQLite와 개발용 모델을 사용하므로 MySQL·Redis·실제 모델 파일이 없어도 실행된다. `tests/backend/api`의 레거시 MySQL 전용 검사는 Docker 통합 검사에서 수행한다.

## 2. 비밀 환경변수 입력

`.env.example`을 복사해 만든 `.env`에 다음 값을 직접 입력한다.

- `SECRET_KEY`, `DB_USER`, `DB_PASSWORD`, `DB_ROOT_PASSWORD`
- `KAKAO_REST_API_KEY`, `KAKAO_JAVASCRIPT_KEY`
- `OPENAI_API_KEY`, `OPENAI_MODEL`
- `CLOVA_OCR_URL`, `CLOVA_OCR_SECRET`

키 값은 문서·채팅·Git에 올리지 않는다. 중복된 변수명이 있으면 마지막 값만 적용될 수 있으므로 변수명은 한 번씩만 둔다.

외부 서비스 연결 확인:

```powershell
.\.venv\Scripts\python.exe .\scripts\verify-external-services.py
```

이 검사는 키 값을 출력하지 않는다. Kakao REST 검색, OpenAI 인증, CLOVA OCR의 합성 이미지 인식을 확인한다. Kakao JavaScript 키의 웹 도메인 등록은 실제 브라우저 주소에서 별도 확인한다.

## 3. 화면·API 데모 실행

모델 파일과 Docker 없이 화면·API 흐름을 확인한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_mvp_demo.ps1
```

- 서비스: `http://127.0.0.1:8000`
- API 문서: `http://127.0.0.1:8000/api/docs`
- 이 모드의 예측은 `development` 결과이며 실제 개인 위험도로 표시하지 않는다.

## 4. 실제 모델 포함 전체 서비스

오늘이·내일이 모델은 Git 제외 파일이므로 승인된 전달 경로에서 받은 뒤 해시를 검증해 배치한다.

```powershell
uv run python scripts/provision-models.py --today "C:\trusted\today\model.joblib" --tomorrow "C:\trusted\tomorrow\model.joblib"
```

그다음 Docker Desktop을 실행하고 다음을 사용한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

실제 모델까지 다른 컴퓨터에서 자동 재현하려면 모델 두 개를 내려받을 수 있는 권한 제한 S3 경로 또는 별도 전달 패키지가 반드시 필요하다. 모델 파일이 없는 상태를 실제 모델 성공으로 처리하지 않는다.

## 5. 합격 기준

- 최초 설치 검사 통과
- 외부 서비스 3종 검사 `ok`
- 회원가입·동의·건강정보 입력·결과·챌린지·리포트·당근의 숲 화면 접근
- 실제 모델 모드에서는 오늘이·내일이 아티팩트 해시 일치 및 Worker 추론 완료
- 새로고침 후 DB 기록 유지
- 비밀키가 로그·응답·Git 변경 목록에 노출되지 않음
