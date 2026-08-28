# Model Card: KLoSA RF25 당뇨 발생 위험 선별 후보

## 모델 식별

| 항목 | 값 |
| --- | --- |
| 모델 | Random Forest 25-feature candidate |
| 모델 버전 | `rf-25features-v001-run-20260825T045054926974Z` |
| 입력 스키마 | `diabetes-incidence-api-25features-v1` |
| 특성 스키마 | `klosa_stage3_25features_v1` |
| 임계값 버전 | `validation-recall-090-080-v1` |
| 실행 ID | `20260825T045054926974Z` |
| 상태 | 연구 후보, 운영 미승인 |
| SHA-256 | `7c07625d5bc4cb89203bfe34612b72655e709e7849f7f5ed00638af1c09a9c73` |

실제 모델은 Git 제외 경로
`outputs/ml/rf_25features_v001/20260825T045054926974Z/model.joblib`에 배치한다.
Manifest의 체크섬과 다르면 추론을 중단한다.

## 의도된 사용과 금지 용도

현재 당뇨병을 진단받지 않은 만 45~105세 사용자의 다음 KLoSA 조사 시점까지 신규
당뇨병 또는 고혈당 의사진단 위험을 선별하고 건강교육을 제공하기 위한 연구 후보이다.
생물학적 발병 시점이나 개인의 절대위험을 확정하지 않는다.

다음 용도로 사용하지 않는다.

- 당뇨병 확진·배제 진단 또는 처방
- 약물 시작·중단·용량 변경
- 응급도 판단이나 의료기관 방문 대체
- 보험·고용·대출 등 불이익 결정
- 기진단자, 만 45세 미만 또는 105세 초과 사용자 추론
- 체크섬·입력 순서·버전 검증을 우회한 모델 로드

## 데이터와 분할

- KLoSA 구조변환자료 1~10차, 2026-04-13 배포본
- 타깃: t0 비당뇨 응답자가 t1에 새로 보고한 당뇨병 또는 고혈당 의사진단
- PID 단위 70/15/15 분할, PID 사건 여부 층화, random state 42
- Train 36,304건/6,111명, Validation 7,605건/1,309명, Test 7,903건/1,310명
- Test 사건 195건, 분할 간 PID 중복 0

전처리와 변수 선택 통계는 Train에서만 학습하고 임계값은 Validation에서만 정한다.
Test는 확정된 모델과 임계값의 마지막 평가에만 사용한다.

## 입력과 전처리

모델 입력 순서는 후보 Manifest의 25개 `features`와
`src.ml.preprocessing.diabetes_api_features.STANDARD_MODEL_FEATURES`가 완전히 같아야 한다.

- 기본 8개: 연령, 성별, BMI, 흡연, 음주, 규칙적 운동, 운동일, 운동시간
- 기저질환 8개: 고혈압, 암, 만성폐질환, 간질환, 심장질환, 뇌혈관질환,
  정신과질환, 관절염·류머티즘
- 사회경제 4개: 로그 가구소득, 교육, 혼인, 가구형태
- 정신건강·생활리듬 5개: 건강·경제·삶 만족도, 우울감, 수면곤란

정확한 모델 입력 순서는 다음과 같다.

```text
age
sex
bmi
smoking_status
current_drinker
regular_exercise
exercise_days_per_week
exercise_minutes
hypertension_diagnosis
cancer_diagnosis
chronic_lung_disease_diagnosis
liver_disease_diagnosis
heart_disease_diagnosis
cerebrovascular_disease_diagnosis
psychiatric_disease_diagnosis
arthritis_rheumatism_diagnosis
log_household_income
education_level
marital_status
household_structure
health_satisfaction_score
economic_satisfaction_score
overall_quality_of_life_score
depressed_feeling_last_week
sleep_difficulty_last_week
```

API 필수 입력은 `birth_date`, `sex`, `height_cm`, `weight_kg`, `smoking_status`,
`current_drinker`, `regular_exercise`, `exercise_days_per_week`, `exercise_minutes`,
`previously_diagnosed_diabetes`다. 키는 120~220cm, 체중은 25~250kg, 운동일은
주 0~7일, 회당 운동시간은 0~720분으로 제한한다. `previously_diagnosed_diabetes`는
적격성 확인용이며 모델 특성이 아니다.

가구소득, 만족도 3개, 기저질환 8개, 교육·혼인·가구형태, 우울감과 수면곤란은
선택 입력이다. 전체 단위·허용값·결측 규칙의 실행 가능한 기준은
`src.ml.preprocessing.diabetes_api_features.API_INPUT_CONTRACT`다.

