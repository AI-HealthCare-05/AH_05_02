# rf_targeted_feature_removal_v001

- 담당자: 양준혁
- 상태: 연구용, 운영 미승인

## 실험 가설

`psychiatric_disease_diagnosis`, `cerebrovascular_disease_diagnosis`,
`exercise_minutes`는 기존 PID OOF permutation importance에서 낮거나 불안정했다.
개별 또는 조합 제거가 Recall 0.80을 유지하면서 Specificity를 안정적으로 높이는지 재탐색한다.

## 사용 데이터와 입력 변수

- 데이터 버전: `official_v1`
- 데이터 파일: `klosa_diabetes_incidence_stage3_25features_v1.pkl` (Git 제외)
- 분할 버전: `pid_group_70_15_15_stratified_any_event_rs42_v1`
- 입력 특성 스키마: `klosa_stage3_25features_targeted_removal_v1`
- 기본안: 학습 당시 순서를 유지한 기존 25개 변수
- 비교안: 세 후보 변수의 개별 3개, 2개 조합 3개, 전체 조합 1개 제거

## 제외 변수와 제외 이유

- 미래 시점 변수: 데이터 누수 방지
- 당뇨 진단·치료 변수: 정답 직접 노출 방지
- 제거 후보: 정신질환 진단, 뇌혈관질환 진단, 운동시간
- 제거 여부는 Test가 아닌 Train PID OOF에서만 결정한다.

## 모델과 하이퍼파라미터

- `RandomForestClassifier`
- `n_estimators=500`, `max_depth=8`, `min_samples_leaf=20`
- `max_features="sqrt"`, `class_weight=None`, `random_state` 고정
- 수치형: Train 중앙값 대치와 결측 지시자
- 범주형: Train 최빈값 대치 후 One-hot encoding

## 임계값 결정 방법

Train PID 5-fold OOF를 시드 42와 1042로 반복한다. 각 시드에서 Recall 0.80 이상인
임계값 중 Specificity가 가장 높은 값을 사용해 제거안을 비교한다. 제거안은 두 시드
모두에서 기존 25변수보다 Specificity가 높을 때만 선택 대상이 된다. 선택된 변수 집합을
전체 Train에 다시 학습하고, 최종 수치 임계값은 Validation에서 Recall 0.80 기준으로만
정한다. Test는 선택된 한 모델의 최종 보고에만 사용한다.

## 평가 결과

Recall, Specificity, AUROC, AUPRC, F1, Brier Score, 혼동행렬, False Positive, False Negative를 기록한다.

재현 실행: `20260828T090442445307Z`

| 순위 | 제거 변수 | 평균 Recall | 평균 Specificity | 평균 AUPRC | 평균 AUROC | 시드별 Specificity 증감 |
|---:|---|---:|---:|---:|---:|---:|
| 1 | 없음 (25개 유지) | 0.8000 | **0.3623** | 0.04045 | 0.63088 | 기준 |
| 2 | 정신질환 | 0.8000 | 0.3613 | **0.04086** | 0.63033 | -0.00062, -0.00130 |
| 3 | 정신질환+뇌혈관질환+운동시간 | 0.8000 | 0.3566 | 0.04052 | 0.62949 | -0.00059, -0.01079 |
| 4 | 정신질환+운동시간 | 0.8005 | 0.3563 | 0.04045 | 0.62988 | -0.00585, -0.00607 |
| 5 | 뇌혈관질환+운동시간 | 0.8000 | 0.3563 | 0.04031 | 0.62871 | -0.00274, -0.00927 |
| 6 | 운동시간 | 0.8000 | 0.3552 | 0.04040 | 0.63026 | +0.00113, -0.01526 |
| 7 | 정신질환+뇌혈관질환 | 0.8000 | 0.3551 | 0.04073 | 0.62992 | -0.01023, -0.00421 |
| 8 | 뇌혈관질환 | 0.8000 | 0.3526 | 0.04087 | 0.62898 | -0.01141, -0.00794 |

결론: 두 시드에서 모두 Specificity가 개선된 제거안은 없었다. 기존 25개 변수를
유지한다. 정신질환 단독 제거는 AUPRC가 소폭 높았지만 Specificity가 두 시드 모두
낮아졌고, 운동시간 단독 제거는 시드 42에서만 `+0.00113` 개선되어 불안정했다.

선택된 25변수 모델의 Validation 임계값은 `0.0224108358`이다. Validation은
Recall 0.8000, Specificity 0.4941, AUROC 0.6775, AUPRC 0.05718이었다. 이 임계값을
고정한 Test 결과는 Recall 0.8000, Specificity 0.4742, AUROC 0.6596,
AUPRC 0.05114, F1 0.07084, Brier Score 0.02389였으며 혼동행렬은
TP 156, FN 39, TN 3,655, FP 4,053이었다.

재현 명령:

```bash
./scripts/ml-experiment.sh run rf_targeted_feature_removal_v001
```

## 한계와 다음 실험

이 결과는 진단이나 처방이 아닌 위험 선별·건강교육 목적의 연구 결과다.

- Test는 과거 실험에서 이미 확인한 동일 고정 분할이므로 완전히 미개봉인 외부 검증셋이 아니다.
- 두 OOF 시드에서 Specificity가 모두 개선돼도 차이가 작을 수 있다. 실질 채택 기준은 각
  시드 Specificity `+0.01` 이상, 평균 AUPRC와 최악 fold Recall 비열화다.
- 원본 의료 데이터와 생성 모델 바이너리는 Git에 포함하지 않는다.
