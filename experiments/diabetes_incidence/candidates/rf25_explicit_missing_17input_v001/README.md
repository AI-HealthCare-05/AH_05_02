# RF25 명시적 범주형 결측 + 17개 입력

25개 변수로 학습하면서 범주형 결측을 최빈값이 아닌 `__MISSING__` 범주로 보존한다.
추론 시 입력 간소화 대상 8개를 결측으로 전달하고 Validation Specificity 0.43 이상에서
Recall이 최대인 임계값을 선택한다. 수치형은 Train 중앙값과 결측 indicator를 사용한다.

제외 입력은 음주, 간질환, 정신과 질환, 암, 가구 형태, 뇌혈관질환, 심장질환,
만성 폐질환이다. 미래·당뇨 진단 및 치료 정보는 사용하지 않는다.

```bash
./scripts/ml-experiment.sh run rf25_explicit_missing_17input_v001
```

실행 결과는 `outputs/ml/rf25_explicit_missing_17input_v001/<run-id>/comparison.json`에 기록한다.
기존 Test는 반복 조회됐으므로 독립 검증이 아니며, 위험 선별·건강교육 연구용이다.

실행 `20260910T013419375601Z`에서 8개 결측 입력의 선택 임계값은 0.0265014888였다.
Validation Recall/Specificity는 0.830769/0.442645, Test는 0.805128/0.409445였다.
Test AUROC/AUPRC는 0.655822/0.047501이며 TP/FP/TN/FN은 157/4552/3156/38이다.
전체 25개 입력 시 Test Recall/Specificity는 0.825641/0.415802였다.
