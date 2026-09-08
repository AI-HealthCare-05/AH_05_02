# 9/7 프론트 UI/UX 1차 수정 및 사용자 흐름 점검

> 후속 전체 흐름 점검은 [오늘 우선순위 체크리스트](DAILY_PRIORITY_CHECKLIST_20260907.md)를 참고한다. 아래는 최초 점검 기록이며, 이후 실제 로컬 API 8단계·브라우저 16개·단위 14개가 통과했다. 기존 integration_refresh 실패도 현재 단위 테스트 재실행에서는 해결됐다. 추가 스냅샷 API404와 정책·후반 QA 미완료 항목은 계속 남아 있다.

## 후속 수정: 비로그인 헤더 오른쪽 정렬

- 가이드 3-1의 미반영 항목을 보완: 로고는 왼쪽, 로그인 → 회원가입은 오른쪽으로 이동했다.
- 로그인은 텍스트 버튼, 회원가입은 초록색 주 버튼으로 위계를 구분했다. 글자 크게는 유지한다.
- 760px 이하에서는 로그인·회원가입이 두 번째 줄 오른쪽에 모이며, 기존 로그인 후 5개 탭은 변경하지 않았다.
- `tests/frontend/guest_header_qa.cjs` 실제 브라우저 검증: 1440/1024/760/380/320px에서 오른쪽 정렬, 두 버튼 최소 높이 48px, 가입·로그인 폼 이동, 글자 크게 상태의 가로 넘침 없음 확인. 로그인 후 메뉴 전환 및 JS 오류 없음도 확인했다.
- 증거: `tmp/guest-header-qa/header-1440.png`, `header-380.png`.
- 이번 후속 작업은 헤더 배치에 한정하며, 아래에 남긴 전체 가이드 미완료 항목의 완료를 의미하지 않는다.

## 범위와 증거

- 대상: `AH_05_02-s2-api002/src/frontend`, 로컬 서버 `http://127.0.0.1:8022/`.
- 참고: 원본 `AH_05_02/docs/frontend/UI_UX_IMPLEMENTATION_GUIDE.md`, 안전 문구, REQUIREMENTS, API_SPEC 및 현재 백엔드 라우터/DTO.
- 목적: 사용자가 가입하고 정보를 입력한 뒤 결과와 다음 행동을 이해하며, 실패해도 입력을 잃지 않고 다시 시도할 수 있게 한다.
- 기존 사용자 결정인 넓은 작업 화면, 로그인 후 5개 탭, 랜딩 캐릭터 구성은 유지한다. 인증 폼만 가독성을 위해 중앙 단일 열로 제한했다.
- GitHub 변경·PR 승인/병합·배포 없음. 진행 중인 모델·백엔드 변경은 수정하지 않았다.
- **실제 로컬 HTTP/DB 흐름 점검과 모델의 실제 추론·운영 승인 검증은 다르다.** 이번 E2E는 실행 중인 8022 로컬 DEMO 환경 기준이다.

## 반영한 수정

- [x] 가입·로그인 폼 단일 열, 모바일 주 버튼 전체 폭.
- [x] 비밀번호 보기/숨기기와 실제 백엔드의 8자 이상·대소문자·숫자·특수문자 조건 안내.
- [x] 인증 오류의 읽기 쉬운 요약, 필드별 오류 연결, 오류 후 입력값 보존, 요약으로 키보드 초점 이동.
- [x] 가입 후 프로필 저장, 이용 가능 확인 전 프로필 저장, 프로필 편집을 `PATCH /users/me/profile`로 수정. 종전 `PATCH /users/me`는 실제 405였다.
- [x] 건강정보 오류 개수 표시 및 첫 오류 항목이 있는 패널로 이동·초점 배치. 걷기 일수 등 이동된 항목도 실제 DOM 위치를 따른다.
- [x] 현재 신호만 확인하는 사용자도 저장 → 분석 → 결과로 이동. 미래 모델은 요청하지 않는다.
- [x] 결과 화면 진입 때 실제 현재 모델 응답이 건강정보 저장 응답으로 덮어써지는 문제 수정.
- [x] 현재 위험 신호등과 미래 신규 발병 위험을 각각 해당 모델 응답으로 표시. 미래 값으로 현재 결과를 대체하지 않는다.
- [x] 공개 가능한 현재 결과의 low/caution/high를 낮음/주의/높음으로 표시.
- [x] 미래 위험이 높아도 현재 신호등을 바꾸지 않으면서 검사·상담 안내를 먼저 제공.
- [x] 미래 전망 응답이 null인 경우 그래프를 숨기고 준비 안내 유지; 화면 예외 방지.
- [x] 추가 세부 건강정보 저장 API 미지원 시 저장·분석되지 않았음을 결과 화면에서 알림. 이전 스냅샷 ID 재사용 방지.
- [x] 챌린지 1~3개 선택 규칙·선택 개수 상시 표시, 목록 실패 시 다시 불러오기 버튼.
- [x] 좁은 모바일 운동 입력 3개를 세로로 배치하여 필드 폭 확보.
- [x] 현재 메뉴의 밑줄·배경, 키보드 포커스 대비, 모션 줄이기 설정 반영.

