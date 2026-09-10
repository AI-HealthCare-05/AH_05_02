# 오늘이·내일이 변수 실험 및 설명가능성 분석 보고서

기준일: 2026-09-10. 아래 결과는 진단·처방이 아닌 위험 선별·건강교육 목적의
연구 결과다. 원자료, 개인별 예측값과 모델 바이너리는 Git에 포함하지 않는다.

본 보고서의 내일이 현재 제안 후보는 **17변수 재학습 RF(`rf17-refit-v1`)**다.
입력 부담을 줄이려는 요구를 반영한 후보 지정이며, RF25보다 성능이 우수하다는
의미는 아니다. RF25에서 8개를 결측 처리하고 17개만 입력하는 방식도 대안으로
함께 제시한다. 실제 서비스 Registry와 배포 모델의 변경은 이 보고서에 포함되지 않는다.

## 1. 비교 전에 구분할 점

| 구분 | 오늘이 | 내일이 |
|---|---|---|
| 과제 | KNHANES 조사 시점의 현재 당뇨 위험 선별 | KLoSA 다음 인접 조사까지 신규 의사진단 위험 선별 |
| 분할 | Train 2016~2020 / Validation 2021~2022 / Test 2023~2024 | PID 단위 70/15/15, seed 42 |
| Test | 9,691명, 양성 390명 | 7,903 person-period, 사건 195건 |
| 기준 모델 | Logistic 0.7 + RF 0.3, Train 연도 OOF Platt 보정 | 튜닝 비가중 RF |
| 임계값 | Validation Specificity 0.42 이상에서 Recall 최대 | 주로 Validation Specificity 0.43 이상에서 Recall 최대 |

라벨, 모집단, 사건률과 분할이 다르므로 오늘이와 내일이의 성능 수치를 직접 순위로
비교하지 않는다. 내일이의 과거 `Recall=0.80` 작동점과 현재 `Spec>=0.43` 작동점도
같은 점수 모델의 서로 다른 임계값일 수 있으므로 모델 구분력 개선과 임계값 효과를
구별해야 한다.

## 2. 오늘이 변수 실험

### 2.1 변수 구성

기존 v0.6.1을 흔히 26변수 모델이라고 부르지만, 정확히는 외부 입력 22개와 내부
허리둘레 파생 4개다.

| 외부 변수 | 설명·단위 | Shared7 포함 |
|---|---|---|
| `age` | 만 나이, 년 | 포함 |
| `height_cm` | 키, cm | 포함 |
| `weight_kg` | 체중, kg | 포함 |
| `waist_cm` | 허리둘레 실측값, cm. 결측이면 추정기 적용 | 제외 |
| `bmi` | 체질량지수, kg/m². 체중÷키(m)² | 포함 |
| `walking_days` | 걷기 실천 일수, 일/주 | 제외 |
| `energy_kcal` | 식이조사 에너지 섭취량, kcal | 제외 |
| `protein_g` | 식이조사 단백질 섭취량, g | 제외 |
| `fat_g` | 식이조사 지방 섭취량, g | 제외 |
| `carbohydrate_g` | 식이조사 탄수화물 섭취량, g | 제외 |
| `sodium_mg` | 식이조사 나트륨 섭취량, mg | 제외 |
| `sex` | 성별, KNHANES 범주 코드 | 포함 |
| `region` | 거주 지역 구분 코드 | 제외 |
| `urban` | 도시·농촌 등 거주지역 유형 코드 | 제외 |
| `education` | 교육 수준 구분 코드 | 포함 |
| `income_quartile` | 개인 소득 사분위 구분 | 제외 |
| `household_income_quartile` | 가구 소득 사분위 구분 | 제외 |
| `hypertension_family_history` | 고혈압 가족력 여부 | 제외 |
| `diabetes_family_history` | 당뇨병 가족력 여부 | 제외 |
| `current_smoker` | 현재 흡연 여부 | 포함 |
| `alcohol_frequency` | 음주 빈도 응답 범주 | 제외 |
| `aerobic_activity` | 유산소 신체활동 실천 여부 | 제외 |

