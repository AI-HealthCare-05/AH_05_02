# rf25_first_interval_survival_ensemble_v001

- 담당자: 양준혁
- 상태: 연구용, 운영 미승인

## 실험 가설

RF25를 모든 장기 구간에 반복 적용하지 않고 첫 2년 위험에만 결합하면 RF의 단기
선별력을 활용하면서 이산시간 Logistic의 조건부 생존 구조와 단조 누적곡선을 유지할
수 있다.

## 사용 데이터와 입력 변수

- 데이터 버전: `official_v1_klosa_structured_20260413_survival_v1`
- 분할 버전: `pid_group_70_15_15_master_rf25_rs42_v1`
- 입력 특성 스키마: `klosa_rf25_first_interval_plus_survival_2to18_v1`
- RF25 기준시점 특성 25개와 이산시간 구간 번호
- PID별 최초 적격 비당뇨 기준시점 한 건

## 제외 변수와 제외 이유

- 미래 시점 변수: 데이터 누수 방지
- 당뇨 진단·치료 변수: 정답 직접 노출 방지
- 기준시점 이후 건강정보와 당뇨 진단·치료 정보
- 미응답 이후 구간: 음성으로 처리하지 않고 엄격 중도절단

## 모델과 하이퍼파라미터

- 첫 2년 후보 A: Platt 보정 RF25 0.65 + 보정 Logistic 0.35
- 첫 2년 후보 B: 보정된 두 점수의 logit을 입력한 Logistic stacking
- 2년 이후: pooled Logistic의 구간별 조건부 hazard
- 누적위험: `1 - (1 - p_ensemble_2y) * product(1 - h_k), k=2..K`
- 첫 구간 방식은 2년 Validation 성능으로만 선택한다.

## 임계값 결정 방법

각 기간별 Validation에서 Specificity 0.43 이상인 임계값 중 Recall이 가장 높은 값을
선택한다. Test는 첫 구간 방식과 모든 임계값을 확정한 뒤 보고에만 사용한다.

## 평가 결과

Recall, Specificity, AUROC, AUPRC, F1, Brier Score, 혼동행렬, False Positive, False Negative를 기록한다.

`./scripts/ml-experiment.sh run rf25_first_interval_survival_ensemble_v001`

- 실행 ID: `20260903T091006078025Z`
- 2년 Validation 선택: Logistic stacking
- 비교 가중 평균: 보정 RF 0.65, 보정 Logistic 0.35
- 개인별 2~18년 누적 위험 단조 증가 검사: Test PID 1,310명 전원 통과

| 기간 | 생존 Logistic Test R/S | 첫 구간 stacking Test R/S |
|---:|---:|---:|
| 2년 | 0.7407 / 0.4513 | 0.7778 / 0.4793 |
| 4년 | 0.6939 / 0.4323 | 0.8163 / 0.4421 |
| 6년 | 0.7059 / 0.4350 | 0.8235 / 0.4203 |
| 8년 | 0.7381 / 0.4096 | 0.7500 / 0.4096 |
| 10년 | 0.7477 / 0.4047 | 0.7297 / 0.4047 |
| 12년 | 0.7200 / 0.4089 | 0.7440 / 0.4261 |
| 14년 | 0.7517 / 0.3916 | 0.7586 / 0.3851 |
| 16년 | 0.7619 / 0.4111 | 0.7738 / 0.3815 |
| 18년 | 0.8115 / 0.3936 | 0.7958 / 0.3787 |

2·4·6년은 Test Specificity 0.40 이상에서 모두 기준 생존모델보다 Recall이 높았다.
그러나 14·16·18년은 최소 Specificity 0.40을 충족하지 못해 2~18년 전체 후보로는
`constraint_failed`다. 장기 구간까지 운영 후보로 사용하지 않는다.

## 한계와 다음 실험

이 결과는 진단이나 처방이 아닌 위험 선별·건강교육 목적의 연구 결과다.

- 2년 이후 Logistic hazard는 별도 시점별 확률 보정을 거치지 않았다.
- IPCW Integrated Brier Score와 calibration 신뢰구간이 아직 없다.
- 기간별 평가는 해당 시점까지 결과가 확인된 complete-case 성격을 가진다.
- 기존 Test가 반복 조회된 historical holdout이므로 새 외부 검증이 필요하다.
