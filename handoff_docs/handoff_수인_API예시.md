# 수인 전달용 — 최신 API 요청·응답 예시

기준: PR #25(`Fix/24 carrot forest sync`, PR #19 브랜치 위에 쌓인 최신 브랜치) 코드 + 로컬 저장소 대조

> ⚠️ **아직 GitHub에 안 올라간 부분 주의**: 예측 작업 실패 시 `MODEL_ARTIFACT_UNAVAILABLE`/`MODEL_DIGEST_MISMATCH`/`MODEL_CONTRACT_MISMATCH`/`INVALID_MODEL_INPUT`으로 세분화되는 부분은 **로컬에서만 고쳐진 상태**이고 아직 PR #25에 푸시되지 않았습니다. 지금 당장 실제 서버를 호출하면 실패 사유가 전부 `INFERENCE_FAILED`로 뭉뚱그려져 나올 수 있으니, 백엔드 푸시 완료 여부를 확인하고 프론트 작업하시는 걸 추천드려요.
>
> **정정 사항**: 이전 버전 이 문서에 `risk_category_label`이 `moderate`로 바뀐다고 적었던 건 제가 잘못 짚은 내용이었습니다 — 실제 코드(`app/prediction/providers.py`, `src/ml/evaluation/diabetes_risk_categories.py`, 프론트 `src/frontend`)는 전부 지금도 `low/caution/high`를 일관되게 씁니다. `moderate`는 모델팀 인수인계서에 적힌 "목표" 이름일 뿐, 실제 구현에는 반영된 적이 없습니다. 아래 예시는 전부 실제 코드 기준(`caution`)으로 다시 맞췄습니다. Docker 대신 실제 MySQL/Redis를 붙여서 전체 pytest(361개)를 돌려 재검증했습니다.

## 공통 포맷

### 성공 응답
```json
{
  "data": {},
  "meta": {
    "request_id": "req_01J...",
    "timestamp": "2026-08-13T03:20:00Z"
  }
}
```

### 오류 응답
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

공통 상태코드: `404`(리소스 없음 — 남의 자원 접근도 404로 통일), `403`(권한 없음), `422`(입력 검증 실패), `503`(서비스 불가)

---

## 회원가입 `POST /api/v1/auth/signup`

