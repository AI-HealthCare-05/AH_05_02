# rf25_discrete_logistic_stacking_v001

- 담당자: 양준혁
- 상태: 연구용, 운영 미승인

## 실험 가설

고정 가중 평균 대신 Train OOF 점수로 Logistic 메타모델을 학습하면 RF25와 이산시간
Logistic의 상호 보완성을 데이터 기반으로 결합해 2년 위험 선별 성능을 개선할 수 있다.

## 사용 데이터와 입력 변수

- 데이터 버전: `official_v1_klosa_structured_20260413_survival_v1`
- 분할 버전: `pid_group_70_15_15_master_rf25_rs42_v1`
- 입력 특성 스키마: `klosa_rf25_earliest_origin_2y_logistic_stack_v1`
- PID별 최초 적격 기준시점 한 건과 확인된 2년 결과
- 기준 모델 입력 RF25와 이산시간 첫 구간 번호

## 제외 변수와 제외 이유

- 미래 시점 변수: 데이터 누수 방지
- 당뇨 진단·치료 변수: 정답 직접 노출 방지
- 미래 조사 응답과 진단·치료 정보: 데이터 누수 방지
- 2년 결과 미확인 사례: 음성으로 처리하지 않고 제외

## 모델과 하이퍼파라미터

- 1단계 RF: 튜닝 RF25 하이퍼파라미터
- 1단계 생존모델: 무가중 pooled Logistic
- Train PID 5-fold OOF로 1단계 예측 생성
- 각 OOF 점수에 Platt sigmoid 보정
- 2단계 모델: 보정 점수의 logit 2개를 입력한 Logistic Regression, `C=1.0`

## 임계값 결정 방법

Validation에서 Specificity 0.43 이상인 임계값 중 Recall이 가장 높은 값을 선택한다.
Test는 메타모델과 임계값 확정 후 결과 보고에만 사용한다.

## 평가 결과

Recall, Specificity, AUROC, AUPRC, F1, Brier Score, 혼동행렬, False Positive, False Negative를 기록한다.

`./scripts/ml-experiment.sh run rf25_discrete_logistic_stacking_v001`

- 실행 ID: `20260903T050726329240Z`
- 메타계수: RF logit 0.6647, Logistic logit 0.4741, 절편 0.5463
- Validation: Recall 0.8214, Specificity 0.4988, AUROC 0.6958, AUPRC 0.1002
- Test: Recall 0.7778, Specificity 0.4793, AUROC 0.6432, AUPRC 0.0420
- Test 혼동행렬: TP 21, FN 6, TN 615, FP 668
- Test Brier Score: 0.02011
- Test 평균 예측위험 0.01939, 관찰 사건률 0.02061

고정 가중 평균(RF 0.65, Logistic 0.35)과 Test Recall은 같고, stacking이 정상
참여자 4명을 추가로 음성 분류해 Specificity를 0.4762에서 0.4793으로 소폭 높였다.
그러나 보정 RF 단독의 Test Recall 0.8519보다 낮아 Recall 최우선 후보를 대체하지는
못했다.

## 한계와 다음 실험

이 결과는 진단이나 처방이 아닌 위험 선별·건강교육 목적의 연구 결과다.

- 두 기준 모델이 동일 RF25 특성을 사용하므로 예측 간 상관성이 높다.
- 사건 수가 적어 메타계수와 Test Recall 변동성이 클 수 있다.
- 기존 Test가 과거 실험에서 반복 조회된 historical holdout이다.
- 내부 확률 보정이며 외부 검증과 운영 승인을 의미하지 않는다.
