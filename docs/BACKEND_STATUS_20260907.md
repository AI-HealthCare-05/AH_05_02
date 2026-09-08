# 데일리 백엔드 상태 정리 (9월 7일)

**(9/7 업데이트) 모레노는 이번 MVP 범위에서 제외하기로 팀 결정됨 — 아래 표/점검 스크립트에 남아있는 모레노 관련 항목은 참고용이며 이번 MVP 완료 기준에는 포함하지 않습니다.**


**(9/7 정정) git worktree 관련 — 실제로는 문제 없었음.** 오전에 이 폴더에서 git 명령이 실패한다고 알렸었는데, 확인해보니 원격 점검 도구가 폴더를 마운트하는 방식 때문에 생긴 착시였고 실제 저장소·워크트리 연결은 정상입니다. Finder/터미널에서 직접 이 폴더를 여시면 `git status`가 정상 동작할 것으로 예상됩니다.
## 0. 팀 공통 연동표 대응 현황

빛샘님 공유 연동표(회원가입 / 사용자 정보 / 오늘이 / 내일이 / 모레노 / 고위험 안내 / 응급 안내 / 챌린지 / 대시보드)에 맞춰 정리한 상태입니다. `scripts/api-smoke-test.sh`로 로컬 서버(`docker compose up -d`)에 실제 요청을 보내 9/7에 전 항목 라이브로 검증 완료했습니다(코드만 읽고 판단한 게 아니라 실제 응답 확인함).

| 흐름 | BE/API | 오늘 상태 |
|---|---|---|
| 회원가입 | `/auth/signup`, `/auth/login` | **완료** — signup 201, login 토큰 발급 정상. `terms_agreed` DB 미저장 버그(1번 항목)도 오늘 수정 완료: `User` 모델에 `terms_agreed`/`terms_agreed_at` 컬럼 추가 + 마이그레이션(`19_20260907120000_user_terms_agreed.py`) + `AuthService.signup()` 연결. `docker compose restart fastapi`로 마이그레이션 적용 후 실제 회원가입→DB 조회로 `terms_agreed=1`, `terms_agreed_at` 시각 저장까지 라이브 확인 완료 |
| 사용자 정보 | `/users/me/profile`, 검진 API | 라이브 검증 완료 — 프로필 저장/조회 정상 |
| 오늘이 | 예측 생성·상태·결과 API | 라이브 검증 완료 — job queued→succeeded, 예측 결과 정상 생성 |
| 내일이 | 예측 생성·상태·결과 API | 라이브 및 브라우저 검증 완료 — `age_risk_forecast.points`마다 `signal_level`(high/caution/low)이 정상적으로 붙고, 결과 화면에 2·4·6년 전망이 표시됨. `scenarios`/`uncertainty`는 이번 MVP 범위 제외로 팀 결정(9/7) — 화면에서도 숨김 처리 완료 |
| 모레노 | 전망 결과 API | **이번 MVP 범위 제외 결정** (9/7 팀 확정). 라이브 확인상 여전히 503 `MODEL_NOT_READY`로 안전하게 막혀 있음 (의도된 동작) |
| 고위험 안내 | 의료기관 검색 API | 라이브 검증 완료 — 실제 카카오 API 호출로 서울 시내 병원 15곳(이름/주소/전화/거리) 정상 반환, `data_source: kakao_local_api_keyword_diabetes` 확인 |
| 응급 안내 | 응급실 검색 API | 라이브 검증 완료 — 응급 신호 '예' 제출 시 `next_action: urgent_medical_guidance`로 정상 전환, NEMC 응급실 검색도 실제 데이터(강북삼성병원 등) 정상 반환 |
| 챌린지 | 챌린지 API | 라이브 검증 완료 — 목록/추천, 사이클 생성, 일일 기록 생성·수정·조회 정상. 같은 날짜 재요청은 기존 기록을 수정하고 미래 날짜는 422로 차단됨. 추천이 `rule_based_reviewed_template`인 것은 팀 결정(`REQ-RECO-001`/`DEC-008`, 8/18 확정 — Sprint2는 템플릿만, RAG 개인화는 후순위)과 일치함 — 문제 아님 |
| 대시보드 | 대시보드 API | 라이브 검증 완료 — 위험 카드, 다음 액션(고위험이라 "의료기관 확인 우선" 안내) 정상 반영 |