| 내부 파생변수 | 설명·단위 |
|---|---|
| `waist_height_ratio` | 허리둘레÷키, 두 값 모두 cm로 계산한 비율 |
| `waist_was_estimated` | 허리둘레 결측 대체 여부, 실측 0·추정 1 |
| `waist_expected_cm` | 키·체중·나이·성별로 추정한 기대 허리둘레, cm |
| `waist_minus_expected_cm` | 실측 또는 대체 허리둘레−기대 허리둘레, cm. 대체 행은 0 |

범주형 값은 학습 전처리기의 코드 체계를 따른다. Shared7의 BMI는 내부 계산이
가능하므로 7개 모델 특성이 곧 사용자 질문 7개를 의미하지 않는다.

### 2.2 축소·추가 실험 결과

| 구성 | 외부 입력 | Validation R/S | Test R/S | Test AUROC | Test AUPRC | FN/FP |
|---|---:|---:|---:|---:|---:|---:|
| 기존 v0.6.1 | 22 | .9590/.4201 | .9385/.4066 | .7712 | .1138 | 24/5,519 |
| 공통 입력 | 7 | .9422/.4202 | .9308/.4131 | .7602 | .1060 | 27/5,459 |
| 공통+허리둘레 | 8 | .9349/.4303 | .9333/.4252 | .7706 | .1172 | 26/5,346 |
| 공통+당뇨 가족력 | 8 | .9446/.4420 | .9205/.4269 | .7639 | .1053 | 31/5,330 |
| 공통+허리둘레+가족력 | 9 | .9518/.4482 | .9205/.4400 | .7754 | .1171 | 31/5,209 |
| 교육 제외 | 6 | .9446/.4212 | .9256/.4173 | .7589 | .1048 | 29/5,420 |

공통 7개는 기존 대비 Test Recall이 0.77%p 낮고 FN이 3건 늘었지만 입력을 크게
줄였다. 허리둘레를 추가한 8개는 Recall 손실이 0.51%p로 줄고 FP도 173건 감소했다.
교육 제외 6개는 Validation Recall이 소폭 높았으나 Test Recall과 AUROC/AUPRC가
낮아 동등 성능으로 확정할 수 없다.

서비스 재현 환경(scikit-learn 1.8)의 공통 7개 결과는 Validation R/S
`.9373/.4254`, Test R/S `.9333/.4194`, AUROC `.7602`, AUPRC `.1061`이다.
이는 라이브러리 버전 통일 재현값이며 모델 버전은
`knhanes-shared7-sk180-research-v1`이다.

### 2.3 오늘이 결론

- 질문 수 최소화 기준: 공통 7개.
- 추가 입력 1개를 허용할 때: 허리둘레가 가장 설득력 있는 후보다.
- 허리둘레·가족력 9개는 Validation과 Test Specificity가 가장 높지만 Test Recall은
  공통 7개보다 낮았다.
- 서비스 연령 45~105세에서 별도 Test Specificity가 `.2169`였으므로 전체 성인
  `.4194`를 서비스 연령 성능으로 오해하면 안 된다. 오늘이는 아직 운영 승인 전이다.

### 2.4 허리둘레 결측 추정기

기존 v0.6.1과 허리둘레 포함 축소 후보에는 `AnthropometricWaistEstimator`가 포함된다.
Shared7에는 추정기와 허리둘레 파생 4개가 모두 제외된다.

| 순서 | 추정기 입력 | 단위·처리 |
|---:|---|---|
| 1 | `height_cm` | 키, cm |
| 2 | `weight_kg` | 체중, kg |
| 3 | `age` | 나이, 년 |
| 4 | `sex` | 학습 데이터와 동일한 수치 코드 |

BMI는 추정기에 직접 입력하지 않는다. 앞선 대화의 `sex="male"` JSON 예시는
이 추정기의 직접 입력 규격으로 사용할 수 없다. 서비스 문자열은 학습 코드로
변환해야 하며, 해당 추정기는 수치형 중앙값 대치를 적용한다.

- 학습 목표: Train에서 실제 관찰된 `waist_cm`.
- 모델: HistGradientBoostingRegressor, learning_rate 0.05, max_iter 180,
  max_leaf_nodes 15, min_samples_leaf 30, l2_regularization 2.0.
- 추정기 입력 결측은 학습부 중앙값과 결측 indicator로 처리한다.
- 관측 허리둘레가 100건 이상이면 회귀기를 학습한다. 부족하면 학습부 허리둘레
  중앙값을 사용하고, 관측 허리둘레가 전혀 없으면 오류를 발생시킨다.