## 화면별 API 매핑

아래 경로의 공통 접두사는 `/api/v1`이다. API 코드는 사용자 UI에 직접 노출하지 않는다.

| 화면 | 호출 | 필요한 요청/응답 필드 | 정상 다음 행동 | 예외·현재 상태 |
|---|---|---|---|---|
| 시작 | API 없음 | 비로그인/로그인 상태 | 가입 또는 로그인 | 기존 헤더 유지 |
| 가입 | POST `/auth/signup` | email, password, terms_agreed → user_id | 자동 로그인 | 422 입력 수정, 409 기존 계정 로그인 |
| 로그인 | POST `/auth/login`, GET `/users/me` | email, password → access_token; birthday, gender | 동의·이력 확인 | 인증 실패 시 폼 유지 |
| 프로필 저장 | PATCH `/users/me/profile` | birthday, gender | 동의 또는 이용 대상 확인 | **실제 405 수정 후 200 확인** |
| 건강정보 동의 | POST/GET `/consents` | consent_item=health_data, version, is_agreed; items, withdrawn_at | 이용 대상 확인 | 미동의/철회 안내; 보유기간·철회 설명 보완 필요 |
| 이용 대상 확인 | POST `/eligibility-checks`, GET `/eligibility-checks/latest` | birth_date, has_diabetes_diagnosis, has_urgent_warning_sign, population_in_scope → model_eligible, reason_codes, capability 필드 | 기본정보 입력 | 기진단·응급·연령 범위 안내 |
| 기본·생활습관 저장 | POST `/health-checkups`, GET `/health-checkups` | checkup_type/date, height_cm, weight_kg, waist_cm, systolic_bp, diastolic_bp, self_rated_health, meal_count_yesterday, smoking_status, regular_exercise, current_drinker, exercise_days_per_week/minutes → checkup_id | 분석 요청 | 범위 오류 시 입력 수정. 공복혈당 등 모든 화면 항목이 전송되는 것은 아님 |
| 세부 건강정보 | POST `/current-screening-inputs` | health_checkup_id, input_as_of_date, 모델별 추가 입력 → snapshot ID | 현재 모델 요청에 스냅샷 참조 | **8022 실제 404. 저장 완료로 간주하지 않음** |
| 분석 상태 | POST `/prediction-jobs`, GET `/prediction-jobs/{job_id}` | checkup_id, model_key → job_id, status, prediction_id/error | 성공 후 결과 | queued/running 유지, failed/timeout 시 재시도; 입력 유지 |
| 현재 위험 신호 선별 | GET `/predictions/{id}` | model_key=diabetes_current_screening, display/result/promotion 상태, risk_category, 모델 메타데이터 | 안전 안내 후 챌린지 | 미승인·응답 없음은 준비 안내. 미래 결과로 대체 금지 |
| 미래 신규 발병 위험 | 동일 prediction API | model_key=diabetes_incidence; 별도 prediction_id와 공개 상태 | 별도 미래 범주 표시 | 현재 점수와 평균/합산하지 않음 |
| 미래 위험 전망 | 백엔드: POST `/prediction-jobs`의 diabetes_lifetime_risk + prediction_type=survival_curve | 승인, risk_curve_status, lower/upper, calibration, 모델 메타데이터 | 승인된 전망만 그래프 | **현재 프론트 runPrediction은 lifetime 별도 작업을 요청하지 않음. 독립 연결 후 검증 필요** |
| 챌린지 선택 | GET `/challenges`, GET `/challenge-recommendations` | prediction_id는 정수 또는 없음; items, personalized, medical_guidance_required_first | 최대 3개 선택 | 실패 시 목록 재요청. 맞춤 후보 생성은 로컬 초안이며 저장 API 미연결 |
| 챌린지 시작 | POST `/challenge-cycles` | start_date, challenge_ids, prediction_id → cycle, user_challenges | 대시보드 | 409 진행 중 사이클을 불러옴; 의료 안내 우선 |
| 오늘 기록 | PUT `/user-challenges/{id}/logs/{date}` | completed 등 기록 DTO | 기록 표시 갱신 | API 실패 후 재시도 필요 |
| 홈 | GET `/dashboard/summary`, `/dashboard/challenge-progress`, `/health-checkups`, `/challenge-cycles/current` | 오늘 기록·활성 사이클·건강 이력 | 오늘 실천 기록 | 건강정보 없음과 기존 기록 있음의 로그인 진입 분리 확인 |
| 리포트 | GET `/weekly-reports/current`; PDF `/weekly-reports/current/pdf?...` | period, status, 기록 항목; 선택 기간 | 생활습관 기록 요약·PDF | 이번 실행은 리포트 조회 200까지만 확인. 지난4주/전체 집계 및 PDF 본문 재검증 필요 |
| 함께하기 | GET `/connections`, `/shared-challenge-groups`; 숲 `/forest` | 연결·공유 그룹·숲 상태 | 공유/숲 하위 기능 | 별도 E2E 예정 |
| 건강도구·의료기관 | `/medical-facilities/nearby`, `/emergency-facilities/nearby`, `/health-education/questions` 등 | 위치 또는 질문; 기관/출처/상태 | 안내 확인 | 권한 거부·시간초과·빈 결과·실패 모두 후속 점검 |