## 1. 회원가입 `terms_agreed` 포함 여부 · 프로필 저장 순서 — **수정 완료 (9/7)**

- `POST /auth/signup` 요청 DTO(`SignUpRequest`)는 `email`, `password`, `terms_agreed` 세 필드만 받고, `terms_agreed`는 `field_validator`로 `True`가 아니면 422 에러를 던지도록 검증합니다.
- **원래 문제**: 검증만 하고 값 자체는 저장하지 않았습니다 (`User` 모델에 컬럼 자체가 없었음).
- **수정 내용**:
  - `app/models/users.py`: `User`에 `terms_agreed`(bool, default False), `terms_agreed_at`(datetime, null 허용) 컬럼 추가
  - `app/core/db/migrations/models/19_20260907120000_user_terms_agreed.py`: 위 두 컬럼 추가하는 마이그레이션 신규 작성
  - `app/repositories/user_repository.py`: `create_user()`가 `terms_agreed`/`terms_agreed_at`를 받아 저장하도록 수정
  - `app/services/auth.py`: `AuthService.signup()`이 `data.terms_agreed`와 가입 시각을 실제로 전달하도록 수정
  - `tests/backend/api/auth_apis/test_signup_api.py`: 회귀 방지 테스트 `test_signup_persists_terms_agreed` 추가
- **라이브 검증 완료**: `docker compose restart fastapi`로 마이그레이션 적용 → `SHOW COLUMNS`로 컬럼 생성 확인 → 신규 회원가입 후 DB 조회로 `terms_agreed=1`, `terms_agreed_at`에 실제 시각 저장 확인함.
- 프로필(이름/성별/생년월일/키/전화번호)은 회원가입 시점에는 전부 `None`으로 생성되고, 별도 엔드포인트 `PATCH /users/me/profile`(`UserManageService.update_user`)에서 나중에 채워지는 구조입니다. 가입 → 프로필 입력 순서를 API 레벨에서 강제하는 로직(예: "프로필부터 채워야만 다음 단계 호출 가능")은 없습니다.
- **다만 라이브로 확인한 결과, 순서를 안 지켜도 안전합니다 (9/7 검증 완료)**: 프로필을 채우지 않고 바로 `POST /eligibility-checks`를 호출하면 `422` + `"적합성 확인 전에 건강정보 입력 단계에서 생년월일을 등록해 주세요."`로 명확하게 막힙니다. 같은 패턴으로 `POST /health-checkups`도 성별 없으면 `422` + `"예측 전에 프로필 성별을 입력해 주세요."`, 모델 추론 직전(`inference_payload`)에서도 생년월일/성별/흡연상태 등이 비면 `ML_INPUT_MISSING`으로 막혀 `error_detail()` 형식(`"모델 입력 계약을 확인해 주세요."`)으로 응답됩니다. 즉 순서를 강제하는 게이트는 없지만, 각 단계마다 방어 로직이 있어 잘못된 순서로 호출해도 서버 에러나 잘못된 데이터 저장 없이 안전하게 막힙니다. 프론트에서 이 에러 메시지를 사용자에게 잘 보여주는지만 확인하면 될 것 같습니다.

## 2. 건강정보 생성·수정 API

`app/apis/v1/health_routers.py` 기준, CRUD 전부 구현되어 있습니다.

| API | 상태 |
|---|---|
| `POST /health-checkups` (생성) | 완료 |
| `GET /health-checkups` (목록) | 완료 |
| `GET /health-checkups/{id}` (단건) | 완료 |
| `PATCH /health-checkups/{id}` (수정) | 완료 |
| `GET /health-checkups/input-schema` | 완료 (프론트 폼 스키마 제공용) |
| `POST /consents`, `GET /consents`, `PATCH /consents/{id}/withdraw` | 완료 |
| `POST /eligibility-checks`, `GET /eligibility-checks/latest` | 완료 |