- 예상 허리둘레는 45~160cm로 제한한다. 이 범위 제한은 예상값에 적용되며
  실측값 검증을 대신하지 않는다.
- 실측값은 유지하고 `waist_cm`이 결측인 행만 예상값으로 채운다.
- 파생값: `waist_height_ratio=waist_cm/height_cm`, `waist_was_estimated`,
  `waist_expected_cm`, `waist_minus_expected_cm=waist_cm-waist_expected_cm`.
  결측 대체 행에서는 마지막 잔차가 0이다.

추정기는 fold 학습부에서만 적합한다. 허리둘레 포함 모델의 기존 성능은 실측과
자연 결측이 섞인 평가 결과이며, 모든 사용자의 허리둘레를 추정했을 때 같은
성능을 보장하지 않는다.

근거 코드는 `src/ml/modeling/transformers.py`, 설정은
`configs/knhanes_current_screening_recall_v061.json`에 있다.

## 3. 내일이 변수 확장 실험

### 3.1 8개에서 45개까지 단계별 확장

| 단계 | 변수 구성 | 대표 결과와 판단 |
|---|---|---|
| 기본 8 | 나이·성별·BMI·흡연·음주·규칙적 운동·운동일·운동시간 | 비가중 RF Test R/S `.7744/.3900`, AUROC `.6245`, AUPRC `.0370` |
| 16 | 기본 8 + 기저질환 8개 | RF Test R/S `.8000/.4124`, AUROC `.6485`, AUPRC `.0415`; 증분 신호 확인 |
| 20 | + 교육·소득·가구 형태·혼인 | RF Test R/S `.7744/.4547`, AUROC `.6511`, AUPRC `.0437`; Recall 개선 불일치 |
| 25 | + 우울·수면·건강/경제/삶 만족도 | RF Test R/S `.8000/.4742`, AUROC `.6596`, AUPRC `.0511`; 균형 기준 채택 |
| 30 | + ADL/IADL·악력·낙상·이동 독립성 | RF `.8051/.4569`; XGBoost `.8103/.4131`; RF25 대비 효율 불충분 |
| 36 | + 이전 차수 BMI·운동·흡연·음주 변화 | 축소 연속관찰 코호트에서 RF30 `.8480/.3434` 대 RF36 `.8363/.3362`; 채택 안 함 |
| 45 | + 최근 3개 조사 추세 | 별도 wave3+ 코호트에서 RF36 `.8425/.4014` 대 RF45 `.8425/.3805`; 채택 안 함 |

36·45변수 결과는 이전 차수 관찰이 가능한 축소 코호트이므로 전체 25변수 결과와
직접 비교하지 않는다.

### 3.2 표준 RF25와 변수 목록

기존 서비스 연동 기준 모델 `rf25-tuned-spec40-v1`은 다음 25개를 고정 순서로 쓴다.

| 순서 | 변수 | 설명·단위 | RF17 |
|---:|---|---|---|
| 1 | `age` | 기저시점 만 나이, 년 | 유지 |
| 2 | `bmi` | 체질량지수, kg/m² | 유지 |
| 3 | `exercise_days_per_week` | 주당 운동 일수, 일/주 | 유지 |
| 4 | `exercise_minutes` | 1회 운동시간, 분/회 | 유지 |
| 5 | `log_household_income` | 가구소득에 log(1+소득)을 적용한 수치. 원소득 단위는 학습 규격 준수 | 유지 |
| 6 | `health_satisfaction_score` | 자신의 건강에 대한 만족도, 0~100점 | 유지 |
| 7 | `economic_satisfaction_score` | 자신의 경제 상태에 대한 만족도, 0~100점 | 유지 |
| 8 | `overall_quality_of_life_score` | 전반적인 삶의 질 만족도, 0~100점 | 유지 |
| 9 | `sex` | 성별 | 유지 |
| 10 | `smoking_status` | 현재·과거·비흡연 등 흡연 상태 | 유지 |
| 11 | `current_drinker` | 현재 음주 여부. 음주량·빈도와 구별 | 제외 |
| 12 | `regular_exercise` | 규칙적 운동 실천 여부 | 유지 |
| 13 | `hypertension_diagnosis` | 고혈압 의사진단 여부 | 유지 |
| 14 | `cancer_diagnosis` | 암 의사진단 여부 | 제외 |
| 15 | `chronic_lung_disease_diagnosis` | 만성 폐질환 의사진단 여부 | 제외 |
| 16 | `liver_disease_diagnosis` | 간질환 의사진단 여부 | 제외 |
| 17 | `heart_disease_diagnosis` | 심장질환 의사진단 여부 | 제외 |
| 18 | `cerebrovascular_disease_diagnosis` | 뇌혈관질환 의사진단 여부 | 제외 |
| 19 | `psychiatric_disease_diagnosis` | 정신과 질환 의사진단 여부. 우울감 설문과 별개 | 제외 |
| 20 | `arthritis_rheumatism_diagnosis` | 관절염·류머티즘 의사진단 여부 | 유지 |
| 21 | `education_level` | 최종 교육 수준 범주 | 유지 |
| 22 | `marital_status` | 혼인 상태 범주 | 유지 |
| 23 | `household_structure` | 1인 가구·다인 가구 구분 | 제외 |
| 24 | `depressed_feeling_last_week` | 지난 일주일 우울감 경험에 관한 응답 범주 | 유지 |
| 25 | `sleep_difficulty_last_week` | 지난 일주일 수면 어려움에 관한 응답 범주 | 유지 |

