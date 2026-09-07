# 완료 기준 1 — 주요 화면별 API와 필요 필드

대상: 9/7 로컬 통합 화면 `http://127.0.0.1:8022/`  
기준 코드: 프론트 PR #23 커밋 `a9a0d29`, 통합 로컬 코드 `codex/s2-api002`  
공통 API prefix: `/api/v1`

상태 표기:

- **연결·검증:** 8022에서 실제 HTTP 또는 실제 전체 흐름으로 확인함.
- **화면 구현:** 프론트 화면·상태 처리는 구현했지만 실제 서버의 모든 예외까지 확인한 것은 아님.
- **계약 필요:** API·필드·정책이 없거나 확정되지 않아 백엔드 협의가 필요함.

## 1. 시작 화면

| 구분 | 내용 |
|---|---|
| 화면 기능 | 서비스 소개, 로그인, 회원가입 진입 |
| API | 없음 |
| 필요 필드 | 없음 |
| 다음 화면 | 회원가입 또는 로그인 |
| 상태 | **연결·검증** — 로그인·회원가입 버튼과 소개 화면 이동 확인 |

## 2. 회원가입·로그인

### 회원가입

| API | Method | 전송 필드 | 필수 응답 | 상태 |
|---|---|---|---|---|
| `/auth/signup` | POST | 실제 서버 계약: `email`, `password`, `terms_agreed` | `user_id`, `email`, `created_at` | **연결·검증** |
| `/auth/login` | POST | `email`, `password` | `access_token`; refresh token은 쿠키 | **연결·검증** |
| `/users/me/profile` | PATCH | `birthday`, `gender` | 사용자 프로필 | **연결·검증** |
| `/consents` | POST | `consent_item="health_data"`, `version="1.0"`, `is_agreed=true` | 동의 식별자·저장 상태 | **연결·검증** |

프론트 회원가입 폼에는 `email`, `password`, `birth_date`, `gender`, 서비스 약관 동의, 건강정보 처리 동의가 있다. 현재 프론트는 `/auth/signup` JSON에 `birth_date`, `gender`도 함께 넣지만, 실행 중인 `SignUpRequest`의 정식 필드는 `email`, `password`, `terms_agreed`뿐이다. 생년월일·성별은 가입 후 `/users/me/profile`에 다시 저장한다.

검증 규칙:

- 이메일: 유효한 이메일, 서버 스키마 최대 40자.
- 비밀번호: 8자 이상, 영문 대문자·소문자·숫자·특수문자 누락을 프론트가 항목별 표시. 서버가 최종 검증.
- 서비스 약관 미동의: 가입 요청 차단.
- 건강정보 처리 미동의: 개인화 흐름 진입 차단 및 동의 필요 안내.
- 만 14세 미만: 가입 화면에서 사전 차단. 서버는 현재 프로필 저장 시에도 검사함.

### 로그인·계정 복구

| API | Method | 목적 |
|---|---|---|
| `/auth/login` | POST | 로그인 |
| `/users/me` | GET | 프로필 복원 |
| `/consents` | GET | 건강정보 동의 복원 |
| `/eligibility-checks/latest` | GET | 최근 이용 대상·안전 분기 복원 |
| `/health-checkups` | GET | 건강정보 보유 여부 및 저장 이력 확인 |
| `/challenge-cycles/current` | GET | 진행 중 챌린지 확인 |

가입만 성공하고 자동 로그인·프로필·동의 중 일부가 실패하면 새 계정을 다시 만들지 않고 실패 단계부터 재시도한다. **화면 구현 및 제어 응답 7종 검증 완료**.

## 3. 이용 대상·안전 확인

| API | Method | 요청 필드 | 주요 응답 필드 | 상태 |
|---|---|---|---|---|
| `/users/me/profile` | PATCH | `birthday`, `gender` | 사용자 프로필 | **연결·검증** |
| `/eligibility-checks` | POST | `birth_date`, `has_diabetes_diagnosis`, `has_urgent_warning_sign`, `population_in_scope` | `age`, `reason_codes`, `next_action`, `challenge_eligible`, `current_health_check_eligible`, `future_prediction_eligible`, `model_eligible`, `active_model` | **연결·검증** |

중요한 현재 동작:

