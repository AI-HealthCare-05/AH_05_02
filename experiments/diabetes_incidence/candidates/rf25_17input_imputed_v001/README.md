# rf25_17input_imputed_v001

기존 `rf25-tuned-spec40-v1`을 재학습하지 않고 17개 입력만 제공하는 민감도
분석이다. 다음 8개는 추론 직전에 명시적으로 NaN으로 설정한다.

`current_drinker`, `liver_disease_diagnosis`, `psychiatric_disease_diagnosis`,
`cancer_diagnosis`, `household_structure`, `cerebrovascular_disease_diagnosis`,
`heart_disease_diagnosis`, `chronic_lung_disease_diagnosis`.

기존 fitted 전처리기의 Train 최빈값 대치를 사용한다. 결측을 `no`로 해석하지
않는다. 임계값은 이 입력 조건의 Validation에서 Specificity 0.43 이상인 값 중
Recall이 최대가 되도록 결정하고 Test에 그대로 적용한다.

기록된 실행은 Validation Recall/Specificity 0.8154/0.4351, Test
0.8359/0.4002, Test AUROC/AUPRC 0.6597/0.0496이다. 반복 조회된 historical
Test 결과이므로 독립 검증이나 운영 승인을 뜻하지 않는다.

```bash
./scripts/ml-experiment.sh run rf25_17input_imputed_v001
```

원자료, 공통 전처리본, 모델 바이너리와 실행 결과는 Git에 커밋하지 않는다.
결과는 진단·처방이 아닌 위험 선별·건강교육 연구에만 사용한다.