질환 여부의 미응답은 '아니오'가 아니라 결측으로 유지한다. 범주형 코드와
규칙적 운동의 설문 정의는 KLoSA 입력 계약을 따른다.

튜닝값은 RF 500 trees, `max_depth=8`, `min_samples_leaf=39`,
`max_samples=0.7`, `criterion=log_loss`, `ccp_alpha=0.00001`,
`bootstrap=True`, `max_features=sqrt`, 무가중이다. 임계값
`0.021153602801262862`에서 Validation R/S `.8256/.4337`, Test R/S
`.8410/.4024`, AUROC `.6636`, AUPRC `.0485`, TP/FN/TN/FP
`164/31/3102/4606`이다.

## 4. 내일이 축소·제거 실험

### 4.1 OOF 중요도 기반 25→20→15→10

Train 내부 nested PID OOF에서 fold 안쪽 permutation importance로만 변수를 골랐다.

| 변수 수 | OOF Recall | OOF Specificity | AUROC | AUPRC |
|---:|---:|---:|---:|---:|
| 25 | .8000 | .3614 | .6307 | .0405 |
| 20 | .8000 | .3357 | .6267 | .0422 |
| 15 | .8000 | .3286 | .6249 | .0425 |
| 10 | .8000 | .3317 | .6252 | .0419 |

BMI와 나이만 안정성 점수가 명확히 양수였지만, 약한 결합 신호를 한꺼번에 제거하자
Specificity가 하락해 25개 유지로 결론 냈다.

### 4.2 단일 제거, 음주 제외 후 추가 제거, 2개 조합 전수 탐색

- RF25 단일 제거 25회: Validation 선택은 `exercise_days_per_week` 제거였으나
  Test R/S `.8359/.3997`로 Test Specificity 0.40에 미달했다.
- `current_drinker`만 제거한 RF24: Test Recall `.8410`을 유지하며 Specificity가
  `.4085`로 높아졌지만 사후 Test 관찰이다.
- RF24에서 나머지 24개를 하나씩 더 제거: Validation은 `regular_exercise` 제거를
  선택했으나 Test R/S `.8256/.3973`; 채택하지 않았다.
- 25개 중 2개 제거 전 조합 300개: Train PID OOF 두 seed 평균으로
  `education_level`+`health_satisfaction_score` 제거가 선택됐다. Validation
  `.8359/.4370`, Test `.8103/.4124`, AUROC `.6582`, AUPRC `.0474`로 표준 RF25의
  Recall을 넘지 못했다.
- 사전 지정 `psychiatric_disease_diagnosis`,
  `cerebrovascular_disease_diagnosis`, `exercise_minutes` 개별·조합 제거도 OOF seed
  모두에서 RF25를 일관되게 개선하지 못했다.

다중 비교와 반복 조회된 Test의 선택 편향 때문에 위 결과로 변수를 인과적으로
불필요하다고 결론 내리지 않는다.

### 4.3 입력 부담 축소 실험

