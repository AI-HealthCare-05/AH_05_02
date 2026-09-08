# 백엔드 구현 현황 및 미해결 이슈 (2026.9.3 기준)

## 1. 의료기관·응급실 검색 (PR #32, `feature/medical-facility-search`)

**구현 완료**
- 카카오 로컬 API 기반 의료기관 검색 (`app/facilities/providers.py` — `KakaoLocalMedicalFacilitySearchProvider`)
- 국립중앙의료원(NEMC) 기반 응급실 검색 (`NemcEmergencyFacilitySearchProvider`)
- 개발용 목업 provider 포함 (`MEDICAL_FACILITY_SEARCH_PROVIDER=development`로 전환 가능)
- 라우터: `GET /medical-facilities/nearby`, `GET /emergency-facilities/nearby` (`app/apis/v1/facility_routers.py`)
- 프론트 계약 일치 확인: `app.js`가 호출하는 경로와 백엔드 라우터 경로가 정확히 일치

**리뷰 반영 완료** (커밋 f7eb5f3, d572d1d, eea4663)
- 위치 확인 실패 시 서울 좌표로 자동 검색하던 동작 제거
- 위치 권한 거부·시간초과 시 주소 직접 입력 폼으로 안내
- 검색 시작·실패 시 이전 지도·마커·결과 초기화 (`resetFacilitySearchUi`)
- 주소 검색 기준점 라벨을 "현재 위치" → "검색 기준 위치"로 수정
- 119 안내 문구는 검색 성공 여부와 무관하게 항상 고정 노출

**리뷰·병합 완료**
- 리뷰어(J36-Ai-Editer) 재검토 완료, CI 통과(`eea4663` 기준 success) 확인 후 통합 완료
- 미해결 이슈 없음

## 2. 예측 파이프라인 (ai_worker, `codex/fe-ui-layout-polish` 로컬 테스트 기준)

**오늘 발견·수정한 이슈**
1. ai-worker가 redis 타임아웃(`redis.exceptions.TimeoutError`)에서 크래시 루프 — 최상위 재시도 예외 처리에 `RedisError`가 빠져 있었음. `except (ConnectionError, OSError, RedisError)`로 수정.
2. `.env`의 `PREDICTION_PROVIDER=artifact`가 미구현 provider(`ArtifactPredictionProvider`, "PR #4 이후 연결 예정")를 가리켜 항상 실패 — `development`로 전환.
3. MySQL `predictions` 테이블에 모델이 요구하는 `input_as_of_date` 컬럼이 없어 INSERT 실패 — 브랜치 전환 중 스키마 drift로 발생, 수동 `ALTER TABLE`로 해결(이후 PR #28 병합분에서는 정식 컬럼으로 재확인·재추가).
4. (PR #28 병합 이후) ai-worker 컨테이너에 `lightgbm`이 설치되어 있지 않아 실제 모델 추론 실패 — `ai_worker/Dockerfile`의 `uv sync`가 `ai` 그룹만 설치하고 `lightgbm`이 속한 `modeling` 그룹을 빠뜨렸던 것. `--group modeling` 추가로 해결.

**반영 상태**
- 1번(redis 예외처리), 4번(Dockerfile `modeling` 그룹)은 코드 변경 사항이라 `fix/e2e-integration-signup-and-worker-deps` PR에 포함되어 이미 GitHub에 반영됨 (커밋 `16814ac`).
- 2번(`PREDICTION_PROVIDER` 값)은 `.env` 설정이라 애초에 git 추적 대상이 아니고, 3번(DB 컬럼 추가)은 로컬 DB에 직접 실행한 수동 `ALTER TABLE`이라 코드로 올릴 대상이 아님 — 둘 다 로컬/환경 조치로 남는 것이 정상.

**주의할 점**
- `DB_GENERATE_SCHEMAS=true`는 없는 테이블만 새로 만들 뿐, 기존 테이블에 새 컬럼을 자동으로 추가해주지 않음. 브랜치를 옮기며 모델 필드가 늘어날 때마다 수동 `ALTER TABLE`이 필요할 수 있음 — 반복되면 `docker compose down -v`로 로컬 DB 초기화 고려.
- `docker compose restart <service>`는 `.env` 값을 다시 읽지 않음. 환경변수 변경 후에는 `down` → `up -d`(또는 `--force-recreate`)로 컨테이너를 재생성해야 함.

## 3. 통합 브랜치 `codex/e2e-integration` (PR #28) 반영 후 발견된 프론트/백엔드 계약 불일치

로컬 테스트 중 다음 두 가지 통합 버그를 발견·수정함 (PR #28 자체의 기존 버그로, 오늘 작업 중 발견):

1. **회원가입 실패**: 백엔드 `SignUpRequest`가 `terms_agreed: bool`을 필수 필드로 요구하는데, 프론트 `app.js`의 회원가입 요청이 이 필드를 아예 보내지 않음. 이용약관 체크박스(`#personal-consent`)는 화면에 있었지만 값이 전송되지 않았음 → 수정 완료.
2. **이용 가능 확인 단계 405 에러**: 프론트가 `PATCH /users/me`를 호출하는데 실제 라우터는 `PATCH /users/me/profile`로만 등록되어 있었음 → 프론트 호출 경로 수정 완료.

위 두 가지 수정 사항은 `fix/e2e-integration-signup-and-worker-deps` PR(base: `codex/e2e-integration`)로 올렸음. 이 과정에서 `tests/test_prototype.py`의 `test_frontend_uses_current_backend_signup_profile_and_prediction_contract`가 옛날(버그 있던) `/users/me` 계약을 "정답"으로 고정해둔 것도 함께 발견해 `/users/me/profile` 기준으로 수정 — CI 통과 확인. `codex/e2e-integration` 브랜치로의 최종 병합만 남음.

## 4. '당근의 숲' 게임팩 백엔드 연동 — 팀 계획상 의도된 미완성 상태

- `forest-game.js`는 실제 API를 호출하는 `ApiForestAdapter` 클래스를 정의만 해두고, 실제로는 `DemoForestAdapter`(로컬 브라우저 저장소 전용)만 사용하도록 고정되어 있음. 퀘스트·보상·아바타 저장이 전부 로컬에만 남고 서버로 전송되지 않음.
- 로그인 토큰이 메모리에만 있고 어디에도 영속화되지 않아, 메인 페이지 → 당근의 숲 페이지 이동 시 인증 정보 자체가 소실됨 — 현재 구조로는 실제 연동이 불가능한 상태.
- "내 생활습관 지도" 검색(RAG)도 로컬 키워드 매칭(`ragGuideFor`)만 동작하고, 실제 백엔드 `/health-education/questions`(`src/rag/engine.py`)는 호출하지 않음.
- 이는 4회차 멘토링 사전보고서 3-3항에 이미 "실제 검색·생성 API 연동은 남아 있습니다"로 명시된 **의도된 진행 상태**이며, 오늘 작업 중 발견했지만 팀 계획에 따라 별도 요청 전까지 손대지 않기로 함.

## 전체 요약: 배포 전 남은 과제

1. `fix/e2e-integration-signup-and-worker-deps` PR을 `codex/e2e-integration`에 병합
2. 당근의 숲 실제 API 연동 (어댑터 전환 + 토큰 영속화) — 멘토링 이후 착수 예정
3. `main`/`develop` 최종 병합 전 전체 실제 모델·GPS·외부 API 흐름 재검증

**완료된 항목**
- PR #32 (의료기관·응급실 검색): 리뷰 반영 → 재검토 → CI 통과 → 통합 완료
