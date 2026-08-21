# 트리 전용 Stacking 추가 실험

## 1. 실험 질문

Random Forest, XGBoost, LightGBM의 OOF 예측 확률만 입력으로 사용하고 마지막 Logistic Regression이 최종 결과를 결합하면 Recall이 개선되는지 확인했다.

```text
RF ───────┐
XGBoost ──┼─ OOF 확률 3개 → Logistic Regression → validation 임계값 → 최종 선별
LightGBM ─┘
```

기존 실험과 동일한 seed, 데이터 분할, 표본 수, 입력 변수, 기본 모델 후보를 사용했다. KLoSA와 KNHANES는 서로 다른 타깃이므로 데이터셋 간 성능을 직접 비교하지 않는다.

## 2. 비교 조건

| 항목 | 적용 내용 |
| --- | --- |
| 트리 기본 모델 | Random Forest, XGBoost, LightGBM |
| 트리 Soft Voting | 세 트리 확률의 동일 가중 평균 |
| 트리 OOF Blending | train OOF에서 0.25 단위 가중치 탐색 |
| 트리 Stacking | 세 트리 OOF 확률 → class-balanced Logistic Regression |
| 선택 제약 | Specificity ≥ 0.50, AUPRC lift ≥ 1.05 |
| 선택 순서 | 제약 통과 → Recall → AUPRC → Specificity |
| 임계값 | validation에서 선택 후 test에 고정 적용 |

## 3. KLoSA Test 결과

| 모델 | Recall | Specificity | AUPRC | 판정 |
| --- | ---: | ---: | ---: | --- |
| 기존 Logistic Regression | 0.613 | 0.522 | 0.036 | 기준 후보 |
| 기존 전체 Stacking | 0.653 | 0.516 | 0.037 | Test 성능 참고, validation 선택 후보 아님 |
| 트리 Soft Voting | 0.560 | 0.509 | 0.039 | 제약 통과, Recall 감소 |
| 트리 OOF Blending | 0.560 | 0.530 | 0.038 | 제약 통과, Recall 감소 |
| 트리 Stacking | 0.560 | 0.533 | 0.039 | 제약 통과, Recall 감소 |

KLoSA에서는 세 트리의 공통 오분류가 최종 로지스틱에도 그대로 전달됐다. 양성 사례가 적고 입력 변수가 제한된 조건에서는 트리 전용 Stacking이 기존 LR보다 Recall을 높이지 못했다.

## 4. KNHANES Test 결과

| 모델 | Recall | Specificity | AUPRC | 판정 |
| --- | ---: | ---: | ---: | --- |
| 기존 Logistic Regression | 0.892 | 0.476 | 0.136 | Recall 높지만 Specificity 미달 |
| 기존 전체 Stacking | 0.883 | 0.492 | 0.113 | Specificity 미달 |
| 트리 Soft Voting | 0.833 | 0.524 | 0.092 | 유일한 트리 앙상블 Test 제약 통과 |
| 트리 OOF Blending | 0.858 | 0.484 | 0.096 | Specificity 미달 |
| 트리 Stacking | 0.875 | 0.485 | 0.099 | 개별 트리 대비 Recall 개선, Specificity 미달 |

트리 Stacking은 개별 RF·XGBoost·LightGBM보다 Recall을 높였지만 최소 Specificity를 유지하지 못했다. 트리 Soft Voting은 Recall이 낮아지는 대신 Specificity 기준을 통과해 더 안정적인 대안이었다.

## 5. 결정

- **트리 전용 Stacking을 운영 후보로 승격하지 않는다.** Recall만 보면 개선됐지만 KNHANES Test의 최소 Specificity를 통과하지 못했고 KLoSA에서는 Recall이 감소했다.
- KLoSA는 기존 LR을 validation 선택 후보로 유지한다.
- KNHANES는 고재현율 연구 후보로 기존 전체 Stacking을 유지하되 배포하지 않는다. 균형 후보로 트리 Soft Voting을 별도 보관한다.
- 모든 후보의 상태는 `candidate_internal_not_for_personal_probability_display`로 유지한다.

## 6. 다음 실험

1. KNHANES 트리 Stacking의 validation 최소 Specificity를 0.55~0.60으로 높여 test 여유 구간을 확보한다.
2. Meta Logistic Regression의 `C`와 class weight를 OOF/validation에서 비교한다.
3. KLoSA는 변수 확장 전 트리 복잡도를 더 높이지 않고, 추적기간·생활습관 변수 품질과 양성 표본을 먼저 점검한다.
4. 전체 표본에서 부트스트랩 신뢰구간을 산출해 0.01~0.03 수준 차이가 우연인지 확인한다.