삭제 우선 8개는 `current_drinker`, `liver_disease_diagnosis`,
`psychiatric_disease_diagnosis`, `cancer_diagnosis`, `household_structure`,
`cerebrovascular_disease_diagnosis`, `heart_disease_diagnosis`,
`chronic_lung_disease_diagnosis`로 두었다.

| 방식 | Validation R/S | Test R/S | Test AUROC | Test AUPRC | 해석 |
|---|---:|---:|---:|---:|---|
| RF17로 재학습 | .8154/.4614 | .8103/.4259 | .6583 | .0458 | 입력 8개 제거, Recall 감소 |
| 기존 RF25에 8개를 NaN | .8154/.4351 | .8359/.4002 | .6597 | .0496 | 기존 최빈/중앙 대치 경로, 경계 여유 작음 |
| RF25 명시적 missing 학습 후 8개 NaN | .8308/.4426 | .8051/.4094 | .6558 | .0475 | Validation은 양호하나 Test Recall 감소 |
| Shared5로 재학습 | .7795/.4310 | .7692/.3976 | .6280 | .0387 | 입력 최소화 손실 큼 |
| Shared7로 재학습 | .7795/.4381 | .7385/.4104 | .6243 | .0398 | 키·체중 추가도 Recall 개선 없음 |

Shared5는 `age`, `sex`, `bmi`, `smoking_status`, `education_level`이다.
Shared7은 여기에 `height_cm`, `weight_kg`을 직접 추가한 모델이다. 내일이 원 RF25는
키·체중을 직접 사용하지 않고 BMI만 사용하므로 Shared7은 단순 입력 매핑이 아니라
새 모델 재학습 실험이다.

## 5. 내일이 결측·파생변수 실험

### 5.1 결측 처리

- 표준 RF25: 수치형은 Train 중앙값, 범주형은 Train 최빈값, one-hot encoding.
- 수치형은 학습 당시 결측이 있던 열에 missing indicator가 붙는다.
- 명시적 missing 실험은 범주형 결측을 최빈값에 합치지 않고
  `__MISSING__` one-hot 범주로 보존한다.
- 어떤 경우에도 Validation/Test를 포함한 전체 데이터로 대치 통계를 학습하지 않는다.

### 5.2 명시적 missing·운동량·질환 요약

| 변형 | Train OOF R/S | Validation R/S | Test R/S | 판단 |
|---|---:|---:|---:|---|
| 튜닝 RF25 최빈값 | .7692/.4013 | .8256/.4337 | .8410/.4024 | 현행 후보 |
| 튜닝 RF25 명시적 missing | .7626/.4010 | .8154/.4471 | .8256/.4158 | Specificity↑, Recall↓ |
| 튜닝 RF26 missing+주간 운동량 | .7703/.4004 | .8205/.4321 | .8359/.4028 | OOF 선택이나 Test 개선 불일치 |

주간 운동량은 `exercise_days_per_week × exercise_minutes`(분/주)다. 초기 leaf 20
실험에서도 missing+주간 운동량은 Test R/S `.8256/.4346`이었으나 기준 RF25
`.8000/.4742`보다 AUROC/AUPRC가 낮았다. 기저질환 개수와 심혈관 질환군 요약을
추가한 27·28변수도 Validation 선택 규칙에서 RF25를 대체하지 못했다.

### 5.3 다른 파생 후보

- KLoSA 핵심 후보 순차 추가: 체중 변화, 상대 악력, 운동 지속기간, 식사 규칙성,
  상세 흡연·음주 부담. OOF는 체중 변화 26개(B)를 골랐지만 Test `.8103/.4687`,
  AUROC `.6592`, AUPRC `.0498`로 RF25를 확실히 개선하지 못했다.
- 운동·비만 상호작용, 정신건강 축약, 심혈관·대사 상호작용: OOF/Validation 선택
  기준에서 원 25개를 일관되게 넘지 못했다.
- BMI 지속성 6개, 운동 지속성 5개, 종단 변화·추세: 관찰 가능한 차수만 남아
  코호트가 달라지고 일관된 증분 성능이 없어 표준 입력에 채택하지 않았다.

## 6. 현재 후보 상세 및 SHAP 분석

### 6.1 RF17 재학습과 RF25 8개 결측 입력 비교

두 방식 모두 사용자가 제공하는 모델 특성은 17개다. 전자는 학습 특성 자체를
17개로 줄이고, 후자는 25개 학습 모델의 입력 열을 유지하면서 8개를 NaN으로 채운다.
8개 결측 처리 모델이라는 표현은 8변수로 학습한 모델을 의미하지 않는다.

