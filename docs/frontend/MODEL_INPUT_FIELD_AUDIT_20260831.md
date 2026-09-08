# 모델 입력 필드 프론트엔드 임시 대조표

- 작성일: 2026-08-31
- 상태: **연구 후보 확인 / 운영 계약 미확정**
- 목적: 모델 연구 코드의 25개 후보와 현재 프론트·API 입력을 구분한다.

## 결론

현재 운영 코드의 예측 입력 계약은 8개이며, 연구 코드의 1위 후보 모델은 25개다. 두 계약은 기본 8개 구성부터 서로 다르므로 25개 필드를 프론트 건강정보 화면에 바로 추가하면 안 된다.

- 현재 운영 계약: `app/prediction/contracts.py`
- 25개 연구 후보: `ai_worker/ml/compare_klosa_top_balanced_model_weights.py`
- 연구 후보 상태: `research_class_weight_comparison_not_for_deployment`

## 1. 현재 운영 예측 입력 8개

| 모델 필드 | 프론트 원천 | 현재 상태 |
|---|---|---|
| `age` | 생년월일에서 계산 | 있음 |
| `bmi` | 키·몸무게에서 계산 | 있음 |
| `self_rated_health` | 주관적 건강상태 | 있음 |
| `meal_count_yesterday` | 어제 식사 횟수 | 있음 |
| `sex` | 프로필 성별 | 위치 결정 필요 |
| `regular_exercise` | 규칙적 운동 여부 | 있음 |
| `current_smoker` | 현재 흡연 여부 | 있음 |
| `current_drinker` | 현재 음주 여부 | 있음 |

## 2. 연구 후보 모델 25개

### 기본 8개

| 연구 필드 | 프론트 입력 가능성 | 확인 필요 사항 |
|---|---|---|
| `age` | 가능·파생 | 생년월일 저장 위치 |
| `sex` | 가능 | 성별 수집 필요성·위치 |
| `bmi` | 가능·파생 | 키·몸무게 범위 |
| `smoking_status` | 가능 | 현재 API의 `current_smoker` 불리언과 범주가 다름 |
| `current_drinker` | 가능 | 문항 기준 기간 필요 |
| `regular_exercise` | 가능 | 문항 정의 필요 |
| `exercise_days_per_week` | 추가 질문 필요 | 주당 횟수 범위 |
| `exercise_minutes` | 추가 질문 필요 | 1회 또는 주간 시간인지 정의 필요 |

### 기저시점 만성질환 8개

| 연구 필드 | 프론트 입력 가능성 | 확인 필요 사항 |
|---|---|---|
| `hypertension_diagnosis` | 가능 | 의료진 진단 기준 문구 |
| `cancer_diagnosis` | 민감·검토 필요 | MVP 수집 필요성 |
| `chronic_lung_disease_diagnosis` | 민감·검토 필요 | 질환 범위 정의 |
| `liver_disease_diagnosis` | 민감·검토 필요 | 질환 범위 정의 |
| `heart_disease_diagnosis` | 민감·검토 필요 | 질환 범위 정의 |
| `cerebrovascular_disease_diagnosis` | 민감·검토 필요 | 질환 범위 정의 |
| `psychiatric_disease_diagnosis` | 고민감·별도 검토 | 최소수집·안전 문구 |
| `arthritis_rheumatism_diagnosis` | 민감·검토 필요 | 질환 범위 정의 |

### 사회경제 4개

| 연구 필드 | 프론트 입력 가능성 | 확인 필요 사항 |
|---|---|---|
| `education_level` | 가능하나 검토 필요 | 예측 필요성과 선택지 |
| `marital_status` | 가능하나 검토 필요 | 최소수집 원칙 |
| `household_structure` | 가능하나 검토 필요 | 가구원 수에서 파생 여부 |
| `log_household_income` | 직접 입력 금지 | 원소득을 받을지, 수집 자체를 제외할지 결정 |

### 정신건강·수면·삶의 만족도 5개

| 연구 필드 | 프론트 입력 가능성 | 확인 필요 사항 |
|---|---|---|
| `health_satisfaction_score` | 추가 질문 필요 | 0~100 척도 설명 |
| `economic_satisfaction_score` | 민감·검토 필요 | 수집 필요성 |
| `overall_quality_of_life_score` | 추가 질문 필요 | 척도 설명 |
| `depressed_feeling_last_week` | 고민감·별도 검토 | 위기 대응·안내 문구 |
| `sleep_difficulty_last_week` | 가능 | 기간·빈도 선택지 |

## 3. 현재 건강정보 저장 API와의 차이

현재 `POST /health-checkups`는 키·몸무게·허리둘레·혈압·주관적 건강상태·식사 횟수·운동·흡연·음주 등을 받는다. 혈압과 허리둘레는 현재 저장·표시 항목이지만 운영 8개 모델 입력에는 포함되지 않는다.

따라서 화면 필드는 다음 세 종류로 구분해야 한다.

1. 사용자에게 보여주고 저장하는 건강정보
2. 실제 활성 모델에 전달하는 입력
3. 연구 후보에서만 사용하는 입력

## 4. 팀 확인 요청

- 최종 활성 모델이 현재 운영 8개인지 연구 후보 25개인지
- 25개 모델의 Artifact·SHA-256·스키마 버전
- 모든 25개가 실제 추론 필수값인지, 결측 허용·대체값이 있는지
- 고민감 정보와 사회경제 정보를 사용자에게 직접 받을지
- `smoking_status`와 `current_smoker` 중 표준 필드
- `exercise_days_per_week`, `exercise_minutes`의 단위와 허용 범위
- 연구용·운영 미승인 결과를 사용자 화면에서 차단하는 기준

## 5. 프론트 임시 원칙

- 최종 계약 수령 전 신규 17개 질문을 화면에 추가하지 않는다.
- 현재 입력 화면의 항목을 임의로 모델 입력이라고 표시하지 않는다.
- 검증되지 않은 점수·확률·위험요인을 만들지 않는다.
- 계약 확정 후 필수·선택·단위·범위·오류 메시지를 한 번에 반영한다.
