# 현재 모델 성능 기록

## 2026-08-31 서버 연동 후보

현재 서버 연동 기준 연구 후보는 `rf25-tuned-spec40-v1`이다. Test 7,903건에서
Recall 0.8410, Specificity 0.4024, AUROC 0.6636, AUPRC 0.0485를 기록했다.
High 임계값은 `0.021153602801262862`이며 Validation Specificity 0.43 이상에서
Recall을 최대화했다. Artifact·입출력·오류·적용 연령 계약은
[`RF25_TUNED_SPEC40_SERVER_HANDOFF.md`](RF25_TUNED_SPEC40_SERVER_HANDOFF.md)를
따른다. 이 후보는 연구용이며 운영 승인되지 않았다.

아래 내용은 선행 베이스라인과 누적 실험의 역사적 기록이다.

- 기준일: 2026-08-24
- 상태: 연구용 베이스라인, 운영 배포 및 진단·처방 사용 금지
- 대표 모델: 비가중 Logistic Regression
- 과제: 다음 인접 KLoSA 조사 시점의 신규 당뇨병 의사진단 위험 선별
- 관찰 간격: 중앙값 730일, 5~95백분위 671~786일

## 데이터와 평가 설계

| 항목 | 값 |
| --- | ---: |
| 전체 person-period | 51,812 |
| 고유 참여자 | 8,730 |
| 신규진단 사건 | 1,300 |
| 전체 사건률 | 2.51% |
| Train | 36,304건 / 6,111명 / 910건 사건 |
| Validation | 7,605건 / 1,309명 / 195건 사건 |
| Test | 7,903건 / 1,310명 / 195건 사건 |

- 동일 참여자가 여러 차수에 등장하므로 PID 단위 70/15/15 분할을 사용했다.
- Train/validation/test 사이 PID 중복은 0이다.
- 결측 대치, one-hot 인코딩과 표준화 통계는 train에서만 적합한다.
- 평가 임계값은 validation에서 Recall 0.80을 목표로 선택했으며 test는 선택에 사용하지 않았다.
- 모든 모델은 확률 보정을 적용하지 않았다.

## Pooled 후보 Test 성능

| 모델 | 불균형 처리 | AUROC | AUPRC | Recall | Specificity | F1 | Brier | 평가 임계값 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Logistic Regression** | 없음 | **0.6278** | **0.0397** | 0.7487 | **0.4172** | **0.0604** | **0.0240** | 0.02095 |
| Logistic Regression | class_weight=balanced | 0.6261 | 0.0390 | 0.7436 | 0.4136 | 0.0597 | 0.2397 | 0.44943 |
| Random Forest | 없음 | 0.6245 | 0.0370 | 0.7744 | 0.3900 | 0.0598 | 0.0240 | 0.02135 |
| Random Forest | balanced_subsample | 0.6210 | 0.0354 | **0.8205** | 0.3556 | 0.0601 | 0.1970 | 0.40221 |
| XGBoost | 없음 | 0.6271 | 0.0375 | 0.8000 | 0.3682 | 0.0598 | 0.0240 | 0.01933 |
| XGBoost | scale_pos_weight=38.89 | 0.6219 | 0.0365 | 0.7897 | 0.3709 | 0.0593 | 0.2223 | 0.42156 |

`Brier`는 낮을수록 좋다. 가중 모델의 원시 확률은 학습 목적함수 변경으로 크게 왜곡되므로 보정 전 사용자 확률로 해석하면 안 된다. 비가중 세 모델의 Brier score도 낮은 사건률의 영향을 받으므로 이것만으로 보정 완료를 판단하지 않는다.

## 대표 모델 상세

대표 모델은 `klosa-diabetes-incidence-pooled-logistic-v1`이다.

| Test 혼동행렬 | 건수 |
| --- | ---: |
| True positive | 146 |
| False negative | 49 |
| True negative | 3,216 |
| False positive | 4,492 |

- Test 사건률은 2.47%다.
- 평가 임계값 0.02095에서 Recall 74.87%, Specificity 41.72%다.
- 양성 판정의 오탐이 많아 F1은 0.0604에 불과하다.
- 10분위 Test calibration ECE는 0.0034지만 상위 확률 구간에서 과대·과소 추정이 교차한다.
- 임계값은 연구 비교용이며 운영 판정이나 `low/caution/high` 위험구간으로 사용할 수 없다.

## 대표 모델 연령별 Test 성능

| 연령군 | 표본 | 사건률 | AUROC | AUPRC | Recall | Specificity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 45~64세 | 3,833 | 2.03% | 0.6389 | 0.0472 | 0.5769 | 0.6240 |
| 65~74세 | 2,321 | 2.84% | 0.6411 | 0.0516 | 0.8182 | 0.2736 |
| 75세 이상 | 1,749 | 2.92% | 0.5369 | 0.0321 | 0.9216 | 0.1508 |