| 항목 | 현재 후보: RF17 재학습 | 대안: RF25의 8개 결측 입력 |
|---|---|---|
| 학습 변수 수 | 17 | 25 |
| 실제 제공 변수 수 | 17 | 17 |
| 학습 | 전처리기·RF 모두 Train에서 재학습 | 기존 RF25와 전처리기 유지 |
| 범주형 결측 | Train 최빈값 | 기존 Train 최빈값 |
| 임계값 | 0.0216135233 | 0.0208020684 |
| 임계값 규칙 | Validation Spec≥0.43에서 Recall 최대 | 같은 규칙, 8개 NaN 조건 Validation 사용 |
| Validation R/S | .8154/.4614 | .8154/.4351 |
| Test R/S | .8103/.4259 | .8359/.4002 |
| Test AUROC/AUPRC | .6583/.0458 | .6597/.0496 |
| Test TP/FN/TN/FP | 158/37/3283/4425 | 163/32/3085/4623 |

RF25 8개 결측 대안은 기존 임계값 0.0211536028을 그대로 쓸 때 Test R/S가
`.8359/.4175`다. 조정 임계값은 Validation 규칙에 따라 선택한 값이며,
Test Specificity가 더 높은 기존 임계값으로 사후 교체하지 않는다.
명시적 `__MISSING__`로 다시 학습한 별도 대안은 앞 표의 `.8051/.4094`로,
기존 최빈값 대치 대안과 구별한다.

RF17 유지 변수는 3.2절 표에서 '유지'로 표시한 17개다. 신체·생활습관은
나이, 성별, BMI, 흡연, 규칙적 운동, 운동일, 운동시간이며, 질환은 고혈압과
관절염·류머티즘이다. 사회경제 변수는 로그 가구소득, 교육 수준, 혼인 상태,
정신건강·웰빙 변수는 건강·경제·삶 만족도, 지난 일주일 우울감과 수면 어려움이다.
실제 추론 열 순서는 각 Artifact의 `features`를 따른다.

RF17 Artifact:
`outputs/ml/rf_17features_v001/20260910T004604353702Z/model.joblib`.
버전은 `rf17-refit-v1`, 입력 스키마는 `klosa_17features_v1`이다.
저장 후 재로딩한 고정 3행 예측 일치를 확인한 기록이 있다. 별도 운영 승인 및
서비스 API의 17개 입력 계약 반영은 완료된 것으로 간주하지 않는다.

### 6.2 TreeSHAP 결과

분석 대상은 **기존 RF25**다. 고정 Test에서 seed 42로 추출한 1,000건에
`TreeSHAP tree_path_dependent`를 적용했다. one-hot 및 결측 indicator 기여값을
원 변수로 합친 뒤 평균 절대 기여도를 산출했다. 기준 점수와 모든 SHAP 기여값의
합이 모델 점수와 일치하는 가산성 검증을 통과했다.

| 순위 | 변수 | 평균 절대 SHAP |
|---:|---|---:|
| 1 | 고혈압 진단 | .004561 |
| 2 | BMI | .003050 |
| 3 | 나이 | .002284 |
| 4 | 로그 가구소득 | .001497 |
| 5 | 관절염·류머티즘 | .001196 |
| 6 | 건강 만족도 | .001050 |
| 7 | 흡연 상태 | .000683 |
| 8 | 수면 어려움 | .000632 |
| 9 | 혼인 상태 | .000564 |
| 10 | 삶의 만족도 | .000527 |
| 18 | 만성 폐질환 | .000295 |
| 19 | 심장질환 | .000250 |
| 20 | 뇌혈관질환 | .000250 |
| 21 | 현재 음주 | .000178 |
| 22 | 가구 형태 | .000122 |
| 23 | 암 | .000058 |
| 24 | 정신과 질환 | .000051 |
| 25 | 간질환 | .000037 |

평균 절대 SHAP은 영향의 크기를 나타내며 위험 증가·감소 방향을 뜻하지 않는다.
사용자 입력에 따라 개인별 기여값과 방향은 바뀐다. 예를 들어 `.004561`은
모델 원시 점수 척도의 평균 절대 기여량이며 실제 발병률이 그만큼 증가했다는
의미가 아니다. 상관된 변수 간 기여도 분산도 고려해야 한다.