요청/응답 예시는 4번 항목 참고.

## 3. 오늘이·내일이·모레노 요청·조회 API 목록

코드에서 "오늘이"는 **현재 위험 신호 선별**(KNHANES, `diabetes_current_screening` 모델), "내일이"는 **약 2년 후 신규 발병 위험**(KLoSA, `diabetes_incidence` 모델)을 가리킵니다.

> **정정**: 처음엔 "모레노는 코드에 아예 없다"고 적었는데, 팀 공유 연동표를 보니 모레노 = "연령별 발병 위험 전망 / 이산시간 생존모델"입니다. 이건 코드에서 `model_key=diabetes_lifetime_risk`, `GET /predictions/{id}/risk-curve`로 이미 스캐폴딩돼 있는 기능과 같은 것으로 보입니다. 이름만 다르고 실체는 있었습니다.

| 구분 | 관련 API | model_key | 상태 |
|---|---|---|---|
| 오늘이 (현재 선별) | `POST /prediction-jobs` (model_key=`diabetes_current_screening`) → `GET /predictions/latest`, `GET /predictions/{id}` | `diabetes_current_screening` | 완료 |
| 내일이 (약 2년 후) | `POST /prediction-jobs` (model_key=`diabetes_incidence`) → `GET /predictions/latest`, `GET /predictions/{id}`, `age_risk_forecast` 필드 | `diabetes_incidence` | 완료 (오늘 `signal_level` 필드 누락 버그 수정함) |
| 모레노 (연령별 발병 위험 전망 / 이산시간 생존모델) | `POST /prediction-jobs` (model_key=`diabetes_lifetime_risk`) → `GET /predictions/{id}/risk-curve` | `diabetes_lifetime_risk` | **이번 MVP 범위 제외 (9/7 팀 결정)** — 어차피 승인된 생존모델이 없어 코드로 완성 불가한 상태였음(`_create_lifetime_risk_job()`이 의도적으로 항상 `ModelNotReadyError`). 지금 코드(항상 501/503 반환)는 그대로 둬도 되고, 이번 MVP 점검·QA 대상에서는 제외. 모델(소유자: 양준혁)이 나오고 다음 스프린트에서 다시 붙일 때 재논의 |

공통 조회: `GET /prediction-jobs/{job_id}` (작업 상태 폴링), `GET /predictions`, `GET /predictions/changes`, `GET /predictions/{id}/risk-factors`(설명 기능은 아직 항상 빈 배열).

## 4. PredictionJob 상태값 · 오류 응답 통일 — **수정 완료 (9/7, 버그 1건 추가 발견 및 수정)**

**상태값 — 통일 완료**: `PredictionJobResponse.status`와 범용 `AIJobResponse.status`(`/ai-jobs` 엔드포인트)는 같은 테이블(`PredictionJob` 모델, `prediction_jobs` 테이블)을 감싸는 두 DTO인데, `AIJobResponse.status`만 `str`(자유 형식)로 느슨했습니다. 실제로 대입되는 값은 `"queued"/"running"/"succeeded"/"failed"` 네 가지뿐이라 `app/dtos/ai_jobs.py`의 타입을 `PredictionJobResponse`와 동일한 `Literal[...]`로 맞췄습니다.

**추가로 발견한 진짜 버그**: 라이브로 `POST /api/v1/ai-jobs`를 호출해보니 404가 나왔습니다. 원인은 `ai_job_router`(`/ai-jobs`)가 `app/apis/v1/__init__.py`의 `v1_routers`에 **include되어 있지 않았던 것** — 즉 코드는 있는데 실제 서버 라우팅에는 연결이 안 돼 있었습니다. `docs/ASYNC_AI_PIPELINE.md`, `docs/BACKEND_DB_CONSOLIDATION.md` 둘 다 `/api/v1/ai-jobs`가 `demo_inference` 등 범용 작업용으로 `/api/v1/prediction-jobs`와 나란히 계속 노출되어야 한다고 문서화돼 있어서, 이건 의도적 폐기가 아니라 등록 누락 버그로 판단했습니다. `app/apis/v1/__init__.py`에 `ai_job_router` import + `v1_routers.include_router(ai_job_router)` 추가해서 고쳤습니다.