75세 이상 AUROC는 0.5369로 무작위 수준에 가깝고 Specificity도 매우 낮다. 높은 Recall만으로 성능이 좋다고 해석할 수 없으며, 운영 검토 전 별도의 개선 또는 무추론 정책이 필요하다.

## 임계값 민감도

모델 6종의 기준 임계값 대비 상대적 하향 실험은 [`KLOSA_THRESHOLD_SCALING_EXPERIMENT.md`](KLOSA_THRESHOLD_SCALING_EXPERIMENT.md)에 기록한다.

대표 모델에서 validation 목표 Recall을 높일수록 Test Recall은 증가하지만 오탐률이 급격히 증가한다.

| Validation 목표 Recall | Test Recall | Test Specificity | Test false-positive rate |
| ---: | ---: | ---: | ---: |
| 0.70 | 0.6615 | 0.5188 | 0.4812 |
| 0.80 | 0.7487 | 0.4172 | 0.5828 |
| 0.90 | 0.8821 | 0.2496 | 0.7504 |
| 0.95 | 0.9538 | 0.1327 | 0.8673 |

현재 데이터에서는 민감도를 높일수록 매우 많은 사용자가 위양성으로 선별된다. 의료 안전·사용자 부담·후속검사 자원을 고려한 운영 임계값 검증이 필요하다.

## 별도 샘플 실험

Wave 9→10 단일 전환 샘플은 pooled 대표 모델과 분리해 기록한다.

| 항목 | 값 |
| --- | ---: |
| 전체 표본 / 사건 | 4,169 / 157 |
| Test 표본 / 사건 | 626 / 24 |
| Logistic AUROC | 0.5058 |
| Logistic AUPRC | 0.0590 |
| Dummy AUPRC | 0.0383 |

단일 전환 샘플은 실행 가능성 확인용이며 최종 모델 선정 근거가 아니다.

## 결론과 사용 제한

기저질환 8개를 추가한 16개 입력 연구 결과는 [`KLOSA_COMORBIDITY_FEATURE_EXPANSION.md`](KLOSA_COMORBIDITY_FEATURE_EXPANSION.md)에 기록한다. 증분 성능은 확인됐지만 운영 입력 계약과 대표 배포 모델은 아직 기존 8개 비가중 Logistic 베이스라인을 유지한다.

교육·소득·가구형태·혼인상태를 추가한 2단계 결과는 [`KLOSA_SOCIOECONOMIC_FEATURE_EXPANSION.md`](KLOSA_SOCIOECONOMIC_FEATURE_EXPANSION.md)에 기록한다. Recall 개선이 일관되지 않아 현재 확장 후보에는 채택하지 않는다.

수면·우울감·주관적 웰빙 5개를 누적 추가한 3단계 결과는 [`KLOSA_MENTAL_RHYTHM_FEATURE_EXPANSION.md`](KLOSA_MENTAL_RHYTHM_FEATURE_EXPANSION.md)에 기록한다. 25개 입력 Random Forest가 Test Recall 0.8000, Specificity 0.4742로 3단계 연구 후보가 됐다. 공통 인지·직접 스트레스 변수는 확인되지 않아 포함하지 않았고, 운영 입력 계약과 배포 모델은 변경하지 않는다.

ADL/IADL·악력·최근 낙상·이동 독립성을 누적 추가한 4단계 결과는 [`KLOSA_PHYSICAL_FUNCTION_FEATURE_EXPANSION.md`](KLOSA_PHYSICAL_FUNCTION_FEATURE_EXPANSION.md)에 기록한다. Recall 절대 우선 순위에서는 30개 입력 XGBoost가 Test Recall 0.8103으로 가장 높지만 Specificity는 0.4131이다. Recall 0.80 이상에서 오탐까지 고려하면 3단계 25개 Random Forest가 더 효율적이며, 운영 입력 계약과 배포 모델은 변경하지 않는다.

이전 조사 대비 BMI·운동·흡연·음주 변화 6개를 누적한 5단계 결과는 [`KLOSA_LONGITUDINAL_CHANGE_FEATURE_EXPANSION.md`](KLOSA_LONGITUDINAL_CHANGE_FEATURE_EXPANSION.md)에 기록한다. 이전 값이 없는 1→2 전환을 양쪽 비교군에서 제외하고 같은 축소 코호트의 30개·36개 모델을 재학습했다. 변화 입력은 Random Forest와 Logistic Recall을 낮췄고 XGBoost에서만 Recall이 개선돼 채택하지 않는다.