하위 8개는 RF17에서 제외한 8개와 일치해 입력 축소의 참고 근거가 된다.
하지만 SHAP 중요도가 낮다고 제거 후 성능 유지가 보장되는 것은 아니며, RF17
재학습에서는 Test FN이 증가했다. 오늘이와 RF17 자체의 SHAP 분석은 이 보고서에
인용한 산출물에는 없으므로 RF25 SHAP을 두 모델의 설명으로 전용하지 않는다.

전체 순위·그림은 `outputs/ml/rf25_shap_analysis/global_feature_importance.csv`와
`global_feature_importance.png`에 있다. 개인별 실제 입력이 포함된
`local_explanations.json`은 Git 제외 상태로 유지하고 본 보고서에는 옮기지 않는다.

## 7. 현재 판단

1. 오늘이는 서비스 입력 호환성을 우선하면 공통 7개가 실용적이나, 허리둘레 1개
   추가 후보가 성능상 가치가 있다.
2. 내일이 현재 제안 후보는 입력 편의를 반영한 `rf17-refit-v1`이다.
   `rf25-tuned-spec40-v1`은 기존 성능 비교 기준으로 유지한다.
3. RF17은 Test Recall이 `.8410→.8103`으로 낮아지고 Specificity는
   `.4024→.4259`로 높아진다. FN은 31→37, FP는 4,606→4,425다.
4. 선택 8개를 단순 미입력 처리하면 분포 이동이 발생한다. 결측 대치가 실행된다는
   사실은 성능 보장을 뜻하지 않는다.
5. 음주 제거 RF24는 유망한 사후 신호지만 독립 holdout 또는 nested PID CV 없이
   RF25를 교체할 근거는 부족하다.
6. 같은 historical Test를 반복 조회했으므로 앞으로의 모델 선택은 Test가 아니라
   Train nested PID OOF와 사전 고정 Validation 규칙으로 끝내고 새 외부 검증을 둔다.

## 8. 재현 코드

모든 명령은 저장소 루트에서 실행한다. Git 제외 KLoSA/KNHANES 데이터와 필요한
Artifact가 로컬에 있어야 하며, 새 출력 폴더를 사용한다.

### 오늘이

```bash
# 22개 기준과 공통 7/8/9개 비교
.venv/bin/python -m src.ml.evaluation.compare_knhanes_shared_inputs \
  --handoff-dir /path/to/today_v061_team \
  --output-dir outputs/ml/knhanes_shared_inputs_v001/<new-run>

# 교육 제거 6개 포함
.venv/bin/python -m src.ml.evaluation.compare_knhanes_shared_inputs \
  --handoff-dir /path/to/today_v061_team \
  --output-dir outputs/ml/knhanes_shared_inputs_v001/<new-run> \
  --education-ablation

# scikit-learn 1.8 공통 7개 재현
.venv/bin/python -m src.ml.evaluation.reproduce_knhanes_shared7_sk180 \
  --handoff-dir /path/to/today_v061_team \
  --output-dir outputs/ml/knhanes_shared7_sk180_v001/<new-run>

.venv/bin/python -m pytest -q \
  tests/ml/test_knhanes_shared_inputs.py \
  tests/ml/test_knhanes_sk180_reproduction.py
```

### 내일이

```bash
./scripts/ml-experiment.sh validate

# 표준 RF25와 OOF 축소
./scripts/ml-experiment.sh run rf_25features_tuned_spec40_v001
./scripts/ml-experiment.sh run rf_oof_feature_reduction_v001

# 단일·사전 지정·2개 조합 제거
./scripts/ml-experiment.sh run rf25_leave_one_out_v001
./scripts/ml-experiment.sh run rf_targeted_feature_removal_v001
./scripts/ml-experiment.sh run rf24_no_alcohol_leave_one_out_v001
./scripts/ml-experiment.sh run rf25_pair_removal_oof_v001

# 명시적 결측과 파생변수
./scripts/ml-experiment.sh run rf_missing_weekly_comorbidity_v001
./scripts/ml-experiment.sh run pid_oof_tuned_rf_missing_weekly_v001
./scripts/ml-experiment.sh run rf_activity_adiposity_interactions_v001
./scripts/ml-experiment.sh run rf_mental_health_compact_features_v001
./scripts/ml-experiment.sh run rf_cardiometabolic_interactions_v001
./scripts/ml-experiment.sh run rf_klosa_core_candidates_v001

# 입력 축소 재학습 및 결측 입력 비교
./scripts/ml-experiment.sh run rf_shared5_v001
./scripts/ml-experiment.sh run rf_shared7_anthropometric_v001
./scripts/ml-experiment.sh run rf_17features_v001
./scripts/ml-experiment.sh run rf25_17input_imputed_v001
./scripts/ml-experiment.sh run rf25_explicit_missing_17input_v001
uv run python -m src.ml.evaluation.compare_minimal_input_spec40

./scripts/ml-experiment.sh leaderboard
.venv/bin/python -m pytest -q tests/ml
```

