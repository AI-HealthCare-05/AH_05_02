# 모델–API–DB–화면 공통 입출력 계약

| 항목 | 확정 기준 |
|---|---|
| API 기본 경로 | `/api/v1` |
| 모델 키 | `diabetes_incidence` |
| 예측 목적 | 다음 KLoSA 조사 시점의 신규 당뇨 진단 위험 선별 |
| 작업 상태 | `queued/running/succeeded/failed` |
| 특성 스키마 | `klosa-diabetes-incident-v1` |
| 사용자 결과 | 승인된 임계값 버전이 있을 때만 `낮음/주의/높음` 표시 |

## 1. 입력 계약

사용자는 건강정보 화면에서 원자료를 입력하고, 서버가 모델 특성을 생성한다.

| 모델 특성 | 생성·입력 기준 | 형식 |
|---|---|---|
| `age` | 생년월일과 검진일로 서버 계산 | 정수, 활성 모델 검증 연령 내 |
| `bmi` | `weight_kg / (height_cm / 100)^2` | 실수, 10~80 |
| `self_rated_health` | 사용자 선택 | `very_good/good/fair/poor/very_poor` |
| `meal_count_yesterday` | 전일 식사 횟수 | 정수, 0~10 |
| `sex` | 가입 기본정보 | `female/male` |
| `regular_exercise` | 규칙적 운동 여부 | boolean |
| `current_smoker` | 현재 흡연 여부 | boolean |
| `current_drinker` | 현재 음주 여부 | boolean |

- 정답을 직접 결정하는 미래 진단·미래 약물·후속 조사값은 입력에서 제외한다.
- 사용자의 `checkup_id`만 작업 요청에 전달하고, Worker가 소유권이 확인된 검진에서 특성을 구성한다.
- artifact의 특성 이름·순서는 위 8개 항목과 정확히 같아야 한다.

## 2. API 계약

| 단계 | Method·Path | 핵심 요청·응답 |
|---|---|---|
| 건강정보 저장 | `POST /api/v1/health-checkups` | 검진·생활습관 입력 → `checkup_id`, `feature_schema_version` |
| 예측 접수 | `POST /api/v1/prediction-jobs` | `{checkup_id, model_key}` → HTTP 202, `job_id`, `status_url` |
| 상태 조회 | `GET /api/v1/prediction-jobs/{job_id}` | 상태·버전·`prediction_id` 또는 오류·재시도 정보 |
| 최신 결과 | `GET /api/v1/predictions/latest` | 결과 상태·공개 가능한 위험 범주·버전·면책 문구 |
| 결과 상세 | `GET /api/v1/predictions/{prediction_id}` | 검진·모델·특성·임계값 버전과 안전한 표시 결과 |
| 위험요인 | `GET /api/v1/predictions/{prediction_id}/risk-factors` | 검증 전 빈 목록과 미제공 안내, 검증 후 승인된 설명만 제공 |

## 3. 모델 artifact 계약

필수 메타데이터는 다음과 같다.

- `model_key`, `model_version`, `feature_schema_version`, `threshold_version`
- `outcome_definition`, `observation_horizon`, `model_population`
- 8개 `feature_columns`의 이름과 순서
- 전처리기와 모델의 재현 가능한 저장 형식
- Validation에서 선택한 임계값과 선택 근거
- Recall·Specificity·AUPRC·AUROC·F1·Brier 및 하위집단 성능
- artifact SHA-256 checksum과 롤백 모델 식별자

서비스 시작 시 계약이 다르면 추론하지 않고 명시적인 설정 오류로 중단한다.

## 4. DB 저장 계약

| 엔터티 | 최소 저장 내용 |
|---|---|
| `PredictionJob` (`ai_jobs`) | `job_id`, 사용자·검진 ID, 상태, 모델·특성·임계값 버전, 시각, 오류 코드, 재시도 정보 |
| `Prediction` | 작업·사용자·검진 ID, 목적, 결과 상태, 내부 점수, 위험 범주, 모든 버전, 모집단, 설명 상태, 예측 시각 |
| `RiskFactor` | 검증된 설명이 준비된 뒤 요인명·방향·중요도·수정 가능성·문구 버전 저장 |

- Redis는 큐와 빠른 상태 전달에 사용하고 DB는 감사·재현에 필요한 최소 이력을 보존한다.
- 원본 건강정보와 개인 식별정보를 큐 메시지·로그에 중복 저장하지 않는다.

## 5. 화면 상태 계약

| API 상태 | 화면 표시 |
|---|---|
| `queued` | 요청 접수·대기 중 |
| `running` | 분석 중, 중복 요청 방지 |
| `succeeded` + 승인 모델 | `낮음/주의/높음`, 모델 버전, 진단 아님 문구 |
| `succeeded` + 개발 모델 | 연결 완료·검토 중, 확률·범주 비공개 |
| `failed` | 실패 사유를 쉬운 문장으로 표시하고 `retryable`일 때만 재시도 안내 |

- API의 `low/caution/high`는 화면에서 `낮음/주의/높음`으로 변환한다.
- 내부 점수는 사용자에게 확정적 발병확률 또는 건강 개선율로 표현하지 않는다.
- 기진단·경고 증상 사용자는 예측 대신 의료진 지침·검사 안내를 먼저 표시한다.

## 6. 오류·안전 계약

- `403`: 동의·적합성·기진단 등 정책상 예측 불가
- `404`: 사용자 소유의 검진·작업·결과를 찾을 수 없음
- `422`: 누락·범위·특성 스키마 불일치
- `503`: Worker·Redis·artifact 설정 불가
- 비동기 시간초과: 상태 조회 HTTP 200, `status: failed`, `error_code: TIMEOUT`과 재시도 정보
- 약물 시작·중단·용량 변경, 진단·처방, 근거 없는 개인별 의료 조언은 제공하지 않는다.

