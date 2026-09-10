# rf_oof_feature_reduction_v001

- 담당자: 양준혁
- 상태: 연구용 후보, 운영 미승인

## 실험 가설

현재 RF 25변수 중 중요도가 낮거나 fold 간 불안정한 변수를 제거하면 Recall 0.80을 유지하면서 Specificity와 재현성을 개선할 수 있다.

## 사용 데이터와 입력 변수

- 데이터 버전: `official_v1`
- 분할 버전: `pid_group_70_15_15_stratified_any_event_rs42_v1`
- 입력 후보 스키마: `klosa_stage3_nested_oof_selected_10_25_v1`
- 원본 후보: RF 25개 t0 변수 전체
- 비교 크기: 25, 20, 15, 10개

## 제외 변수와 제외 이유

- 미래 시점 변수와 현재·미래 당뇨 진단·치료 변수
- PID, 가구 ID와 target
- 바깥 PID 5-fold의 검증부는 변수 중요도 계산에서 제외
- 각 바깥 학습부 내부 PID 3-fold에서만 permutation importance 산출
- Validation은 최종 임계값 선택에만 사용하고 Test는 마지막 보고에만 사용
- 모든 결측 대체와 One-Hot 변환은 각 fold 학습부에서만 적합

## 모델과 하이퍼파라미터

현재 최고 RF 설정을 고정한다: 500 trees, depth 8, minimum leaf 20, `max_features="sqrt"`, 비가중. 변수 선택 효과만 비교한다.

Permutation importance는 각 inner fold에서 변수 하나를 섞었을 때 `Recall >= 0.80` 작동점의 Specificity 감소량으로 정의한다. 양의 중요도를 보인 fold 비율, 평균과 표준편차를 함께 기록하고 `평균-표준편차` 안정성 점수로 순위를 정한다.

25개 모델은 전체 변수를 사용한다. 20·15·10개 축소 모델은 상관된 건강·경제·삶의 만족도 3개 중 Train 내부 중요도가 가장 안정적인 대표 하나만 유지한다.

## 임계값 결정 방법

Train nested OOF에서 변수 수를 확정한 뒤 최종 변수를 Train 정보만으로 결정한다. 최종 모델은 Train 전체에서 학습하며 임계값은 Validation Recall 0.80 이상을 만족하는 값 중 Specificity가 가장 높은 값으로 선택한다.

## 평가 결과

- 최신 실행 ID: `20260825T051558622722Z`
- 실행 상태: `constraint_passed`
- 선택 결과: **25개 전체 유지**

| Train nested OOF 변수 수 | Recall | Specificity | AUROC | AUPRC | Threshold |
| ---: | ---: | ---: | ---: | ---: | ---: |
| **25** | 0.8000 | **0.3614** | **0.6307** | 0.0405 | 0.01978379 |
| 20 | 0.8000 | 0.3357 | 0.6267 | 0.0422 | 0.01907923 |
| 15 | 0.8000 | 0.3286 | 0.6249 | **0.0425** | 0.01884866 |
| 10 | 0.8000 | 0.3317 | 0.6252 | 0.0419 | 0.01841910 |

Recall 0.80에서 25개 전체 대비 Specificity는 20개에서 2.57%p, 15개에서 3.28%p, 10개에서 2.97%p 낮았다. 축소안의 AUPRC가 소폭 높아진 경우는 있었지만 Recall 중심 선택 기준에서는 25개 전체가 우세했다.

최종 25개 모델은 Validation Recall 0.8000, Specificity 0.4941에서 임계값 0.02241084가 선택됐다. Test는 Recall 0.8000, Specificity 0.4742, AUROC 0.6596, AUPRC 0.0511이며 TP 156, FN 39, TN 3,655, FP 4,053이다. 25개 전체가 선택됐으므로 현재 최고 모델과 결과가 동일하다.

### 중요도 안정성

- 안정성 점수(`평균 Specificity 감소-표준편차`)가 양수인 변수: `bmi` 0.01172, `age` 0.01005
- 나머지 변수는 개별 중요도가 작거나 fold 간 변동이 컸다.
- 만족도 변수의 Train 상관계수는 0.587~0.650으로 중간 수준이었다.
- 축소안에서는 세 만족도 변수 중 `overall_quality_of_life_score`가 대표로 선택됐다.

이 결과는 BMI와 연령이 가장 안정적인 단일 신호임을 보여주지만, 그 외 변수의 약한 결합 신호를 대량 제거하면 Recall 0.80 작동점의 Specificity가 하락함을 뜻한다. 따라서 RF 입력을 20개 이하로 축소하지 않는다.

상세 fold별 중요도와 변수 수별 합의 특성은 `outputs/ml/rf_oof_feature_reduction_v001/20260825T051558622722Z/feature_selection_results.json`에 기록했다.

## 한계와 다음 실험

이 결과는 진단이나 처방이 아닌 위험 선별·건강교육 목적의 연구 결과다.

- permutation importance는 변수 간 상관이 있을 때 중요도를 분산시킬 수 있다.
- 선택 안정성은 KLoSA 내부 분할에 대한 결과이며 외부 타당성을 보장하지 않는다.
- 기존 Test는 과거 실험에서 이미 조회되어 완전히 미사용된 최종 holdout이 아니다.
