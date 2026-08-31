# rf_25features_tuned_spec40_v001

- 담당자: 양준혁
- 상태: 연구용, 운영 미승인

## 실험 가설

PID OOF 튜닝으로 선택한 RF25 하이퍼파라미터를 고정하고, 서버 연동에 사용할
단일 Artifact와 Validation 전용 위험 임계값을 재현한다.

## 사용 데이터와 입력 변수

- 데이터 버전: `official_v1`
- 분할 버전: `pid_group_70_15_15_stratified_any_event_rs42_v1`
- 입력 특성 스키마: `klosa_stage3_25features_v1`
- 입력 변수: 고정된 KLoSA 25변수

## 제외 변수와 제외 이유

- 미래 시점 변수: 데이터 누수 방지
- 당뇨 진단·치료 변수: 정답 직접 노출 방지
- 추가 제외 변수: 없음

## 모델과 하이퍼파라미터

- Random Forest 500 trees, max depth 8, max features sqrt
- `min_samples_leaf=39`, `max_samples=0.7`, `criterion=log_loss`
- `ccp_alpha=0.00001`, `bootstrap=True`, random state 42

## 임계값 결정 방법

- `high`: Validation Specificity 0.43 이상에서 Recall 최대화
- `caution`: Validation Recall 0.90 이상에서 Specificity 최대화
- Test는 두 임계값을 고정한 다음 마지막 보고에만 사용

## 평가 결과

Recall, Specificity, AUROC, AUPRC, F1, Brier Score, 혼동행렬, False Positive, False Negative를 기록한다.

`./scripts/ml-experiment.sh run rf_25features_tuned_spec40_v001` 실행 결과를
`outputs/ml/rf_25features_tuned_spec40_v001/<UTC 실행시각>/`에 저장한다.

## 한계와 다음 실험

이 결과는 진단이나 처방이 아닌 위험 선별·건강교육 목적의 연구 결과다.

동일 Test 분할이 선행 연구에서 반복 조회됐으므로 외부 검증 전 운영 활성화하지
않는다. KLoSA 기반 45~105세 기저시점 미진단자 위험 선별·건강교육 연구에만 쓴다.