최근 3개 조사의 BMI·운동·흡연·음주 추세 9개를 누적한 6단계 결과는 [`KLOSA_THREE_WAVE_TREND_FEATURE_EXPANSION.md`](KLOSA_THREE_WAVE_TREND_FEATURE_EXPANSION.md)에 기록한다. 같은 3~9차 기준 코호트에서 36개·45개 모델을 재학습했다. 45개 Logistic의 Recall은 0.8493이지만 36개 Random Forest보다 양성 1건 추가 선별에 위양성 625건이 증가해 추세 변수를 채택하지 않는다.

동일 전체 코호트 R/S 균형 상위 5개의 클래스 가중치 비교는 [`KLOSA_TOP_BALANCED_CLASS_WEIGHT_COMPARISON.md`](KLOSA_TOP_BALANCED_CLASS_WEIGHT_COMPARISON.md)에 기록한다. RF의 `balanced`·`balanced_subsample`, XGBoost의 음성:양성 비율 가중치, Logistic의 `balanced`를 각각 재학습하고 임계값도 재선택했으나 모든 후보의 R/S 균형이 하락했다. 비가중 3단계 25개 Random Forest를 균형 1순위로 유지한다.

3단계 25개 Random Forest의 사전 정의 변수군 제거 실험은 [`KLOSA_STAGE3_FEATURE_ABLATION.md`](KLOSA_STAGE3_FEATURE_ABLATION.md)에 기록한다. validation Recall 0.80 이상에서 Specificity를 최대화한 결과 전체 25개가 유지됐고 Test R/S 균형도 0.6371로 가장 높았다. 축소가 필수라면 건강 만족도를 제외한 24개가 R/S 균형 0.6312로 가장 가까운 대안이다.

3단계 25개 입력의 PID 단위 5-fold RF·XGBoost 튜닝은 [`KLOSA_STAGE3_GROUP_CV_TUNING.md`](KLOSA_STAGE3_GROUP_CV_TUNING.md)에 기록한다. RF는 기존 파라미터가 다시 선택됐다. XGBoost는 depth 2, min child 20, learning rate 0.05, 300 rounds가 OOF Specificity를 0.3777에서 0.3909로 개선했지만 Test Recall이 기존 XGBoost보다 낮고 RF를 대체하지 못해 연구 후보를 변경하지 않는다.

동일 OOF 예측의 RF+XGBoost soft-voting 결과는 [`KLOSA_STAGE3_GROUP_CV_ENSEMBLE.md`](KLOSA_STAGE3_GROUP_CV_ENSEMBLE.md)에 기록한다. RF 25% + CV 선택 XGBoost 75%, OOF 임계값 0.01906457이 Recall 0.8000에서 Specificity 0.4042로 구성 모델보다 높았다. 역사적 Test에서도 선택 XGBoost보다 개선됐지만 RF 단독의 Recall·R/S 균형을 넘지 못해 연구 후보를 변경하지 않는다.

1. 비가중 Logistic Regression을 단순성, 후보 중 최고 AUROC·AUPRC, 상대적으로 안정적인 원시 확률 때문에 대표 연구 베이스라인으로 유지한다.
2. 절대 성능은 낮고 오탐이 많으므로 운영 배포 기준을 충족했다고 볼 수 없다.
3. 결과는 진단·처방이 아니라 위험 선별과 건강교육 연구에만 사용한다.
4. 공개 API에서는 현재 `risk_category=null`, `decision_threshold=null`을 유지하고 확률을 기본 화면에 표시하지 않는다.
5. 확률 보정, 외부 검증, 임계값 검증, 75세 이상 정책과 40~44세 지원 정책이 결정되기 전 운영 활성화를 금지한다.

## 근거 산출물

- `experiments/diabetes_incidence/baselines/klosa_diabetes_logistic_pooled/metrics.json`
- `experiments/diabetes_incidence/baselines/klosa_diabetes_logistic_balanced_pooled/metrics.json`
- `experiments/diabetes_incidence/baselines/klosa_diabetes_random_forest_pooled/metrics.json`
- `experiments/diabetes_incidence/baselines/klosa_diabetes_random_forest_unweighted_pooled/metrics.json`
- `experiments/diabetes_incidence/baselines/klosa_diabetes_xgboost_pooled/metrics.json`
- `experiments/diabetes_incidence/baselines/klosa_diabetes_xgboost_unweighted_pooled/metrics.json`
- `experiments/diabetes_incidence/candidates/klosa_diabetes_threshold_comparison/operating_points.json`
- `experiments/diabetes_incidence/candidates/klosa_diabetes_label_audit/summary.json`
