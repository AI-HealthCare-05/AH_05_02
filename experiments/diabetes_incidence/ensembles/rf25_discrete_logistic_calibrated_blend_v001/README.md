# rf25_discrete_logistic_calibrated_blend_v001

- 담당자: 양준혁
- 상태: 연구용, 운영 미승인

## 실험 가설

같은 최초 기준시점에서 튜닝 RF25의 비선형 판별력과 이산시간 pooled Logistic의
확률 안정성을 Platt 보정 후 결합하면, 단독 모델보다 Validation 특이도 0.43 이상에서
2년 Recall을 높일 수 있는지 확인한다.

## 사용 데이터와 입력 변수

- 데이터 버전: `official_v1_klosa_structured_20260413_survival_v1`
- 분할 버전: `pid_group_70_15_15_master_rf25_rs42_v1`
- 입력 특성 스키마: `klosa_rf25_earliest_origin_2y_calibrated_blend_v1`
- PID별 최초 적격 비당뇨 기준시점 1건
- 기준시점 이후 2년 상태가 확인되거나 그 전에 최초 진단된 사례
- RF25 입력 25개와 이산시간 첫 구간 번호

## 제외 변수와 제외 이유

- 미래 시점 변수: 데이터 누수 방지
- 당뇨 진단·치료 변수: 정답 직접 노출 방지
- 기준시점 이후 건강정보와 조사 응답: 미래 정보이므로 제외
- 2년 상태 미확인 사례: 음성으로 간주하지 않고 평가 코호트에서 제외

## 모델과 하이퍼파라미터

- RF: 튜닝 RF25 구성, 500 trees, depth 8, min leaf 39, max samples 0.7,
  `log_loss`, bootstrap, `ccp_alpha=0.00001`
- Logistic: 무가중 pooled discrete-time Logistic, RF25 + interval index
- 보정: Train PID 5-fold OOF 원점수에 각각 Platt sigmoid 적용
- 결합: `alpha * calibrated_RF + (1-alpha) * calibrated_Logistic`
- RF 가중치: 0.05~0.95, 0.05 간격

## 임계값 결정 방법

Validation에서 각 가중치별로 Specificity 0.43 이상에서 Recall이 가장 높은 임계값을
결정한다. Recall, Specificity, AUPRC, Brier Score 순으로 가중치를 선택한다. Test는
가중치와 임계값을 확정한 후 보고에만 사용한다.

## 평가 결과

Recall, Specificity, AUROC, AUPRC, F1, Brier Score, 혼동행렬, False Positive, False Negative를 기록한다.

`./scripts/ml-experiment.sh run rf25_discrete_logistic_calibrated_blend_v001`
실행 결과의 `calibrated_blend_results.json`에 단독 모델, 전체 가중치 후보와 선택된
앙상블 결과를 기록한다.

- 실행 ID: `20260903T024757480846Z`
- 선택 가중치: 보정 RF 0.65, 보정 Logistic 0.35
- Validation: Recall 0.8214, Specificity 0.4957, AUROC 0.6947, AUPRC 0.1044
- Test: Recall 0.7778, Specificity 0.4762, AUROC 0.6440, AUPRC 0.0411
- Test 혼동행렬: TP 21, FN 6, TN 611, FP 672
- Test Brier Score: 0.02010
- Test 평균 예측위험 0.01940, 관찰 사건률 0.02061

같은 코호트의 보정 RF 단독 Test는 Recall 0.8519, Specificity 0.4186이고 보정
Logistic 단독은 Recall 0.7407, Specificity 0.4513이다. 앙상블은 Validation에서 RF와
같은 Recall을 유지하면서 Specificity를 0.4457에서 0.4957로 높였지만, Test에서는 RF
단독보다 사건 2명을 덜 발견하고 Specificity를 0.0577 높였다.

## 한계와 다음 실험

이 결과는 진단이나 처방이 아닌 위험 선별·건강교육 목적의 연구 결과다.

- 동일 RF25 특성을 공유하므로 모델 오류가 강하게 상관되어 앙상블 이득이 작을 수 있다.
- 기존 Test가 과거 실험에서 반복 조회되어 완전히 미사용된 최종 holdout이 아니다.
- 2년 사건 수가 적어 PID bootstrap 신뢰구간과 외부 검증이 추가로 필요하다.
- 보정은 내부 KLoSA 표본에 한정되며 운영 승인이나 임상 확률 검증을 의미하지 않는다.