(문법 검사는 완료. 이 폴더 쪽 브릿지에는 docker가 없어 라이브 재확인은 못 했습니다 — `docker compose up -d`/`restart fastapi` 후 `POST /api/v1/ai-jobs`로 확인 부탁드립니다.)

**오류 응답 — 통일 완료**: 예측 및 범용 AI 작업 라우터의 자체 오류를 공통 `error_detail()` 헬퍼로 통일했습니다.

```json
{
  "detail": {
    "error_code": "PREDICTION_JOB_NOT_FOUND",
    "message": "예측 작업을 찾을 수 없습니다.",
    "retryable": false
  }
}
```

404 예측 작업·예측 결과 오류는 로컬 API에서 실제 응답까지 확인했습니다. 큐 연결 실패는 `QUEUE_UNAVAILABLE`, 재시도 가능 여부는 `retryable: true`로 반환합니다.

## 5. 챌린지·대시보드·병원 검색 API 구현 상태

| 도메인 | API | 상태 |
|---|---|---|
| 챌린지 | `GET /challenges`, `/challenge-recommendations`, `POST /challenge-cycles`, `GET /challenge-cycles/current`, `GET /challenge-cycles/{id}`, `PATCH /challenge-cycles/{id}/status`, `PUT /user-challenges/{id}/logs/{date}`, `GET /user-challenges/{id}/logs` | 완료 (서비스 코드에 TODO/mock 표시 없음) |
| 대시보드 | `GET /dashboard/summary`, `/dashboard/challenge-progress`, `/dashboard/lifetime-risk`, `/follow-up-actions`, `PATCH /follow-up-actions/{id}/acknowledge`, `/recommendations` | 완료 |
| 병원 검색 | `GET /emergency-facilities/nearby`, `GET /medical-facilities/nearby` | **완료** — `KakaoLocalMedicalFacilitySearchProvider`(카카오 로컬 API 키워드 검색, 카테고리 필터링, 거리순 정렬)와 `NemcEmergencyFacilitySearchProvider`(국립중앙의료원 응급의료 API)가 둘 다 완전히 구현돼 있고, 로컬·운영 서버 `.env` 모두 `MEDICAL_FACILITY_SEARCH_PROVIDER=kakao` + 실제 키 설정 확인 완료 (9/7). |

## 4-1. `scenarios`/`uncertainty` — 이번 MVP 범위 제외로 팀 결정 (9/7)

- 결정: 모레노와 같은 이유로, `age_risk_forecast`의 `scenarios`(시나리오 비교)/`uncertainty`(불확실성 범위)는 이번 MVP에서 아예 노출하지 않기로 팀 결정.
- 백엔드: 기존에도 항상 빈 값(`{}`)이었으므로 변경 없음.
- 프론트: `src/frontend/index.html`의 `.scenario-comparison`, `#uncertainty-panel`에 `hidden` 속성 추가, `src/frontend/app.js`의 `renderAgeRiskForecast()`에서 실제 데이터가 있을 때만 `hidden`을 해제하도록 수정. 지금은 데이터가 없어 항상 숨겨짐 — 나중에 검증된 값이 채워지면 코드 수정 없이 자동으로 다시 표시됨.

## 5-1. 챌린지 추천 RAG 관련 — 팀 확인 결과 "문제 아님"으로 정정 (9/7)