API는 키(cm)와 체중(kg)으로 BMI를 계산하고 연소득 만원 단위에 `log1p`를 적용한다.
규칙적 운동이 `false`이면 운동일과 운동시간은 구조적 0으로 변환한다. 선택 수치값은
`NaN`으로 전달한 뒤 Train 중앙값과 결측 indicator로 처리하며, 선택 범주값은 Train
최빈값으로 대치하고 One-Hot 인코딩한다. 진단 상태 `null`은 `no`로 간주하지 않는다.

현재·미래 당뇨 진단과 치료, t1·미래 변수, `target`, PID 및 HHID는 입력에서 제외한다.

## Recall 중심 성능

Validation Recall 0.80 이상 중 Specificity가 가장 높은 임계값 `0.022410835788097848`을
Test에 고정 적용했다.

| Recall | Specificity | AUROC | AUPRC | F1 | Brier |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.8000 | 0.4742 | 0.6596 | 0.0511 | 0.0708 | 0.02389 |

Test 혼동행렬은 TP 156, FN 39, TN 3,655, FP 4,053이다. Recall은 목표를 충족했지만
절반이 넘는 비사건이 양성으로 분류되고 AUPRC·F1이 낮다. 실험 Manifest의 Specificity
0.30은 연구 실행 하한일 뿐 운영 승인 기준이 아니다. 운영 전에는 최소 Specificity,
확률 보정, 시간·외부 검증과 하위집단 기준을 별도로 승인해야 한다.

## 출력 계약과 고정 입력

- `risk_score`: 소수점 12자리로 정규화한 연구용 RF 점수
- `low`: 점수 < `0.016719708895315412`
- `moderate`: 위 값 이상, `0.022410835788097848` 미만
- `high`: `0.022410835788097848` 이상
- 모델·입력·특성·임계값 버전과 적용 연령·안내 문구를 함께 반환

고정 입력 `inference_request.example.json`은 기준일 2026-08-26에 점수
`0.029554591894`, 범주 `high`를 반환한다. Golden 응답은
`inference_response.golden.json`이며 동일 아티팩트·입력·기준일에서 전체 JSON이 같아야 한다.

## 한계

- 타깃은 약 2년 후 생물학적 발병이 아니라 다음 조사에서 관측된 자기보고 의사진단이다.
- 사건률이 낮고 FP가 많아 운영 후속 조치 부담이 크다.
- Test가 과거 실험에서 반복 조회되어 완전히 미사용된 최종 holdout으로 보기 어렵다.
- KLoSA 중고령 표본, 패널 탈락, 자기보고·의료 접근성 편향이 있다.
- 확률 보정과 독립 외부검증이 없으며 모든 연령·성별·사회경제집단의 동일 성능을 보장하지 않는다.
- 위험 범주는 연구용이며 현재 운영 활성화 승인을 받지 않았다.

## 활성화 차단 및 롤백 기준

현재 모델은 `candidate_only`이므로 아래 운영 승인 조건을 충족하기 전 활성화하지 않는다.

### 즉시 차단·롤백

- 모델 파일 누락, SHA-256 불일치 또는 역직렬화 실패
- 모델·입력·특성·임계값 버전 또는 25개 특성 순서 불일치
- Golden 고정 입력의 전체 JSON 불일치
- 필수값·연령·기진단자 검증 우회 또는 진단·처방 금지 문구 누락
- 추론 실패 후 임의 기본 점수나 위험 범주를 반환하는 fallback 발생

### 성능 기반 재검토·롤백

- 승인된 라벨 평가창에서 Recall이 승인 하한 미만이거나 승인 시점 대비 0.05 이상 절대 하락
- Specificity가 승인 하한 미만이거나 승인 시점 대비 0.10 이상 절대 하락
- 주요 연령·성별 하위집단 Recall이 승인 하한보다 0.10 이상 낮음
- 입력 결측·범위 오류·점수 분포 이동으로 기존 보정과 임계값을 신뢰하기 어려움
- 의료 안전 검토에서 예상하지 못한 위해 또는 과도한 후속 검사 부담 확인

롤백은 애플리케이션 코드를 되돌리는 대신 `models/registry/diabetes_incidence/active.json`을
마지막으로 승인된 모델 버전과 체크섬으로 복원하고 서비스를 재시작한 뒤 Golden 추론을
재검증한다. 승인된 이전 모델이 없으면 artifact 추론을 비활성화하고 위험 점수를 생성하지
않는다. 모델 바이너리 삭제나 덮어쓰기로 롤백하지 않는다.

## 재현과 검증

```bash
./scripts/ml-experiment.sh validate
./scripts/ml-experiment.sh run rf_25features_v001
./scripts/ml-experiment.sh leaderboard
DIABETES_RF25_MODEL_PATH=outputs/ml/rf_25features_v001/20260825T045054926974Z/model.joblib \
  .venv/bin/pytest -q tests/ml/test_diabetes_standard_inference.py
```

후보 Manifest:
`models/registry/diabetes_incidence/candidates/rf_25features_v001-20260825T045054926974Z.json`