**요청** (실제 코드 `SignUpRequest` 기준, PR #25 최신):
```json
{
  "email": "user@example.com",
  "password": "Str0ngPassw0rd!",
  "terms_agreed": true
}
```
- `terms_agreed`가 `false`면 422로 거부됩니다 ("서비스 이용약관에 동의해야 합니다.")
- `name`/`gender`/`birth_date`/`phone_number`는 최근 커밋(`회원가입 이름 수집 제거`)으로 가입 단계에서 빠졌습니다. 이 값들은 가입 이후 프로필 입력 단계(`PATCH /users/me`)에서 받는 걸로 보이니, 가입 직후 프로필 입력 플로우가 별도로 있는지 백엔드팀에 확인해 주세요. 프론트 가입 폼도 3필드 기준으로 맞추시면 됩니다.

## 로그인 `POST /api/v1/auth/login`
```json
{ "email": "user@example.com", "password": "Str0ngPassw0rd!" }
```
**응답**
```json
{ "access_token": "eyJ..." }
```

## 프로필 수정 `PATCH /users/me` — 전부 선택 입력
```json
{
  "name": "홍길동",
  "phone_number": "01011112222",
  "birthday": "1990-05-01",
  "gender": "FEMALE"
}
```
**프로필 조회 응답**
```json
{ "id": 101, "name": "홍길동", "email": "user@example.com", "phone_number": "01011112222", "birthday": "1990-05-01", "gender": "FEMALE", "created_at": "2026-08-13T03:20:00Z" }
```

## 건강정보 입력 `POST /health-checkups`

⚠️ RF25 모델 계약 반영으로 필드가 25변수 기준으로 확장되어 있습니다. 최신 실제 구현 기준 예시:
```json
{
  "checkup_type": "initial",
  "checkup_date": "2026-08-01",
  "height_cm": 165,
  "weight_kg": 58.5,
  "self_rated_health": "good",
  "meal_count_yesterday": 3,
  "smoking_status": "never",
  "current_drinker": false,
  "regular_exercise": true,
  "exercise_days_per_week": 3,
  "exercise_minutes": 40,
  "annual_household_income_10k_krw": 4500,
  "health_satisfaction_score": 7,
  "economic_satisfaction_score": 6,
  "overall_quality_of_life_score": 7,
  "hypertension_diagnosis": false,
  "cancer_diagnosis": false,
  "chronic_lung_disease_diagnosis": false,
  "liver_disease_diagnosis": false,
  "heart_disease_diagnosis": false,
  "cerebrovascular_disease_diagnosis": false,
  "psychiatric_disease_diagnosis": false,
  "arthritis_rheumatism_diagnosis": false,
  "education_level": "university",
  "marital_status": "married",
  "household_structure": "couple",
  "depressed_feeling_last_week": false,
  "sleep_difficulty_last_week": false,
  "feature_schema_version": "klosa_stage3_25features_v1"
}
```
- `smoking_status`는 `never/former/current` 3단계 (예전 `current_smoker: boolean`에서 변경됨)
- 진단·소득·만족도·교육/혼인/가구형태·우울/수면 항목은 전부 선택값 — `null`로 보내도 됨(임의로 정상값 처리하지 않음)
- (새로 확인) `self_rated_health`, `meal_count_yesterday`도 최근 마이그레이션으로 선택값(nullable)이 됐습니다 — 이 둘도 `null` 허용됩니다.
- `regular_exercise=false`면 `exercise_days_per_week`/`exercise_minutes`는 백엔드가 자동으로 `0` 처리

## 예측 작업 접수 `POST /prediction-jobs` (202)
**요청**
```json
{ "checkup_id": 501, "model_key": "diabetes_incidence" }
```
**응답**
```json
{
  "data": {
    "job_id": "predjob_01J...",
    "status": "queued",
    "model_key": "diabetes_incidence",
    "model_version": "rf-25features-v001-run-20260825T045054926974Z",
    "status_url": "/api/v1/prediction-jobs/predjob_01J..."
  },
  "meta": {"request_id": "req_01J...", "timestamp": "2026-08-13T03:20:00Z"}
}
```

## 작업 상태 조회 `GET /prediction-jobs/{job_id}`

**성공**
```json
{
  "data": { "job_id": "predjob_01J...", "status": "succeeded", "prediction_id": 901, "finished_at": "2026-08-13T03:20:04Z" },
  "meta": {"request_id": "req_01J...", "timestamp": "2026-08-13T03:20:04Z"}
}
```
**실패(타임아웃)**
```json
{
  "data": { "job_id": "predjob_01J...", "status": "failed", "error_code": "TIMEOUT", "retryable": true, "retry_after_seconds": 30, "finished_at": "2026-08-13T03:20:14Z" },
  "meta": {"request_id": "req_01J...", "timestamp": "2026-08-13T03:20:14Z"}
}
```
**실패(모델 계약 오류 — 재시도 불가)**: `error_code`가 `MODEL_ARTIFACT_UNAVAILABLE` / `MODEL_DIGEST_MISMATCH` / `MODEL_CONTRACT_MISMATCH` / `INVALID_MODEL_INPUT`으로 오면 `retryable: false`입니다. 프론트에서 "재시도" 버튼을 노출하면 안 됩니다.

## 예측 결과 조회 `GET /predictions/{prediction_id}` (`/predictions/latest`, `GET /predictions` 목록도 필드 동일)

⚠️ 실제 코드 기준으로 응답 필드가 훨씬 늘어나 있습니다 — 예전 문서 예시보다 아래가 정확합니다.

**승인 전(개발 단계) — 위험 범주 비공개**
```json
{
  "prediction_id": 901,
  "checkup_id": 501,
  "input_as_of_date": "2026-08-01",
  "model_key": "diabetes_incidence",
  "task_type": "binary_incidence_risk_screening",
  "prediction_type": "future_incidence",
  "outcome_definition": null,
  "result_status": "succeeded",
  "promotion_status": "development_only",
  "risk_category": null,
  "risk_category_label": null,
  "screening_signal_detected": null,
  "screening_result_label": null,
  "model_version": "rf-25features-v001-run-20260825T045054926974Z",
  "threshold_version": "unapproved",
  "threshold_scope": "future_incidence_2y",
  "decision_threshold": null,
  "output_status": null,
  "predicted_at": "2026-08-13T03:20:04Z",
  "disclaimer": "개발용 추론 연결은 완료되었지만 검토된 임계값이 없어 개인 위험 범주와 확률을 제공하지 않습니다.",
  "age_risk_forecast": null,
  "raw_probability_exposed": false
}
```
**승인 후 — 위험 범주 공개**
```json
{
  "prediction_id": 901,
  "checkup_id": 501,
  "input_as_of_date": "2026-08-01",
  "model_key": "diabetes_incidence",
  "task_type": "binary_incidence_risk_screening",
  "prediction_type": "future_incidence",
  "result_status": "succeeded",
  "promotion_status": "approved",
  "risk_category": "caution",
  "risk_category_label": "주의",
  "model_version": "rf-25features-v001-run-20260825T045054926974Z",
  "threshold_version": "validation-spec043-caution-recall090-v1",
  "threshold_scope": "future_incidence_2y",
  "decision_threshold": 0.022410835788097848,
  "output_status": "released",
  "predicted_at": "2026-08-13T03:20:04Z",
  "disclaimer": "이 결과는 당뇨병 진단이 아닌 미래 발병 위험 선별 및 건강교육 정보입니다.",
  "age_risk_forecast": null,
  "raw_probability_exposed": false
}
```
- `risk_category` 값은 실제 코드 기준 지금도 `low` / `caution` / `high` 3종입니다(한글 라벨: 낮음/주의/높음). 예전에 제가 이 문서에 `moderate`로 안내했던 건 잘못된 정정이었으니 무시해 주세요.
- `diabetes_current_screening`(오늘이) 모델은 `prediction_type: "current_screening"`이고, 위 대신 `screening_signal_detected`(bool)·`screening_result_label`("검사 권고"/"현재 위험 신호 낮음")을 씁니다.
- 원시 확률(`internal_score`)은 어떤 응답에서도 노출되지 않습니다(`raw_probability_exposed` 항상 `false`).
- `age_risk_forecast`는 연령별 전망 기능이 아직 없어서 항상 `null`입니다(자세한 조회는 아래 `risk-curve` 참고).

## 예측 변화 비교 `GET /predictions/changes`
같은 모델·같은 outcome으로 예측이 2건 이상 있어야 값이 채워집니다.
```json
{
  "data": {
    "available": true,
    "first": { "...위 predictions 응답과 동일 구조..." : "..." },
    "latest": { "...위 predictions 응답과 동일 구조..." : "..." },
    "change": null,
    "notice": "예측 변화는 진단이나 치료 효과를 의미하지 않습니다."
  }
}
```

## 연령별 위험 전망 `GET /predictions/{prediction_id}/risk-curve`
생존모델이 아직 없어서 `status`가 `"available"`이 아닌 동안은 항상 빈 결과만 옵니다.
```json
{
  "data": {
    "prediction_id": 901,
    "status": "not_applicable",
    "points": [],
    "summary": null,
    "message": "연령별 위험 전망은 승인된 생존모델 결과가 준비된 이후에만 제공됩니다."
  }
}
```

## 위험·보호 요인 `GET /predictions/{prediction_id}/risk-factors`
아직 어디서도 `RiskFactor`에 실제로 저장을 안 하기 때문에(세준 전달 문서 2번 참고) `items`는 항상 빈 배열입니다.
```json
{
  "data": {
    "prediction_id": 901,
    "status": "not_available",
    "items": [],
    "message": "검증된 설명 방법이 준비되기 전에는 위험·보호 요인을 표시하지 않습니다.",
    "shap_claimed": false
  }
}
```

## 챌린지 사이클 시작 `POST /challenge-cycles` (201)
**요청**
```json
{ "start_date": "2026-08-17", "challenge_ids": [11, 24, 37] }
```
**응답**
```json
{
  "data": {
    "cycle_id": 71, "cycle_number": 1, "start_date": "2026-08-17", "end_date": "2026-09-13", "status": "scheduled",
    "user_challenges": [
      {"user_challenge_id": 301, "challenge_id": 11},
      {"user_challenge_id": 302, "challenge_id": 24},
      {"user_challenge_id": 303, "challenge_id": 37}
    ]
  },
  "meta": {"request_id": "req_01J...", "timestamp": "2026-08-13T03:20:00Z"}
}
```

## 대시보드 요약 `GET /dashboard/summary`
```json
{
  "data": {
    "risk_cards": [
      {"model_key": "diabetes_incidence", "risk_category": "moderate", "risk_category_label": "주의", "model_version": "rf-25features-v001-run-20260825T045054926974Z", "predicted_at": "2026-08-13T03:20:04Z"}
    ],
    "current_cycle": {"cycle_id": 71, "day": 4, "completion_rate": 66.7, "recent_7_days": {"completed": 8, "planned": 12}},
    "next_action": null,
    "disclaimer": "위험 범주와 챌린지 수행률은 진단, 질병의 호전 또는 치료 효과를 의미하지 않습니다."
  },
  "meta": {"request_id": "req_01J...", "timestamp": "2026-08-13T03:20:00Z"}
}
```

---
필요하면 개별 필드 하나하나 더 구체적으로 뽑아드릴게요.
