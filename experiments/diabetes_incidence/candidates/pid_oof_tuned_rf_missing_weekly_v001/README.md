# pid_oof_tuned_rf_missing_weekly_v001

- 담당자: 양준혁
- 상태: 연구용, 운영 미승인

## 실험 가설

PID OOF에서 선택된 RF25 하이퍼파라미터를 고정한 상태에서 범주형 결측을
별도 범주로 보존하고 주간 운동량을 추가하면, 특이도 0.40 이상에서 Recall이
개선될 수 있다.

## 사용 데이터와 입력 변수

- 데이터 버전: `official_v1`
- 분할 버전: `pid_group_70_15_15_stratified_any_event_rs42_v1`
- 입력 특성 스키마: `klosa_stage3_tuned_rf_missing_weekly_v1`
- 비교 입력: 기존 RF25, 명시적 missing RF25, 명시적 missing + 주간 운동량 RF26

## 제외 변수와 제외 이유

- 미래 시점 변수: 데이터 누수 방지
- 당뇨 진단·치료 변수: 정답 직접 노출 방지
- 추가 제외 변수: 없음

## 모델과 하이퍼파라미터

세 변형 모두 기존 PID OOF 튜닝에서 선택된 다음 값을 고정한다.

- `min_samples_leaf=39`
- `max_samples=0.7`
- `criterion=log_loss`
- `ccp_alpha=0.00001`
- `bootstrap=True`

## 임계값 결정 방법

변형은 Train PID 5-fold OOF에서 Specificity 0.40 이상인 Recall로 선택한다.
최종 수치 임계값은 Validation Specificity 0.43 이상에서 Recall을 최대화한다.

## 평가 결과

Recall, Specificity, AUROC, AUPRC, F1, Brier Score, 혼동행렬, False Positive, False Negative를 기록한다.

`./scripts/ml-experiment.sh run pid_oof_tuned_rf_missing_weekly_v001`로 재현하고
상세 결과는 실행 폴더의 `tuned_missing_weekly_results.json`에서 확인한다.

| 변형 | OOF Recall/Specificity | Validation Recall/Specificity | Test Recall/Specificity |
|---|---:|---:|---:|
| 튜닝 RF25 최빈값 결측 | 0.7692 / 0.4013 | 0.8256 / 0.4337 | 0.8410 / 0.4024 |
| 튜닝 RF25 명시적 missing | 0.7626 / 0.4010 | 0.8154 / 0.4471 | 0.8256 / 0.4158 |
| 튜닝 RF26 명시적 missing + 주간 운동량 | 0.7703 / 0.4004 | 0.8205 / 0.4321 | 0.8359 / 0.4028 |

Train PID OOF 선택 결과는 튜닝 RF26 명시적 missing + 주간 운동량이다. 다만
Test Recall은 기존 튜닝 RF25보다 0.0051 낮으므로 일관된 개선으로 확정하지 않는다.

## 한계와 다음 실험

이 결과는 진단이나 처방이 아닌 위험 선별·건강교육 목적의 연구 결과다.

동일 Test 분할이 선행 실험에서 반복 조회됐으므로 최종 운영 모델 선택 전 새로운
Holdout 또는 중첩 PID 교차검증이 필요하다.
