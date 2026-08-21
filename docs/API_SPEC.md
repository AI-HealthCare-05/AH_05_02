# 만성질환 생활습관 챌린지 웹서비스 API 명세서

| 항목 | 내용 |
|---|---|
| 문서 버전 | v2.0 |
| 작성일 | 2026-08-19 |
| 상태 | Sprint 2 구현 기준선 |
| API Base URL | `/api/v1` |
| 인증 방식 | Bearer Access Token |
| 데이터 형식 | `application/json`, `snake_case` |
| 기준 산출물 | 요구사항 정의서 v2.0, 서비스 대상·제외 범위 및 의료 안전 문구 v1.0, Figma 와이어프레임, ERD v2 |

> 본 서비스의 결과는 의료진의 진단·처방이 아닌 위험 선별 및 건강교육 정보이다. 약물의 시작·중단·용량 변경을 안내하지 않는다.

## 1. 작성 기준과 확인 필요 사항

### 1.1 API 작성 기준

- 만 19세 이상 서비스 이용 가능 여부, 만 40세 이상 핵심 타깃 여부, 활성 모델 적용 가능 여부를 각각 반환한다.
- Sprint 2 활성 예측은 당뇨병 미래 신규 발병 이진분류 하나로 제한한다.
- KLoSA 단독 모델은 검증 근거가 없는 40~44세에 적용하지 않으며, 실제 예측 범위는 활성 모델 카드의 `min_age`·`max_age`·모집단 조건으로 통제한다.
- 건강검진 1건에 여러 모델 버전의 예측 결과를 허용한다.
- 원시 확률과 변화값은 내부 감사·분석용으로 저장하거나 계산할 수 있으나, 사용자에게 건강 개선율로 노출하지 않는다.
- 예측은 비동기 작업으로 접수하여 `job_id`를 먼저 반환한다.
- 알림 기능과 이미지 식단 분석은 MVP에서 제외한다.

### 1.2 산출물 간 확인 필요 사항

| ID | 항목 | 현재 차이 | API 명세 적용안 |
|---|---|---|---|
| DEC-001 | 이용 범위 | 이용 자격·핵심 타깃·모델 검증 범위가 서로 다름 | `service_eligible`·`target_segment`·`model_eligible` 분리 |
| DEC-002 | 질환 범위 | 고혈압은 후속 확장 대상 | Sprint 2는 `diabetes_incidence`만 활성화 |
| DEC-003 | 예측 출력 | 미래 발병 이진분류와 사용자 표시를 구분해야 함 | 내부 확률은 저장하고 공개 화면은 `낮음·주의·높음` 범주 표시 |
| DEC-004 | 예측 작업 | 비동기 상태와 영속 이력을 분리해야 함 | Redis는 최소 작업 상태, DB는 요청·완료·실패·모델 버전 최소 이력 |

## 2. 공통 규칙

### 2.1 인증과 권한

- 공개 API를 제외한 모든 API는 `Authorization: Bearer {access_token}` 헤더가 필요하다.
- 사용자는 본인의 건강정보·예측·챌린지 기록만 조회하거나 변경할 수 있다.
- 다른 사용자의 자원에 접근하면 `404`를 반환하여 자원 존재 여부를 노출하지 않는다.
- 비밀번호·토큰·이메일 원문·건강 수치는 애플리케이션 로그에 기록하지 않는다.

### 2.2 시간·목록·멱등성

- 서버 저장 시각은 UTC, 응답은 ISO 8601 형식으로 반환한다. 예: `2026-08-13T03:20:00Z`.
- 목록 API는 `page`, `size`, `sort`를 사용한다. 기본값은 `page=1`, `size=20`, 최대 `size=100`이다.
- 같은 날짜의 챌린지 기록은 `PUT`으로 생성 또는 수정하여 중복을 방지한다.
- 예측 요청은 `Idempotency-Key` 헤더를 지원하여 중복 작업 생성을 방지한다.

