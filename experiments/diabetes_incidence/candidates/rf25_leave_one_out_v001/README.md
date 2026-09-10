# rf25_leave_one_out_v001

- 담당자: 양준혁
- 상태: 연구용, 운영 미승인

## 실험 가설

기준 RF25와 변수 하나를 제거한 25개 모델을 비교한다.

## 사용 데이터와 입력 변수

- 데이터 버전: `official_v1`
- 분할 버전: pid_group_70_15_15_stratified_any_event_rs42_v1
- 입력 특성 스키마: klosa_rf25_leave_one_out_v1

## 제외 변수와 제외 이유

- 미래 시점 변수: 데이터 누수 방지
- 당뇨 진단·치료 변수: 정답 직접 노출 방지
- 추가 제외 변수: 각 실험마다 RF25 입력 중 하나. 해당 원핫·결측지표도 제거한다.

## 모델과 하이퍼파라미터

현재 튜닝 RF25 설정을 재사용한다: 500 trees, depth 8, leaf 39,
max_samples 0.7, log_loss, ccp_alpha 0.00001, bootstrap, 무가중, seed 42.
전처리 통계는 Train에서만 학습한다. 입력을 생략해 대치하는 실험이 아니라
전처리 열부터 제거하고 재학습한다.

## 임계값 결정 방법

고정 임계값 0.021153602801262862와 모델별 Validation Specificity>=0.43에서
Recall을 최대화하는 임계값을 함께 평가한다.
Validation Recall, Specificity, AUPRC 순으로 후보를 선택하고 Test 예측 전에 기록한다.

## 평가 결과

Recall, Specificity, AUROC, AUPRC, F1, Brier Score, 혼동행렬, False Positive, False Negative를 기록한다.

실행: `./scripts/ml-experiment.sh run rf25_leave_one_out_v001`
Git 제외 outputs/ml/rf25_leave_one_out_v001 실행 폴더의 comparison.csv에
Validation/Test 및 fixed/adjusted의 지표와 기준선 대비 변화량을 모두 기록한다.
results.json, selection.json, variant별 joblib과 run.json을 함께 보관한다.
현재 RF25 기록의 Recall, Specificity, AUROC, AUPRC, Brier 재현 여부를 검사한다.

## 한계와 다음 실험

이 결과는 진단이나 처방이 아닌 위험 선별·건강교육 목적의 연구 결과다.

25회 다중 비교와 historical Test 반복 조회에 의한 선택 낙관성에 주의한다.
Test는 고정된 전체 비교안의 기술적 보고에만 사용한다. 운영 모델은 변경하지 않는다.
개선 후보는 PID OOF로 추가 확인해야 한다. 원핫 차원과 sqrt 특성 샘플링도
달라지므로 단일 변수의 인과 효과로 해석하지 않는다.
