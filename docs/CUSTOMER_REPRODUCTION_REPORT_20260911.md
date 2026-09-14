# 고객용 재현 환경 점검 결과 — 2026-09-11

## 0. 결론

- PR #51이 포함된 최신 통합 기준 브랜치에서 Windows 신규 설치 절차와 MVP 개발 모드 실행을 재현했다.
- 메인 화면, API 문서, 당근의 숲, 회원가입부터 리포트까지의 핵심 HTTP 흐름이 통과했다.
- OpenAI API와 Clova OCR은 실제 호출에 성공했다.
- Kakao Local API는 키 형식 문제가 아니라 개발자 앱의 지도·로컬 서비스가 비활성화되어 HTTP 403을 반환한다.
- 실제 오늘이·내일이 모델 추론은 Git에 포함하지 않는 모델 Artifact가 별도 제공되지 않아 신규 PC에서 재현할 수 없다.
- Docker가 현재 검증 PC에 설치되어 있지 않아 MySQL·Redis·AI Worker·Nginx 전체 컨테이너 실행은 확인하지 못했다.

## 1. 검증 기준

- 기준 브랜치: `codex/customer-repro-20260911`
- 포함 기준: PR #51 병합 커밋 및 후속 의료기관 UI·API 수정
- 운영체제: Windows
- Python: 3.13
- 검증 방식: 빈 고객용 작업 폴더에 저장소를 새로 구성한 뒤 설치·테스트·실행

## 2. 통과 항목

| 구분 | 결과 | 비고 |
| --- | --- | --- |
| Windows 초기 설치 | 통과 | Python 3.13 가상환경 및 의존성 설치 |
| 전체 Python 테스트 | 통과 | `530 passed, 4 skipped` |
| 변경 파일 Ruff 검사 | 통과 | 오류 없음 |
| 메인 프론트 | 통과 | `/` HTTP 200 |
| 당근의 숲 | 통과 | `/forest` HTTP 200 |
| API 상태 | 통과 | `/api/health` HTTP 200 |
| API 문서 | 통과 | `/api/docs` HTTP 200 |
| 가입·로그인 | 통과 | `terms_agreed` 포함 계약 확인 |
| 프로필·동의·적합성 | 통과 | 45세 이상 전체 예측 흐름 |
| 건강정보 입력 | 통과 | 서버의 현재 입력 스키마 버전 자동 확인 |
| 오늘이 | 통과 | 개발 데모 Provider 기준 |
| 내일이 | 통과 | 개발 데모 Provider 기준 |
| 챌린지·기록 | 통과 | 추천, 사이클 생성, 일일 기록 |
| 대시보드·주간 리포트 | 통과 | JSON 및 PDF 생성 |
| OpenAI API | 통과 | 키 값은 로그에 출력하지 않음 |
| Clova OCR | 통과 | 메모리에서 만든 테스트 이미지의 텍스트 인식 |
| Git 비밀정보 검사 | 통과 | 추적 파일에서 입력한 비밀 키 미검출 |

## 3. 남은 차단 사항

### Kakao 지도·의료기관 검색

- 결과: HTTP 403
- 제공자 메시지: `App(D1V3) disabled OPEN_MAP_AND_LOCAL service.`
- 조치: Kakao Developers에서 해당 앱의 지도·로컬 서비스를 활성화하고, 웹 플랫폼 도메인과 JavaScript 키 사용 도메인을 등록한다.
- 활성화 후 `python scripts/verify-external-services.py`로 다시 확인한다.

### 실제 오늘이·내일이 모델

- 모델 바이너리는 저장소 정책상 Git에서 제외되어 있다.
- 신규 PC에는 검증된 모델 파일과 Manifest가 없으므로 개발용 결과만 재현된다.
- 실제 추론 재현을 위해 다음 중 하나를 확정해야 한다.
  1. 권한이 제한된 S3에서 체크섬 검증 후 자동 내려받기
  2. 배포 담당자가 암호화된 별도 Artifact 패키지 전달
- 모델을 받은 후 `scripts/provision-models.py`로 배치하고 Manifest SHA-256 검증을 통과해야 한다.

### Docker 전체 스택

- 현재 검증 PC에는 Docker 명령이 없어 컨테이너 전체 실행을 확인하지 못했다.
- Docker Desktop 설치 후 MySQL, Redis, AI Worker, FastAPI, Nginx 상태와 비동기 예측을 별도로 Smoke Test한다.

## 4. 이번에 보완한 재현 기능

- Windows·macOS 설치 테스트가 빈 `.env`의 DB·JWT 설정 때문에 실패하지 않도록 격리된 테스트 설정을 적용했다.
- 개발용 MVP 실행 시 실제 모델 파일이 없어도 오늘이·내일이 연결 흐름을 확인할 수 있게 했다.
- Kakao JavaScript 키의 프론트 하드코딩을 제거하고 서버 설정 API로 전달하도록 변경했다.
- Clova OCR 실제 업로드 엔드포인트와 이미지 크기·형식 검증을 추가했다.
- OpenAI·Kakao·Clova를 키 노출 없이 점검하는 스크립트를 추가했다.
- 고객용 HTTP Smoke Test를 추가해 가입부터 리포트까지 한 번에 검증할 수 있게 했다.

## 5. 최종 재현 완료 기준

- Kakao 지도·로컬 서비스 활성화 후 검색 API가 HTTP 200을 반환한다.
- 승인된 오늘이·내일이 Artifact를 신규 PC에 안전하게 공급하고 체크섬을 검증한다.
- Docker Desktop이 설치된 신규 PC에서 MySQL·Redis·AI Worker 포함 전체 Compose가 기동한다.
- 개발 데모가 아닌 실제 Artifact E2E에서 오늘이·내일이 작업이 완료된다.
- 실패·시간초과·API 키 누락 시 사용자 화면에 안전한 오류 문구가 표시된다.