각 실행의 `experiment.json`이 데이터·분할·특성 스키마를 고정하고,
`pipeline.py:run_experiment`가 실제 재현 진입점이다. 결과와 Artifact는
`outputs/ml/<experiment-id>/<UTC-run-id>/`에 생성되며 `outputs/`와
`models/artifacts/`는 Git에 커밋하지 않는다.

### RF25 8개 결측 입력 대안 재평가

다음 코드는 학습된 RF25를 유지하고 Validation에서 임계값을 정한 뒤 Test를
평가한다. 기존 모델 파일과 공통 데이터가 준비된 환경에서 실행한다.

```python
import joblib
import numpy as np
import pandas as pd
from src.ml.evaluation.audit_service_release import metrics, select
from src.ml.modeling.train_klosa_diabetes_pooled import split_grouped_cohort
from src.ml.preprocessing.build_klosa_diabetes_cohort import TARGET

bundle = joblib.load("models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1/model.joblib")
pipeline = bundle["pipeline"]
pipeline.set_params(classifier__n_jobs=1)
removed = [
    "current_drinker", "liver_disease_diagnosis",
    "psychiatric_disease_diagnosis", "cancer_diagnosis",
    "household_structure", "cerebrovascular_disease_diagnosis",
    "heart_disease_diagnosis", "chronic_lung_disease_diagnosis",
]
data = pd.read_pickle("data/processed/official_v1/klosa_diabetes_incidence_stage3_25features_v1.pkl")
_, validation, test = split_grouped_cohort(data, random_state=42)

def masked_scores(frame):
    x = frame[bundle["features"]].copy()
    x[removed] = np.nan
    return pipeline.predict_proba(x)[:, 1]

vp = masked_scores(validation)
threshold = select(validation[TARGET].to_numpy(int), vp, 0.43)
print("validation", metrics(validation[TARGET].to_numpy(int), vp, threshold))
tp = masked_scores(test)
print("test_adjusted", metrics(test[TARGET].to_numpy(int), tp, threshold))
print("test_fixed", metrics(test[TARGET].to_numpy(int), tp, bundle["threshold"]))
```

### RF25 SHAP 재현

```bash
.venv/bin/python -m src.ml.evaluation.analyze_rf25_shap \
  --sample-size 1000 \
  --output outputs/ml/rf25_shap_analysis_reproduction
```

SHAP 설치 환경이 필요하다. 기본 모델은 RF25이며 RF17의 결과는 별도 실행과
검증 후 보고해야 한다. 개인별 설명 결과는 Git 제외 경로에만 저장한다.

## 9. 상세 근거 문서

- `docs/model/KNHANES_SHARED_INPUT_COMPARISON.md`
- `docs/model/KNHANES_SHARED7_SK180_REPRODUCTION.md`
- `docs/model/CURRENT_MODEL_PERFORMANCE.md`
- `docs/model/MINIMAL_INPUT_VALIDATION_SPEC40_COMPARISON.md`
- `docs/model/RF25_LEAVE_ONE_OUT_20260907.md`
- `docs/model/RF24_NO_ALCOHOL_LEAVE_ONE_OUT_20260907.md`
- `experiments/diabetes_incidence/candidates/rf_oof_feature_reduction_v001/README.md`
- `experiments/diabetes_incidence/candidates/pid_oof_tuned_rf_missing_weekly_v001/README.md`
- `experiments/diabetes_incidence/candidates/rf_17features_v001/README.md`
- `experiments/diabetes_incidence/candidates/rf25_explicit_missing_17input_v001/README.md`
