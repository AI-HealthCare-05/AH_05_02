# rf24_no_alcohol_leave_one_out_v001

- 담당자: 양준혁
- 상태: 연구용, 운영 미승인

## 실험 가설

음주 여부 current_drinker를 고정 제외하고, 나머지 24개 중 하나를 추가로
제외한 RF23 모델 24개와 기준 RF24를 비교한다.

## 사용 데이터와 입력 변수

- 데이터 버전: `official_v1`
- 분할 버전: pid_group_70_15_15_stratified_any_event_rs42_v1
- 입력 특성 스키마: klosa_rf24_no_alcohol_leave_one_out_v1

## 제외 변수와 제외 이유

- 미래 시점 변수: 데이터 누수 방지
- 당뇨 진단·치료 변수: 정답 직접 노출 방지
- 추가 제외 변수: current_drinker + 각 행에서 지정하는 변수 하나.
  해당 원핫 열과 결측지표도 제거한다. 누락 후 대치 실험이 아니다.

## 모델과 하이퍼파라미터

튜닝 RF 설정 고정: 500 trees, depth 8, leaf 39, max_samples 0.7,
log_loss, ccp_alpha 0.00001, bootstrap, 무가중, seed 42.
전처리 중앙값·최빈값·원핫은 Train에서만 적합한다.

## 임계값 결정 방법

RF24 기준 임계값 0.021232464150750596를 모든 모델에 적용한 고정 비교와
각 모델 Validation Spec>=0.43에서 Recall을 최대화한 개별 조정 비교를 기록한다.
이전 RF25의 고정 임계값과 다르다.
Validation Recall, Specificity, AUPRC 순으로 후보를 선택하고 Test 예측 전에 저장한다.

## 평가 결과

Recall, Specificity, AUROC, AUPRC, F1, Brier Score, 혼동행렬, False Positive, False Negative를 기록한다.

실행: `./scripts/ml-experiment.sh run rf24_no_alcohol_leave_one_out_v001`
Git 제외 outputs/ml/rf24_no_alcohol_leave_one_out_v001 실행 폴더에
results.json, comparison.csv, selection.json, variant 모델과 run.json을 저장한다.
Precision, AUROC, AUPRC, F1, Brier, 혼동행렬과 기준 RF24 대비 변화량을 포함한다.
기준 RF24의 이전 조정 Test 지표를 재현하는지 수치 검사한다.

## 한계와 다음 실험

이 결과는 진단이나 처방이 아닌 위험 선별·건강교육 목적의 연구 결과다.

단일 분할과 24회 다중 비교이며, 이전 historical Test를 보고 음주 제거가 제안된
단계적 탐색이다. 이번 Test는 조건 확정 뒤 기술 보고에만 사용한다.
유의성·외부 일반화·인과 효과를 주장하지 않는다. PID OOF 후속 확인이 필요하다.
원자료·모델 바이너리는 Git 제외. 운영 모델이나 입력 계약을 변경하지 않는다.