### 2.3 공통 성공 응답

```json
{
  "data": {},
  "meta": {
    "request_id": "req_01J...",
    "timestamp": "2026-08-13T03:20:00Z"
  }
}
```

### 2.4 공통 오류 응답

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "입력값을 확인해 주세요.",
    "fields": [
      {"field": "systolic_bp", "reason": "허용 범위를 벗어났습니다."}
    ],
    "request_id": "req_01J..."
  }
}
```

| 상태 코드 | 사용 기준 |
|---|---|
| `200` | 조회·수정 성공 |
| `201` | 자원 생성 성공 |
| `202` | 비동기 예측 작업 접수 |
| `204` | 로그아웃·철회 등 응답 본문 없는 성공 |
| `400` | 처리할 수 없는 요청 |
| `401` | 인증 실패 또는 토큰 만료 |
| `403` | 동의 누락·기진단 등 정책상 실행 불가 |
| `404` | 자원 없음 또는 소유권 없음 |
| `409` | 이메일·검진일·챌린지 기록 중복 |
| `422` | 필드 형식·단위·범위 오류 |
| `500` | 서버 내부 오류 |
| `503` | DB·모델 서버 준비되지 않음 |
| `504` | 작업 접수 전 동기식 게이트웨이·모델 준비 확인의 시간 초과. `202` 접수 후 시간초과에는 사용하지 않음 |

## 3. API 목록

### 3.1 시스템·인증·회원

| Method | URI | 설명 | 인증 | 관련 요구사항 |
|---|---|---|---|---|
| GET | `/health` | 웹 서버 생존 확인 | 불필요 | NFR-OPS-001 |
| GET | `/ready` | DB·모델 서버 준비 상태 확인 | 불필요 | NFR-OPS-001 |
| POST | `/auth/signup` | 이메일 회원가입 | 불필요 | REQ-USER-001 |
| POST | `/auth/login` | 로그인 및 토큰 발급 | 불필요 | REQ-USER-002 |
| POST | `/auth/refresh` | Access Token 재발급 | Refresh Token | REQ-USER-002 |
| POST | `/auth/logout` | Refresh Token 폐기 | 필요 | REQ-USER-002 |
| GET | `/users/me` | 내 계정·프로필 조회 | 필요 | REQ-HEALTH-001 |
| PATCH | `/users/me/profile` | 성별·생년월일·키 수정 | 필요 | REQ-HEALTH-001 |
| DELETE | `/users/me` | 재인증 후 탈퇴 요청 | 필요 | REQ-USER-004 |

### 3.2 동의·적합성 확인

| Method | URI | 설명 | 주요 엔터티 | 관련 요구사항 |
|---|---|---|---|---|
| GET | `/consents` | 현재 동의 상태·버전 조회 | `consents` | REQ-USER-003 |
| POST | `/consents` | 건강정보 처리 동의 저장 | `consents` | REQ-USER-003 |
| PATCH | `/consents/{consent_id}/withdraw` | 동의 철회 | `consents` | NFR-SEC-003 |
| POST | `/eligibility-checks` | 이용 연령·동의·기진단·경고 증상·모델 범위 판정 | `eligibility_checks` | REQ-USER-003~004 |
| GET | `/eligibility-checks/latest` | 최근 적합성 결과 조회 | `eligibility_checks` | REQ-USER-004 |

### 3.3 건강정보

| Method | URI | 설명 | 주요 엔터티 | 관련 요구사항 |
|---|---|---|---|---|
| POST | `/health-checkups` | 건강검진·생활습관 기록 생성 | `health_checkups` | REQ-HEALTH-002~004 |
| GET | `/health-checkups` | 건강검진 이력 목록 | `health_checkups` | REQ-HEALTH-003 |
| GET | `/health-checkups/{checkup_id}` | 건강검진 상세 조회 | `health_checkups` | REQ-HEALTH-003 |
| PATCH | `/health-checkups/{checkup_id}` | 예측 전 기록 정정 | `health_checkups` | REQ-HEALTH-003~004 |
| GET | `/health-checkups/input-schema` | 입력 필드·단위·허용 범위·필수 여부 조회 | 설정/메타데이터 | REQ-HEALTH-002~004 |

예측과 연결된 검진은 수정하지 않는다. 정정값은 새로운 검진 레코드로 저장한다.

### 3.4 AI 예측

| Method | URI | 설명 | 주요 엔터티 | 관련 요구사항 |
|---|---|---|---|---|
| GET | `/models/active` | 활성 모델 버전·연령·모집단·출력 정의 조회 | 모델 레지스트리 | NFR-ML-003 |
| POST | `/prediction-jobs` | 예측 작업 접수, `202`와 `job_id` 반환 | `prediction_jobs`·Redis | REQ-PRED-001~002 |
| GET | `/prediction-jobs/{job_id}` | 작업 상태·완료된 `prediction_id` 조회 | `prediction_jobs`·Redis | REQ-PRED-001 |
| GET | `/predictions/{prediction_id}` | 미래 발병 위험 범주·모델 버전 조회 | `predictions` | REQ-PRED-002~004 |
| GET | `/predictions/{prediction_id}/risk-factors` | 위험·보호 요인 조회 | `risk_factors` | REQ-PRED-005 |
| GET | `/predictions/latest` | 최신 유효 예측 조회 | `predictions` | REQ-PRED-004 |
| GET | `/predictions` | 질환·검진·기간별 예측 이력 조회 | `predictions` | REQ-DASH-003 |
| GET | `/predictions/changes` | 내부 분석용 최초·최신 결과 비교 | `predictions` | REQ-DASH-003 |

`/predictions/latest`는 `predicted_at DESC, id DESC` 순으로 최신값을 판별한다. 변화값은 같은 질환과 같은 점수 정의끼리만 비교한다.

예측 작업 상태는 `queued`, `running`, `succeeded`, `failed`로 통일한다. 작업 생성 시각은 DB와 API 모두 `created_at`을 사용한다. `202` 접수 후 추론 시간초과가 발생하면 상태 조회는 HTTP `200`과 함께 `status: failed`, `error_code: TIMEOUT`, `retryable`, `retry_after_seconds`를 반환한다.

위험 범주는 승인된 `threshold_version`이 있을 때만 공개한다. 임계값 숫자는 검증 세트의 판별력·보정·민감도와 의료 안전 문구 검토를 통과한 모델 카드에 기록하며 API 코드에 임의로 고정하지 않는다.

### 3.5 챌린지

| Method | URI | 설명 | 주요 엔터티 | 관련 요구사항 |
|---|---|---|---|---|
| GET | `/challenges` | 질환·카테고리·난이도별 챌린지 조회 | `challenges` | REQ-CHAL-001 |
| GET | `/challenge-recommendations` | 예측 결과에 맞는 후보와 추천 이유 조회 | 규칙·`recommendations` | REQ-CHAL-001, REQ-RECO-001 |
| POST | `/challenge-cycles` | 최대 3개 챌린지로 28일 사이클 시작 | `challenge_cycles`, `user_challenges` | REQ-CHAL-002~003 |
| GET | `/challenge-cycles/current` | 현재 진행 중 사이클 조회 | `challenge_cycles` | REQ-DASH-002 |
| GET | `/challenge-cycles/{cycle_id}` | 사이클·참여 챌린지·달성률 조회 | `challenge_cycles`, `user_challenges` | REQ-CHAL-002~004 |
| PATCH | `/challenge-cycles/{cycle_id}/status` | 사용자 중단 또는 기진단 확인에 따른 상태 변경 | `challenge_cycles` | REQ-CHAL-005 |
| PUT | `/user-challenges/{user_challenge_id}/logs/{log_date}` | 날짜별 수행 여부·측정값 생성 또는 정정 | `challenge_logs` | REQ-CHAL-004~005 |
| GET | `/user-challenges/{user_challenge_id}/logs` | 기간별 수행 기록 조회 | `challenge_logs` | REQ-CHAL-004~006 |

### 3.6 대시보드·후속조치·추천·피드백

| Method | URI | 설명 | 주요 엔터티 | 관련 요구사항 |
|---|---|---|---|---|
| GET | `/dashboard/summary` | 최신 위험 범주·현재 챌린지 통합 요약 | 조회 집계 | REQ-DASH-001~003 |
| GET | `/dashboard/risk-trends` | 질환별 예측 시계열 | `predictions` | REQ-DASH-003 |
| GET | `/dashboard/challenge-progress` | 최근 7일·4주 달성률 | 챌린지 엔터티 | REQ-DASH-002 |
| GET | `/follow-up-actions` | 의료기관 상담 권고 이력 조회 | `follow_up_actions` | REQ-PRED-006 |
| PATCH | `/follow-up-actions/{action_id}/acknowledge` | 권고 확인 시각 저장 | `follow_up_actions` | REQ-PRED-006 |
| GET | `/recommendations` | 검토된 예방 행동·챌린지 설명과 출처 조회 | `recommendations` | REQ-RECO-001 |

의료기관 권고 생성은 적합성 또는 예측 서비스 내부에서 수행한다. `trigger_source`는 `eligibility_check` 또는 `prediction`, `trigger_entity_id`는 해당 레코드 ID로 저장한다.

## 4. 핵심 요청·응답 예시

### 4.1 회원가입

`POST /api/v1/auth/signup`

```json
{
  "email": "user@example.com",
  "password": "********",
  "terms_agreed": true
}
```

```json
{
  "data": {
    "user_id": 101,
    "email": "user@example.com",
    "created_at": "2026-08-13T03:20:00Z"
  },
  "meta": {"request_id": "req_01J...", "timestamp": "2026-08-13T03:20:00Z"}
}
```

### 4.2 적합성 확인

`POST /api/v1/eligibility-checks`

```json
{
  "birth_date": "1975-04-12",
  "has_diabetes_diagnosis": false,
  "has_urgent_warning_sign": false
}
```

```json
{
  "data": {
    "eligibility_check_id": 31,
    "service_eligible": true,
    "target_segment": "primary_40_plus",
    "model_eligible": true,
    "reason_codes": [],
    "next_action": "health_checkup_input",
    "active_model": {
      "model_key": "diabetes_incidence",
      "version": "v1.0.0",
      "min_age": 45,
      "max_age": null
    }
  },
  "meta": {"request_id": "req_01J...", "timestamp": "2026-08-13T03:20:00Z"}
}
```

적합성 판정 API는 판정이 완료되면 `200`을 반환한다. 기진단·경고 증상·미동의·모델 검증 범위 밖이면 `model_eligible=false`, 표준 `reason_codes`, 적절한 `next_action`을 반환하고 이후 예측 작업 생성을 허용하지 않는다.

### 4.3 건강검진 입력

`POST /api/v1/health-checkups`

```json
{
  "checkup_type": "initial",
  "checkup_date": "2026-08-01",
  "weight_kg": 67.5,
  "waist_cm": 91.0,
  "smoking_status": "never",
  "drinking_frequency": "monthly_or_less",
  "physical_activity_level": "insufficient",
  "has_family_history_diabetes": true,
  "feature_contract_version": "diabetes-incidence-input-v1"
}
```

응답에는 생성된 `checkup_id`, 입력값의 단위와 검증 결과를 포함한다. 위 필드는 계약 예시이며 실제 필수·선택 입력은 양준혁 담당 모델 입력 계약으로 고정한다. 라벨을 직접 결정하거나 기준 시점 이후에 관측된 값은 입력에서 제외한다.

### 4.4 비동기 예측 요청

`POST /api/v1/prediction-jobs`

```json
{
  "checkup_id": 501,
  "model_key": "diabetes_incidence"
}
```

`202 Accepted`

```json
{
  "data": {
    "job_id": "predjob_01J...",
    "status": "queued",
    "model_key": "diabetes_incidence",
    "model_version": "v1.0.0",
    "status_url": "/api/v1/prediction-jobs/predjob_01J..."
  },
  "meta": {"request_id": "req_01J...", "timestamp": "2026-08-13T03:20:00Z"}
}
```

`GET /api/v1/prediction-jobs/{job_id}` 완료 응답:

```json
{
  "data": {
    "job_id": "predjob_01J...",
    "status": "succeeded",
    "prediction_ids": [901],
    "finished_at": "2026-08-13T03:20:04Z"
  },
  "meta": {"request_id": "req_01J...", "timestamp": "2026-08-13T03:20:04Z"}
}
```

시간초과 실패 응답은 최초 요청을 `504`로 되돌리지 않고 다음과 같이 상태 조회 결과로 제공한다.

```json
{
  "data": {
    "job_id": "predjob_01J...",
    "status": "failed",
    "error_code": "TIMEOUT",
    "retryable": true,
    "retry_after_seconds": 30,
    "finished_at": "2026-08-13T03:20:14Z"
  },
  "meta": {"request_id": "req_01J...", "timestamp": "2026-08-13T03:20:14Z"}
}
```

### 4.5 예측 결과

`GET /api/v1/predictions/901`

```json
{
  "data": {
    "prediction_id": 901,
    "checkup_id": 501,
    "model_key": "diabetes_incidence",
    "outcome_definition": "next_observation_new_diabetes_diagnosis",
    "risk_category": "caution",
    "risk_category_label": "주의",
    "model_version": "v1.0.0",
    "model_population": "baseline_undiagnosed_age_45_plus",
    "predicted_at": "2026-08-13T03:20:04Z",
    "disclaimer": "이 결과는 당뇨병 진단이 아닌 미래 발병 위험 선별 및 건강교육 정보입니다."
  },
  "meta": {"request_id": "req_01J...", "timestamp": "2026-08-13T03:20:04Z"}
}
```

### 4.6 4주 챌린지 시작

`POST /api/v1/challenge-cycles`

```json
{
  "start_date": "2026-08-17",
  "challenge_ids": [11, 24, 37]
}
```

```json
{
  "data": {
    "cycle_id": 71,
    "cycle_number": 1,
    "start_date": "2026-08-17",
    "end_date": "2026-09-13",
    "status": "scheduled",
    "user_challenges": [
      {"user_challenge_id": 301, "challenge_id": 11},
      {"user_challenge_id": 302, "challenge_id": 24},
      {"user_challenge_id": 303, "challenge_id": 37}
    ]
  },
  "meta": {"request_id": "req_01J...", "timestamp": "2026-08-13T03:20:00Z"}
}
```

### 4.7 일일 수행 기록

`PUT /api/v1/user-challenges/301/logs/2026-08-17`

```json
{
  "is_completed": true,
  "value": 30,
  "source": "self_report"
}
```

미래 날짜는 `422`, 같은 날짜의 재요청은 새 레코드를 만들지 않고 기존 기록을 정정한다.

### 4.8 대시보드 요약

`GET /api/v1/dashboard/summary`

```json
{
  "data": {
    "risk_cards": [
      {
        "model_key": "diabetes_incidence",
        "risk_category": "caution",
        "risk_category_label": "주의",
        "model_version": "v1.0.0",
        "predicted_at": "2026-08-13T03:20:04Z"
      }
    ],
    "current_cycle": {
      "cycle_id": 71,
      "day": 4,
      "completion_rate": 66.7,
      "recent_7_days": {"completed": 8, "planned": 12}
    },
    "next_action": null,
    "disclaimer": "위험 범주와 챌린지 수행률은 진단, 질병의 호전 또는 치료 효과를 의미하지 않습니다."
  },
  "meta": {"request_id": "req_01J...", "timestamp": "2026-08-13T03:20:00Z"}
}
```

## 5. 화면·요구사항·DB 추적표

| 화면 | 요구사항 | API | DB |
|---|---|---|---|
| 서비스 소개 | NFR-SAFE-001 | 없음 | 없음 |
| 회원가입·로그인 | REQ-USER-001~002 | `/auth/*` | `users` |
| 건강정보 동의 | REQ-USER-003 | `/consents` | `consents` |
| 적합성·안전 확인 | REQ-USER-003~004 | `/eligibility-checks` | `eligibility_checks`, `user_profiles` |
| 검진 결과 입력 | REQ-HEALTH-001~004 | `/health-checkups` | `health_checkups` |
| 예측 진행·결과 | REQ-PRED-001~006 | `/prediction-jobs`, `/predictions` | `prediction_jobs`, `predictions`, `risk_factors` |
| 챌린지 선택 | REQ-CHAL-001~003 | `/challenge-recommendations`, `/challenge-cycles` | 챌린지 관련 4개 엔터티 |
| 일일 챌린지 기록 | REQ-CHAL-004 | `/user-challenges/*/logs` | `challenge_logs` |
| 추적 대시보드 | REQ-DASH-001~003 | `/dashboard/*` | 예측·검진·챌린지 집계 |
| 의료기관 안내 | REQ-PRED-006, REQ-CHAL-005 | `/follow-up-actions` | `follow_up_actions` |
| 추천 설명 | REQ-RECO-001 | `/recommendations` | `recommendations` |

## 6. 구현·검수 기준

- FastAPI의 `/docs`와 `/openapi.json`에서 요청·응답 스키마와 모든 공통 오류 예시를 확인할 수 있어야 한다.
- 일반 사용자 API는 배포 환경에서 P95 3초 이내, 예측 요청 접수는 1초 이내를 목표로 한다.
- 모델 추론은 준비 완료 상태에서 P95 5초 이내를 목표로 하고 10초 초과 시 `504`를 반환한다.
- 다른 사용자의 ID를 사용한 접근, 동의 없는 건강정보 입력, 기진단자의 예측 실행을 통합 테스트한다.
- 동일 모델 버전과 동일 입력은 반복 실행에서 같은 결과를 반환해야 한다.
- 고위험·경고 증상 응답에는 생활습관 안내보다 의료기관 안내를 우선 포함한다.

## 7. 2026-08-21 구현 상태

- 정식 실행 기준은 `app/main.py`이며 `/api/v1/prediction-jobs`를 포함한 핵심 사용자 흐름(End-to-End)을 구현했다.
- 작업 상태는 `queued/running/succeeded/failed`, 생성 시각은 `created_at`으로 통일했다.
- `klosa-diabetes-incident-v1` 입력 계약과 교체 가능한 `PredictionProvider`를 적용했다.
- 기본 `development` provider는 시스템 연결만 검증하며 위험 범주·내부 점수·확률을 생성하거나 공개하지 않는다.
- 승인 전 위험요인 API는 `not_available`과 빈 목록을 반환한다.
- 챌린지·4주 사이클·일일 기록·기본 대시보드와 의료기관 후속조치 API를 연결했다.
- 구현·테스트 상세는 `SPRINT2_IMPLEMENTATION_REPORT_20260821.md`를 따른다.
- 예측 실패 시 임의 결과를 생성하거나 실패한 예측 레코드를 저장하지 않는다.
- OpenAPI 스키마, 요구사항 ID, Figma 화면, ERD 엔터티 간 추적표를 Sprint 종료 전 다시 점검한다.