- 긴급·당일 진료 증상은 프론트 설문에서 먼저 차단하므로 일반 제출 시 `has_urgent_warning_sign=false`가 전송된다.
- 긴급 증상과 기진단은 실제 서버 응답에서도 현재 건강 확인·미래 예측·챌린지가 모두 차단됨을 확인했다.
- 당일 진료 필요 여부는 실행 중인 `EligibilityCreateRequest`에 별도 저장 필드가 없어 **계약 필요**.
- 현재 코드 응답 기준: 14~18세 챌린지만 가능, 19~44세 현재 건강 확인+챌린지, 45~105세 현재+미래+챌린지, 106세 미래 예측 제외. 팀의 최종 의료·모델 정책 승인은 별도다.
- 정확히 만 14세가 되는 생일 당일 프로필 저장은 현재 422라서 **경계 수정 필요**.

## 4. 건강정보 입력

건강정보 화면은 `기본 정보 → 생활습관 입력 → 세부 건강정보 → 입력 내용 확인` 순서다.

### 기본·생활습관 저장

| API | Method | 필드 | 상태 |
|---|---|---|---|
| `/health-checkups` | POST | 아래 표 참조 | **연결·검증** |
| `/health-checkups` | GET | 없음 | 저장 이력 복원 **연결·검증** |

`POST /health-checkups` 요청:

| 영역 | 필드 | 필수/처리 |
|---|---|---|
| 기록 | `checkup_type` | 최초 `initial`, 수정·재분석 `reassessment` |
| 기록 | `checkup_date` | `YYYY-MM-DD` |
| 신체 | `height_cm`, `weight_kg` | 필수 |
| 신체 | `waist_cm`, `systolic_bp`, `diastolic_bp` | 선택, 모르면 `null` |
| 생활습관 | `self_rated_health` | 필수 |
| 생활습관 | `meal_count_yesterday` | 필수, 0~10 |
| 생활습관 | `smoking_status` | `never/former/current` |
| 생활습관 | `current_smoker` | 흡연 상태에서 파생 |
| 생활습관 | `current_drinker` | 필수 선택 |
| 운동 | `regular_exercise` | 필수 선택 |
| 운동 | `exercise_days_per_week`, `exercise_minutes` | 운동 안 함이면 0, 운동함이면 입력 |

### 세부 건강정보 스냅샷

| API | Method | 필드 | 상태 |
|---|---|---|---|
| `/current-screening-inputs` | POST | `health_checkup_id`, `input_as_of_date`, 아래 세부 필드 | **계약 필요 — 현재 OpenAPI에 없고 404** |

세부 필드: `walking_days`, `energy_kcal`, `protein_g`, `fat_g`, `carbohydrate_g`, `sodium_mg`, `region`, `urban`, `education`, `income_quartile`, `household_income_quartile`, `hypertension_family_history`, `diabetes_family_history`, `alcohol_frequency`.

프론트는 이 API가 404/405/501이면 분석 전체를 거짓 성공으로 만들지 않고 “세부 건강정보 저장 연결 준비 중”으로 구분한다. 최종 모델 입력이 확정되지 않았으므로 기존 세부 항목 삭제는 보류한다.

## 5. 분석 대기

| API | Method | 요청/조회 | 상태 |
|---|---|---|---|
| `/prediction-jobs` | POST | `checkup_id`, `model_key`, 오늘이일 때 제공 가능하면 `current_screening_input_id` | **연결·검증** |
| `/prediction-jobs/{job_id}` | GET 반복 조회 | `status`, `prediction_id`, 오류 정보, 모델 메타데이터 | **연결·검증** |
| `/predictions/{prediction_id}` | GET | 모델 결과·표시 승인·메타데이터 | **연결·검증** |
| `/predictions/{prediction_id}/risk-factors` | GET | 미래 결과 설명·위험요인 | **연결·검증**, 공개 승인 없으면 화면 차단 |

`model_key`:

- 오늘이: `diabetes_current_screening`
- 내일이: `diabetes_incidence`
- 모레노: 연구용이며 MVP에서 호출하지 않음

작업 상태 UI:

- `queued`: 요청 접수·대기
- `running`: 분석 중
- `succeeded`: 결과 화면 이동
- `failed`: 실패 코드와 재시도 버튼
- 제한 시간 초과: 입력을 유지하고 같은 모델만 다시 확인

실제 8022에서는 오늘이와 내일이 작업이 모두 `succeeded`까지 완료됨을 확인했다. 큐 복구는 로컬 전용 워커 기준이며 PR #23만으로 재현되지는 않는다.

## 6. 결과 — 오늘이·내일이·모레노 분리