모델별 추적 필드: model_key, task_type, model_version, threshold_scope, threshold_version를 `modelOutputMetadata`에 받아 유지한다. 이것은 서버 영구 저장 검증을 대신하지 않는다.

## 정상·예외 사용자 이동표

| 조건 | 이동/표시 | 이번 검증 수준 |
|---|---|---|
| 신규 가입 성인 | 가입 → 자동 로그인 → 프로필/동의 → 이용 대상 → 기본 → 생활습관 → 세부 → 확인 → 분석 → 결과 → 챌린지 → 홈 | 실제 8022 API 흐름 통과 |
| 건강정보 없는 기존 계정 | 로그인 → 이용 대상 확인/입력 안내 | 새 브라우저 실제 로그인 통과 |
| 건강정보·챌린지 있는 계정 | 로그인 → 홈 | 새 브라우저 실제 로그인 통과 |
| 현재 모델만 가능한 사용자 | 건강정보 저장 → 현재 모델만 분석 → 현재 결과 | 브라우저 제어 응답 테스트 및 백엔드 통합 테스트; 실제 입력 연령 경계 전체 QA는 남음 |
| 잘못된 로그인/가입 입력 | 값 유지 + 폼 오류, 재입력 | 브라우저 401·422 제어 응답 통과 |
| 건강정보 범위 오류 | 오류 개수 + 해당 패널·첫 오류 초점 | 걷기 일수 8 입력 브라우저 검증 통과 |
| 분석 실패/시간초과 | 결과로 자동 이동하지 않고 다시 시도 | 코드 확인; 실제 모델 장애 유발 E2E는 미실시 |
| 현재 낮음 / 미래 높음 | 현재 낮음 유지, 미래 높음 별도, 검사·상담 우선 | 브라우저 제어 응답 통과 |
| 현재 결과 없음 / 미래 결과 있음 | 현재 준비 중 유지 | 브라우저 제어 응답 통과 |
| 미승인/전망 null | 숫자·곡선 숨김, 준비 안내 | 브라우저·단위 테스트 통과 |
| 챌린지 목록 실패 | 시작 비활성 + 목록 다시 불러오기 → 선택 복구 | 브라우저 503→200 통과 |
| 기진단/응급/당일 진료/미동의/연령 밖 | 기존 안내 팝업과 허용 기능만 제공 | 코드 점검; 각 팝업·뒤로·키보드·실제 서버 분기는 후속 QA |

## 실행한 테스트

