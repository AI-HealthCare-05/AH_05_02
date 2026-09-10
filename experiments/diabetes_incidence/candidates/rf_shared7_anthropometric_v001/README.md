# rf_shared7_anthropometric_v001

- 담당자: 양준혁
- 상태: 연구용, 운영 미승인

## 실험 가설

키와 체중이 BMI에 압축되지 않은 체격 정보를 추가로 제공하여, 공통 5특성 모델보다 Recall 또는 Specificity가 개선되는지 확인한다.

## 사용 데이터와 입력 변수

- 데이터 버전: `official_v1`
- 분할 버전: `pid_group_70_15_15_stratified_any_event_rs42_v1`
- 입력 특성 스키마: `klosa_shared7_anthropometric_v1`
- 입력: `age`, `height_cm`, `weight_kg`, `bmi`, `sex`, `smoking_status`, `education_level`
- 연속형 허용 범위 밖 값은 결측으로 바꾸고 Train 중앙값으로 대치한다.
- 범주형 결측은 Train 최빈값으로 대치하고 One-hot encoding한다.

## 제외 변수와 제외 이유

- 미래 시점 변수: 데이터 누수 방지
- 당뇨 진단·치료 변수: 정답 직접 노출 방지
- RF25의 나머지 20개 변수: 7개 공통 입력만 사용하는 축소 모델을 비교하기 위해 제외

## 모델과 하이퍼파라미터

RF25 최종 후보와 같은 Random Forest 설정을 사용한다: 500 trees, max depth 8, minimum leaf 39, max samples 0.7, log-loss criterion, ccp alpha 0.00001, random state 42.

## 임계값 결정 방법

Validation 데이터에서 Specificity 0.43 이상을 만족하면서 Recall이 최대인 임계값을 결정한다. Test는 임계값 확정 후 한 번 평가한다.

## 평가 결과

Recall, Specificity, AUROC, AUPRC, F1, Brier Score, 혼동행렬, False Positive, False Negative를 기록한다.

실행 `20260909T063529347917Z` 결과:

- Validation: Recall 0.7795, Specificity 0.4381, AUROC 0.6570, AUPRC 0.0458
- Test: Recall 0.7385, Specificity 0.4104, AUROC 0.6243, AUPRC 0.0398
- Test confusion matrix: TP 144, FP 4545, TN 3163, FN 51
- 선택 임계값: 0.0221446583

## 한계와 다음 실험

이 결과는 진단이나 처방이 아닌 위험 선별·건강교육 목적의 연구 결과다.

키·체중·BMI는 수학적으로 중복되므로 독립적인 정보가 3개인 것은 아니다. 같은 분할의 5특성 모델보다 Test Recall이 낮아 성능 개선 후보로 채택하지 않는다. 외부 검증과 Calibration 검토 전에는 운영 모델로 사용하지 않는다.
