# RF17 재학습

입력 부담을 줄이기 위해 RF25에서 음주, 간질환, 정신과 질환, 암, 가구 형태,
뇌혈관질환, 심장질환, 만성 폐질환을 제외하고 전처리기와 RF를 Train에서 새로 학습했다.
미래 정보 및 당뇨 정답·치료 변수는 입력하지 않는다.

## 데이터와 모델

- 데이터: official_v1 KLoSA stage3 코호트, 기존 PID 70/15/15 분할, seed 42.
- Train 36,304행/6,111 PID, Validation 7,605행/1,309 PID, Test 7,903행/1,310 PID.
- 입력 순서는 comparison.json의 features 17개에 고정한다.
- 수치형 Train 중앙값 대치 및 학습 당시 결측 열 indicator, 범주형 Train 최빈값 및 one-hot.
- RF25와 동일: 500 trees, depth 8, leaf 39, max_samples 0.7, bootstrap,
  criterion log_loss, ccp_alpha 0.00001, max_features sqrt, class_weight 없음.
- Validation Spec >=0.43에서 Recall 최대화, 동률이면 Specificity 최대화.

## 결과

실행: outputs/ml/rf_17features_v001/20260910T004604353702Z

| 분할 | 임계값 | Recall | Specificity | AUROC | AUPRC | TP/FP/TN/FN |
|---|---:|---:|---:|---:|---:|---|
| Validation | 0.0216135233 | 0.815385 | 0.461404 | 0.675839 | 0.051224 | 159/3991/3419/36 |
| Test | 0.0216135233 | 0.810256 | 0.425921 | 0.658332 | 0.045750 | 158/4425/3283/37 |
| Test 기존 RF25 임계값 | 0.0211536028 | 0.820513 | 0.403477 | 0.658332 | 0.045750 | 160/4598/3110/35 |

Artifact 저장 후 재로딩한 고정 3행 예측의 완전 일치를 확인했다.

## 재현과 한계

```bash
./scripts/ml-experiment.sh run rf_17features_v001
```

원본 RF25 Artifact는 하이퍼파라미터와 입력 순서 복제에 필요하다. 원자료와 바이너리는 Git 제외.
기존 Test는 반복 조회됐으며 이번 변수 선정도 과거 결과를 참고했다.
독립 검증이나 성능 동등성 검정이 아니다. PID OOF 축소모델 비교는 이번 실행에 포함되지 않았다.
위험 선별·건강교육 연구용이며 운영 모델은 변경하지 않았다.