- `node --check src/frontend/app.js`, `git diff --check` 통과.
- `node --test tests/frontend/*.test.cjs`: 프론트 단위 테스트 49개 통과.
- `tests/frontend/ui_ux_qa.cjs`: 19개 브라우저 확인 통과(제어 API 응답 사용, 모델 성능 검증 아님).
- `tests/frontend/local_flow_smoke.cjs`: 실제 로컬 HTTP E2E 7개 단계 통과. 첫 실행의 프로필 405를 발견·수정한 뒤 재실행했다. 로컬 가상 계정이 생성되며 운영 계정/개인정보는 사용하지 않는다.
- pytest: `test_s2_api002_contract.py`, `backend/test_prediction_job_contract.py`, `test_research_model_api.py`, `test_dual_model_integration.py`, `test_frontend_integration_runtime.py::test_current_result_and_medical_guidance_are_not_hidden_with_future_results`: 20개 통과.
- 기존 내부 가칭을 요구하던 HTML 테스트는 현재 사용자용 명칭과 모델별 영역을 검증하도록 수정했다.
- `tests/frontend/integration_refresh.test.cjs`를 현재 모델 분리·모레노 제외 정책에 맞춰 재정합했으며 8개 테스트가 통과한다.
- MySQL 연결이 필요 없는 Pytest 전체 범위는 352개 통과, 4개 건너뜀이다. MySQL 기반 전체 CI는 GitHub Actions에서 최종 확인한다.
- 가입 복구, 안전 분기 6종, 홈 내비게이션, 챌린지 토글, 리포트 기간, 비밀번호 아이콘, 서비스 소개, 당근의 숲 진입 브라우저 QA가 통과했다.
- 스크린샷/응답 상태 증거: 로컬 `tmp/ui-ux-qa/`의 `results.json`, `live-flow.json`, 각 PNG. 테스트 파일에 실제 비밀번호/토큰 응답을 기록하지 않는다.

## 다음 우선순위 — 완료로 체크하지 않은 항목

1. **세부 입력 계약**: 22입력 스냅샷 API와 현재 shared7 모델 계약의 관계 확정. 프론트 추가 항목이 실제 저장·추론 입력에 반영되는지 비교한다. 공복혈당 입력 미전송 및 교육 코드 매핑도 확인한다. 누락값을 임의 0으로 바꾸지 않는다.
2. **실제 모델 검증**: 최신 백엔드·워커·artifact 버전과 요청 ID를 함께 추적하여 DEMO가 아닌 현재/미래/생존 모델을 각각 검증한다. 공개 승인 플래그는 임의 true로 바꾸지 않는다.
3. **안전 정책 정합**: 안전 문서는 19세, 기존 사용자 요청·프로필 검증 코드는 14세를 사용한다. 정확히 만14세가 되는 날의 경계(`birthday < today - 14 years`)도 현재 문구와 불일치 가능성이 있다. 임의 연령 정책 변경 없이 담당자 확인 후 프론트·백엔드·문서를 통일한다.
4. **동의**: 목적·항목·보유기간·철회 방법의 확정 내용과 상세 열람/철회 진입 경로를 연결한다. 운영 보유기간은 임의로 작성하지 않는다.
5. **예외 흐름**: 6종 안전 팝업(14세 미만, 모델 연령 밖, 응급, 당일 진료, 기진단, 미동의)의 열기·닫기·초점 복원·API 요청 차단을 각각 E2E로 확인한다.
6. **후반 화면 QA**: 리포트 3기간 집계/PDF, 일일 기록, 함께하기·숲, 건강도구 및 지도 실패 상태. 모바일 글자 크게·전체 키보드 흐름·모든 색 대비는 아직 전체 통과 판정을 하지 않는다.

## 테스트 재실행

Playwright가 설치된 환경에서 `PLAYWRIGHT_MODULE`(필요 시), `CHROME_BIN`(필요 시)을 지정한다.

```sh
node --test tests/frontend/ui_ux_rules.test.cjs
node tests/frontend/ui_ux_qa.cjs
# 주의: 아래는 로컬 DB에 가상 QA 계정/건강정보/챌린지 사이클을 생성한다.
node tests/frontend/local_flow_smoke.cjs
```

두 브라우저 스크립트는 localhost/127.0.0.1만 허용한다. 기본 URL은 8022이며 `QA_BASE_URL`로 다른 로컬 서버를 지정할 수 있다.

## PR #23 재구성 기준

- 기존 PR #23의 원격 커밋 `a9a0d29`는 `codex/backup-pr23-a9a0d29` 브랜치로 보존했다.
- PR #23은 `codex/e2e-integration`을 기준으로 하는 PR #36의 최신 커밋 `17c0a20`을 선행 이력으로 사용한다.
- PR #36의 모델·워커·API 코드는 수정하지 않고, 그 위에 프론트 UI·접근성·예외 처리와 관련 테스트만 한 커밋으로 정리했다.
- 이전 PR #23에 섞여 있던 PDF 생성, 폰트, 백엔드 서비스, 의존성 변경은 프론트 변경 묶음에서 제외했다.
- PR #36을 먼저 병합하면 동일 선행 커밋은 PR #23 비교 화면에서 자동으로 빠지고 프론트 변경만 남는다.
