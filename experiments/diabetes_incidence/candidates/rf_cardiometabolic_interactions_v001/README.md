# rf_cardiometabolic_interactions_v001

- 담당자: 양준혁
- 상태: 연구용, 운영 미승인

## 실험 가설

개별 심혈관 진단과 BMI·연령의 결합을 명시하면 현재 RF가 포착하지 못한 건강부담
상호작용을 보완해 Recall 0.80 조건의 Specificity를 개선할 수 있다.

## 사용 데이터와 입력 변수

- 데이터 버전: `official_v1`
- 분할 버전: `pid_group_70_15_15_stratified_any_event_rs42_v1`
- 입력 특성 스키마: `klosa_stage3_cardiometabolic_interaction_variants_v1`
- 공통 입력: 현재 RF와 동일한 t0 25개 변수

## 제외 변수와 제외 이유

- 미래 시점 변수: 데이터 누수 방지
- 당뇨 진단·치료 변수: 정답 직접 노출 방지
- PID·가구 ID·target: 모델 입력 제외
- 혈당·HbA1c·현재 당뇨 진단·치료: 정답 직접 노출 위험으로 제외
- 고혈압·심장·뇌혈관 상태 중 하나라도 불명이면 질환 개수와 관련 상호작용은 결측 유지

## 모델과 하이퍼파라미터

공통 모델은 현재 비가중 RF(500 trees, depth 8, minimum leaf 20, `sqrt`)다.

파생 피처:

- `cardiovascular_diagnosis_count`: 고혈압·심장·뇌혈관 질환의 명시적 yes 개수
- `cardiovascular_comorbidity_any`: 세 질환 중 하나 이상 yes
- `bmi_x_hypertension`, `age_x_hypertension`
- `bmi_x_cardiovascular_count`, `age_x_cardiovascular_count`

비교 변형은 현재 25개, 심혈관 요약 추가 27개, 고혈압 상호작용 추가 27개,
심혈관 부담 상호작용 추가 28개, 전체 추가 31개, 개별 심혈관 진단 3개를 전체
파생군으로 대체한 28개다.

## 임계값 결정 방법

Train PID 5-fold OOF에서 Recall 0.80 이상 → Specificity → AUPRC → AUROC →
최저 fold Recall → 적은 변수 순으로 변형을 선택한다. 선택 변형만 전체 Train에
재학습하고 숫자 임계값은 Validation Recall 0.80 기준으로 결정한다. Test는 마지막
보고에만 사용한다.

## 평가 결과

실행 ID: `20260826T075843996737Z`

Train PID 5-fold OOF 결과(모두 Recall 0.8000 기준):

| 변형 | 변수 수 | Specificity | AUPRC | AUROC | 최저 fold Recall |
|---|---:|---:|---:|---:|---:|
| 현재 RF | 25 | **0.3614** | 0.0405 | 0.6307 | 0.7527 |
| 심혈관 요약 추가 | 27 | 0.3482 | 0.0403 | 0.6263 | 0.7253 |
| 고혈압 상호작용 추가 | 27 | 0.3493 | 0.0418 | 0.6310 | 0.7527 |
| 심혈관 부담 상호작용 추가 | 28 | 0.3499 | 0.0408 | 0.6271 | 0.7418 |
| 전체 파생군 추가 | 31 | 0.3516 | **0.0418** | 0.6277 | 0.7473 |
| 개별 진단을 파생군으로 대체 | 28 | 0.3544 | 0.0418 | 0.6285 | 0.7473 |

선택 결과는 현재 25개 변수다. 선택 모델의 Validation 임계값은 `0.02241084`이며,
Validation은 Recall 0.8000, Specificity 0.4941이었다. 마지막 Test 평가는 Recall
0.8000, Specificity 0.4742, AUROC 0.6596, AUPRC 0.0511이었다(TP 156, FN 39,
TN 3655, FP 4053). 기존 RF를 재현한 결과이며 상호작용 피처는 채택하지 않는다.

## 한계와 다음 실험

이 결과는 진단이나 처방이 아닌 위험 선별·건강교육 목적의 연구 결과다.

- 질환 진단은 자기보고이며 실제 임상 중증도나 치료 상태를 나타내지 않는다.
- RF는 원변수 상호작용을 이미 학습할 수 있어 파생 곱이 중복될 수 있다.
- 단순 곱과 질환 개수는 발병 시점·중증도·약물 통제를 반영하지 못하며, 이번 OOF에서
  Recall 고정 Specificity를 개선하지 못했다.
- 기존 Test가 반복 조회됐으므로 외부·시간 기반 검증 전 운영 모델로 사용하지 않는다.