| 결과 영역 | 모델 | 화면 표시 | 필수 응답·보호 조건 |
|---|---|---|---|
| 오늘이 — 현재 위험 신호 선별 | `diabetes_current_screening` | 별도 신호등/결과 카드 | `model_key`, `task_type`, `model_version`, `threshold_scope`, `threshold_version`, `display_allowed`, `operational_model_activated`, 위험 범주 |
| 내일이 — 미래 신규 발병 위험 | `diabetes_incidence` | 오늘이와 분리된 결과 카드 | 같은 메타데이터, `signal_level` 또는 승인된 범주. 오늘이와 평균·합산 금지 |
| 모레노 — 미래 전망 연구 모델 | 연구용 | **MVP 화면·API 호출에서 제외** | 연구 결과를 운영 결과처럼 대체 표시하지 않음 |

표시 원칙:

- `low/caution/high`는 `낮음/주의/높음`으로만 번역한다.
- 오늘이·내일이는 서로 다른 과제이므로 하나의 확률로 합치지 않는다.
- `display_allowed=false` 또는 `operational_model_activated=false`이면 수치·확률·위험요인을 공개하지 않는다.
- 연구·운영 미승인 및 진단 아님 안내를 함께 표시한다.
- `cumulative_risk_signal`을 개인의 확정 발병확률처럼 표현하지 않는다.
- 생존 곡선·2/4/6년 그래프는 모레노 MVP 제외 및 별도 안전 승인 전까지 표시하지 않는다.
- 한 모델만 실패하면 성공한 모델은 유지하고 실패한 모델만 재시도한다.
- 두 모델 모두 실패하면 입력을 보존한 실패 화면을 표시한다.

실제 E2E 결과: 오늘이 `knhanes-shared7-sk180-research-v1`, 내일이 `rf25-first-interval-survival-ensemble-v1` 각각 성공. 두 결과 모두 `display_allowed=false`, `operational_model_activated=false` 유지 확인.

## 7. 챌린지

| API | Method | 필드/용도 | 상태 |
|---|---|---|---|
| `/challenge-recommendations?prediction_id={id}` | GET | 허용된 예측 결과 기반 추천 | **연결·검증** |
| `/challenges` | GET | 전체 챌린지 목록 | **연결·검증** |
| `/follow-up-actions` | GET | 의료 안내 선확인 필요 여부 | **화면 구현** |
| `/follow-up-actions/{action_id}/acknowledge` | PATCH | 의료 안내 확인 처리 | **화면 구현** |
| `/challenge-cycles` | POST | `start_date`, `challenge_ids`, `prediction_id` | **연결·검증** |
| `/challenge-cycles/current` | GET | 이미 진행 중인 사이클 복원 | **연결·검증** |

목록 로딩·빈 결과·실패·재시도 UI가 있다. 추천 API와 전체 목록 API 중 요청이 실패하면 실패 안내와 “다시 시도”를 표시한다. 진행 중 사이클 409이면 새로 만들지 않고 현재 사이클을 불러와 대시보드로 이동한다.

## 8. 대시보드·기록·리포트

| 화면 | API | Method | 상태 |
|---|---|---|---|
| 홈 요약 | `/dashboard/summary` | GET | **연결·검증** |
| 챌린지 진행 | `/dashboard/challenge-progress` | GET | **연결·검증** |
| 오늘 기록 조회 | `/user-challenges/{id}/logs?start_date&end_date` | GET | **연결·검증** |
| 오늘 기록 저장 | `/user-challenges/{id}/logs/{date}` | PUT | **연결·검증** |
| 건강정보 관리 | `/health-checkups` | GET | **연결·검증** |
| 주간 리포트 | `/weekly-reports/current` | GET | **연결·검증** |
| 이번 주 PDF | `/weekly-reports/current/pdf` | GET | **연결·검증** |
| 4주·전체 PDF | 미정 | 미정 | **계약 필요** |

PDF 실제 검수 결과: A4 1페이지, 생활습관 요약과 비진단 안내 포함, 승인 전 모델 확률·위험요인 없음. 긴 문장이 오른쪽에서 잘려 백엔드 PDF 줄바꿈 보완이 필요하다.

## 완료 판정

- [x] 시작·가입·건강정보·분석·결과·챌린지·대시보드의 호출 API와 필드를 표시함.
- [x] 오늘이·내일이 결과를 분리하고 모레노의 MVP 제외 위치를 표시함.
- [x] 로딩·빈 결과·실패·재시도 상태를 화면별로 명시함.
- [ ] 세부 입력 스냅샷, 당일 진료 분기, 4주·전체 PDF는 백엔드 계약 후 최종 완료 가능.

