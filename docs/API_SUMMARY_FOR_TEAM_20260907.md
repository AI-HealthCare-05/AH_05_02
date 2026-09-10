# 백엔드 API 점검 결과 (9/7)

## 완료 기준
- [x] API별 완료/부분 구현/미구현 상태가 정리된다.
- [x] 프론트가 바로 사용할 수 있는 요청·응답 예시가 제공된다.

---

## 1. 흐름별 API 상태

| 흐름 | API | 상태 | 비고 |
|---|---|---|---|
| 회원가입 | `POST /auth/signup`, `POST /auth/login` | ✅ 완료 | `terms_agreed` 저장 안 되던 버그 수정함 |
| 사용자 정보 | `PATCH /users/me/profile`, `GET /users/me`, 건강정보 API | ✅ 완료 | 프로필 미입력 상태로 다음 단계 호출해도 422로 안전하게 막힘 |
| 오늘이 | 예측 생성·상태·결과 API | ✅ 완료 | |
| 내일이 | 예측 생성·상태·결과 API | ✅ 완료 | `signal_level` 누락 버그 수정함. `scenarios`/`uncertainty`는 아래 참고 |
| 모레노 | 전망 결과 API | ⛔ 이번 MVP 범위 제외 | 승인된 생존모델 없음 (팀 결정) — 503 유지가 정상 동작 |
| 고위험 안내 | 의료기관 검색 API | ✅ 완료 | 카카오 실제 연동, 로컬·운영 키 확인 완료 |
| 응급 안내 | 응급실 검색 API | ✅ 완료 | NEMC 실제 연동 |
| 챌린지 | 챌린지·추천·기록 API | ✅ 완료 | 추천은 규칙 기반(팀 결정과 일치). RAG는 건강교육 Q&A에 별도 구현됨 |
| 대시보드 | 대시보드 API | ✅ 완료 | |
| PredictionJob 상태/오류 | `/prediction-jobs`, `/ai-jobs` | ✅ 완료 | 상태값 타입 통일 + `/ai-jobs` 라우터 미등록 버그 수정 |
| 시나리오 비교/불확실성 | `age_risk_forecast.scenarios`/`uncertainty` | 🔶 부분구현 → 이번 MVP 제외 결정 | 검증된 방법론 없어 항상 빈 값. 화면에서도 숨김 처리 완료 |
| 위험요인 설명 | `GET /predictions/{id}/risk-factors` | 🔶 부분구현 | 항상 빈 배열 (설명 기능 미완성) |

---

## 2. 프론트용 요청·응답 예시

### 회원가입
```
POST /api/v1/auth/signup
{ "email": "user@example.com", "password": "Passw0rd!", "terms_agreed": true }
→ 201
```

### 건강정보 생성
```
POST /api/v1/health-checkups
{
  "checkup_type": "initial",
  "checkup_date": "2026-09-07",
  "height_cm": 165.0, "weight_kg": 68.5, "waist_cm": 82.0,
  "systolic_bp": 128, "diastolic_bp": 82,
  "smoking_status": "never", "regular_exercise": true, "current_drinker": false,
  "exercise_days_per_week": 3, "exercise_minutes": 40
}
→ 201
{ "checkup_id": 12, "bmi": 25.1, "created_at": "2026-09-07T01:00:00Z" }
```

### 예측 작업 생성 (내일이)
```
POST /api/v1/prediction-jobs
{ "checkup_id": 12, "model_key": "diabetes_incidence" }
→ 202
{ "job_id": "job_abc123", "status": "queued", "model_key": "diabetes_incidence", "status_url": "/api/v1/prediction-jobs/job_abc123" }
```

### 예측 결과 조회 (signal_level 포함)
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
    ],
    "scenarios": {},
    "uncertainty": {}
  }
}
```
> `scenarios`/`uncertainty`는 항상 빈 값입니다 — 프론트에서 이 필드로 화면을 그리지 마세요(이미 관련 UI는 숨김 처리했습니다).

### 오류 응답 (모든 API 공통 형식)
```
{ "detail": { "error_code": "PREDICTION_JOB_NOT_FOUND", "message": "예측 작업을 찾을 수 없습니다.", "retryable": false } }
```
`error_code`/`message`/`retryable` 세 필드는 어떤 에러든 항상 이 모양으로 옵니다.

---

자세한 근거·검증 과정은 `docs/BACKEND_STATUS_20260907.md`, API 전체 목록은 `docs/API_STATUS_20260907.md` 참고.