- 챌린지 추천(`GET /challenge-recommendations`)이 RAG가 아닌 규칙 기반(`rule_based_reviewed_template`)인 것은 이미 팀이 확정한 사항이었습니다: `docs/REQUIREMENTS.md`의 `REQ-RECO-001`("Sprint 2는 템플릿만 사용, 생성형 AI·RAG 개인화는 후순위") / `DEC-008`(2026-08-18 확정, 전원 합의).
- 실제 RAG 기능은 별도로 존재하고 이미 완료되어 있습니다: `REQ-RAG-001`("승인된 건강교육 문서에 근거한 답변과 원문 출처") → `POST /api/v1/health-education/questions` (`src/rag/engine.py`의 `answer_with_sources()`). 라이브 확인 결과 당뇨 예방 질문에는 출처(citations) 포함 답변, 약물 관련 질문에는 `answer_status: "medical_safety_refusal"`로 의료진 상담 안내가 정상 동작함을 확인했습니다.
- 즉 팀 연동표의 "RAG 근거" 항목은 챌린지 추천이 아니라 이 건강교육 Q&A 기능을 가리킨 것으로 보이며, 이미 구현·완료되어 있어 별도 조치가 필요 없습니다.

## 6. 실제 요청·응답 JSON 예시

### 회원가입
```
POST /api/v1/auth/signup
{
  "email": "user@example.com",
  "password": "Passw0rd!",
  "terms_agreed": true
}
→ 201 (본문 없음, 이후 /auth/login으로 토큰 발급)
```

### 건강정보 생성
```
POST /api/v1/health-checkups
{
  "checkup_type": "initial",
  "checkup_date": "2026-09-07",
  "height_cm": 165.0,
  "weight_kg": 68.5,
  "waist_cm": 82.0,
  "systolic_bp": 128,
  "diastolic_bp": 82,
  "smoking_status": "never",
  "regular_exercise": true,
  "current_drinker": false,
  "exercise_days_per_week": 3,
  "exercise_minutes": 40
}
→ 201
{
  "checkup_id": 12,
  "bmi": 25.1,
  "feature_schema_version": "v1",
  "created_at": "2026-09-07T01:00:00Z",
  "validation": { "status": "valid", "validated_at": "2026-09-07T01:00:01Z" }
}
```

### 예측 작업 생성 (내일이 / diabetes_incidence)
```
POST /api/v1/prediction-jobs
{ "checkup_id": 12, "model_key": "diabetes_incidence" }
→ 202
{
  "job_id": "job_abc123",
  "status": "queued",
  "model_key": "diabetes_incidence",
  "prediction_id": null,
  "error_code": null,
  "retryable": false,
  "created_at": "2026-09-07T01:00:05Z",
  "status_url": "/api/v1/prediction-jobs/job_abc123"
}
```

### 예측 결과 조회 (오늘 수정한 `signal_level` 포함)
```
GET /api/v1/predictions/latest
→ 200
{
  "prediction_id": 45,
  "risk_category": "high",
  "risk_category_label": "높음",
  "age_risk_forecast": {
    "points": [
      { "display_label": "2년 후 (61세)", "display_percent": 2.3, "signal_level": "caution" },
      { "display_label": "4년 후 (63세)", "display_percent": 4.1, "signal_level": "high" },
      { "display_label": "6년 후 (65세)", "display_percent": 6.0, "signal_level": "high" }
    ]
  },
  "disclaimer": "이 결과는 당뇨병 진단이 아닌 미래 발병 위험 선별 및 건강교육 정보입니다."
}
```

### 오류 응답 예시 (통일 완료 — `error_detail()` 헬퍼로 형식 통일됨)
```
404 LookupError:        { "detail": { "error_code": "HEALTH_CHECKUP_NOT_FOUND", "message": "...", "retryable": false } }
403 PermissionError:     { "detail": { "error_code": "...", "message": "현재 상태에서는 예측 작업을 생성할 수 없습니다.", "retryable": false } }
422 ValueError:          { "detail": { "error_code": "...", "message": "모델 입력 계약을 확인해 주세요.", "retryable": false } }
503 ModelNotReadyError:  { "detail": { "error_code": "MODEL_NOT_READY", "message": "...", "retryable": false } }
503 RuntimeError(큐 실패): { "detail": { "error_code": "QUEUE_UNAVAILABLE", "message": "...", "retryable": true } }
```
모든 케이스가 `{error_code, message, retryable}` 동일한 shape로 나오는 것을 `tests/test_api_responses.py`와 실제 API 호출로 확인했습니다.
