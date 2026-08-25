# rf_25features_v001

- 담당자: 양준혁
- 상태: 연구용 후보, 운영 미승인
- 목적: 진단·처방이 아닌 당뇨 발생 위험 선별과 건강교육

## 실험 가설

KLoSA t0에서 관찰된 25개 변수와 비가중 Random Forest를 사용하면 Validation Recall 0.80을 만족하는 작동점에서 최소 Specificity 0.30을 확보할 수 있다.

## 사용 데이터와 입력 변수

- 데이터: `data/processed/official_v1/klosa_diabetes_incidence_stage3_25features_v1.pkl` (행 단위 자료, Git 제외)
- 원천 버전: KLoSA structured waves 1~10, 2026-04-13 배포본
- 데이터 버전: `official_v1`
- 분할 버전: `pid_group_70_15_15_stratified_any_event_rs42_v1`
- 입력 스키마: `klosa_stage3_25features_v1`
- 분할: PID의 전체 관측기간 중 사건 발생 여부로 층화한 PID 단위 Train/Validation/Test 70/15/15, random state 42

입력 25개:

1. 기본 8개: `age`, `sex`, `bmi`, `smoking_status`, `current_drinker`, `regular_exercise`, `exercise_days_per_week`, `exercise_minutes`
2. t0 기저질환 8개: `hypertension_diagnosis`, `cancer_diagnosis`, `chronic_lung_disease_diagnosis`, `liver_disease_diagnosis`, `heart_disease_diagnosis`, `cerebrovascular_disease_diagnosis`, `psychiatric_disease_diagnosis`, `arthritis_rheumatism_diagnosis`
3. 사회경제 4개: `log_household_income`, `education_level`, `marital_status`, `household_structure`
4. 정신건강·생활리듬 5개: `health_satisfaction_score`, `economic_satisfaction_score`, `overall_quality_of_life_score`, `depressed_feeling_last_week`, `sleep_difficulty_last_week`

## 제외 변수와 데이터 누수 기준

- 다음 조사차수(t1)의 모든 입력과 미래 시점 변수: 미래 정보 누수 방지
- 현재·미래 당뇨 진단, 고혈당 진단 및 당뇨 치료 변수: 정답 직접 노출 방지
- `target`, `pid`, `hhid`: 정답 또는 식별자 누수 방지
- 동일 PID는 세 분할 중 하나에만 포함한다.
- 수치형 중앙값·결측 indicator와 범주형 최빈값·One-Hot 변환은 sklearn Pipeline 내부에서 Train에만 적합한다.
- 임계값은 Validation에서만 선택하고 Test는 확정 후 마지막 평가에만 사용한다.

t0의 비당뇨 기저질환 변수는 예측 시점에 이미 관찰된 건강상태이므로 포함한다. 이 변수들은 목표 당뇨의 현재·미래 진단 또는 치료 변수가 아니다.

## 모델과 하이퍼파라미터

- `RandomForestClassifier`
- `n_estimators=500`
- `max_depth=8`
- `min_samples_leaf=20`
- `max_features="sqrt"`
- `class_weight=None`
- `n_jobs=-1`
- `random_state=42`

## 임계값 결정 방법

Train 학습 완료 후 Validation Recall 0.80 이상을 만족하는 후보 중 Specificity가 가장 높은 임계값을 선택한다. Test는 임계값 선택에 사용하지 않는다.

## 평가 결과

### 기존 점수 — historical reference

아래 결과는 이전 폴더의 단일 분할 실험 기록이며 새 표준 실행 결과가 아니다.

- 근거: `../klosa_diabetes_mental_rhythm_features/metrics.json`
- Validation: Recall 0.8000, Specificity 0.4941, threshold 0.02241084
- Test: Recall 0.8000, Specificity 0.4742, AUROC 0.6596, AUPRC 0.0511, F1 0.0708, Brier 0.02389
- Test 혼동행렬: TP 156, FN 39, TN 3,655, FP 4,053

### 공통 분할 재실행 점수

`./scripts/ml-experiment.sh run rf_25features_v001`로 생성되는 `outputs/ml/rf_25features_v001/<run_id>/run.json`만 이 항목의 공식 재실행 기록이다.

- 실행 ID: `20260825T045054926974Z`
- 상태: `constraint_passed` (최소 Specificity 0.30 충족)
- 분할: Train 36,304건/6,111 PID, Validation 7,605건/1,309 PID, Test 7,903건/1,310 PID, PID 중복 0
- Test: Recall 0.8000, Specificity 0.4742, AUROC 0.6596, AUPRC 0.0511, F1 0.0708, Brier 0.02389
- Threshold: 0.02241084 (Validation에서만 선택)
- Test 혼동행렬: TP 156, FN 39, TN 3,655, FP 4,053

재실행 점수는 기존 점수와 수치상 일치한다. 다만 기존 점수는 과거 산출물의 참고값이고, 재실행 점수는 표준 Manifest와 실행 계약으로 새로 생성된 결과로 출처를 구분한다.

## 재현

```bash
./scripts/ml-experiment.sh validate
./scripts/ml-experiment.sh run rf_25features_v001
./scripts/ml-experiment.sh leaderboard
```

최초 실행 시 `official_v1` 코호트가 없으면 Git 제외 원자료에서 정답 노출 없는 t0 입력 코호트를 생성해 `data/processed/official_v1/`에 저장한다. 모델 파일과 실행 기록은 Git 제외 경로인 `outputs/ml/`에만 생성한다.

## 한계와 다음 실험

- 표적은 생물학적 발병 시점이 아니라 다음 조사에서 새로 보고된 당뇨·고혈당 진단이다.
- 기존 실험에서 Test가 반복 조회되어 완전히 미사용된 최종 holdout으로 볼 수 없다.
- 낮은 유병률 때문에 Recall을 높일수록 False Positive가 많아질 수 있다.
- 자기보고 변수, KLoSA 조사대상과 시점의 대표성 한계가 있다.
- 후보 등록과 웹서비스 활성화 전 시간 기반 외부 검증, 보정, 의료 안전 검토가 필요하다.
