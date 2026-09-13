# 오늘이 8변수·내일이 RF25 v1 모델/XAI/런타임 인계

기준일: 2026-09-14. 오늘이는 연구 후보이고 내일이 Manifest는 `approved`이지만 두 모델 모두 `operational_model_activated=false`이며 XAI 공개는 미승인이다. 결과는 진단·처방이 아니라 위험 선별·건강교육에만 사용한다. `display_allowed=false`인 결과, 모델 누락 또는 추론 실패를 실제 사용자 결과처럼 표시하지 않는다.

## 1. 고정 Artifact 계약

| 구분 | 오늘이: 현재 신호 선별 | 내일이: 약 2년 신규 발병 위험 선별 |
|---|---|---|
| 모델 버전 | `knhanes-shared8-waist-sk180-research-v1` | `rf25-tuned-spec40-v1` |
| 구성 | OOF Platt 보정 Logistic 0.7 + RF 0.3 | 튜닝 Random Forest |
| scikit-learn | 1.8.0 | 1.8.0 |
| Artifact | `models/artifacts/candidates/diabetes_current_screening/knhanes-shared8-waist-sk180-v1/model.joblib` | `models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1/model.joblib` |
| 크기 | 6,707,324 bytes | 2,290,145 bytes |
| SHA-256 | `aceafb1011afed055da727f63c996f1e35a711e0e01f3a38c349360d2f3ee8fc` | `e5067dacd50006b8d7681ef9e558a2a3488913ae1db58d15632c842623c05bf8` |
| Manifest | `models/registry/diabetes_current_screening/candidates/knhanes-shared8-waist-sk180-v1.json` | `models/registry/diabetes_incidence/candidates/rf25-tuned-spec40-v1.json` |
| Threshold 버전 | `shared8-waist-sk180-validation-spec042-v1` | `validation-spec043-caution-recall090-v1` |
| 임계값 | 검사 권고 `0.025988709910244948` | 주의 `0.017113354352510553`, 높음 `0.021153602801262862` |

모델 바이너리는 `.gitignore`의 `models/artifacts/` 규칙으로 제외되며 PR에 포함하지 않는다. 로더는 파일 존재, SHA-256, feature 순서, 모델·Threshold 버전을 모두 확인한 뒤 역직렬화한다. 하나라도 불일치하면 예측 대신 명시적인 오류를 반환한다.

## 2. 입력·전처리 계약

공통 외부 필수값은 `birth_date`, `sex`, `height_cm`, `weight_kg`, `smoking_status`, `current_drinker`, `regular_exercise`, `exercise_days_per_week`, `exercise_minutes`, `previously_diagnosed_diabetes`이다. `previously_diagnosed_diabetes=true`는 모델 입력이 아니라 기존 환자 제외 게이트다. 지원 범위는 만 45~105세이며, 이는 기술적 입력 범위이지 연령별 동일 성능 보장이 아니다.

주요 형식/범위는 다음과 같다.

| 입력 | 형식·단위 | 범위/값 | 처리 |
|---|---|---|---|
| `birth_date` | `YYYY-MM-DD` | 계산 나이 45~105 | 기준일로 만 나이 계산 |
| `sex` | string | `female`, `male` | 범주형 |
| `height_cm` | number, cm | 120~220 | BMI 계산에도 사용 |
| `weight_kg` | number, kg | 25~250 | BMI 계산에도 사용 |
| `waist_cm` | number/null, cm | 45~160 | 오늘이만 사용; null이면 Train-fold 전용 추정기로 추정 |
| `smoking_status` | string | `never`, `former`, `current` | 오늘이는 현재 흡연 여부로 축약 |
| `current_drinker` | boolean | true/false | 내일이 사용 |
| `regular_exercise` | boolean | true/false | false이면 운동일·시간을 0으로 정규화 |
| `exercise_days_per_week` | number, 일/주 | 0~7 | 내일이 사용 |
| `exercise_minutes` | number, 분/회 | 0~720 | 내일이 사용 |

내일이 선택값 15개는 소득, 만족도 3개, 기저질환 8개, 교육·혼인·가구 형태, 우울·수면 항목이다. 선택 수치형 null은 Train 중앙값과 missing indicator, 선택 범주형 null은 Train 최빈값으로 처리한다. 알 수 없는 진단력은 `false`로 가정하지 않고 NaN으로 보존한 뒤 전처리한다. 전체 25개 순서는 Manifest의 `features`가 단일 기준이다.

오늘이 내부 입력 순서는 `age, height_cm, weight_kg, bmi, waist_cm, sex, current_smoker, education`이다. BMI는 키·체중에서 파생한다. 허리둘레가 없으면 Train-fold 안에서 학습한 `AnthropometricWaistEstimator`가 추정하고 `waist_was_estimated` 파생 신호를 함께 만든다. 이후 수치형은 Train 중앙값+indicator, 범주형은 Train 최빈값+one-hot을 사용한다.

## 3. 고정 Test 성능

| 모델 | N | 유병/발병률 | TP / FN / TN / FP | Recall | Specificity | PPV | NPV | Positive rate | AUROC | AUPRC |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 오늘이 8변수 | 9,691 | 0.04024 | 364 / 26 / 3,985 / 5,316 | 0.93333 | 0.42845 | 0.06408 | 0.99352 | 0.58611 | 0.77115 | 0.11746 |
| 내일이 RF25 v1 | 7,903 | 0.02467 | 164 / 31 / 3,102 / 4,606 | 0.84103 | 0.40244 | 0.03438 | 0.99011 | 0.60357 | 0.66356 | 0.04855 |

서로 다른 데이터(KNHANES 단면 vs KLoSA 종단), 라벨, 표본, 분할과 목적이므로 두 행의 성능을 동일 모집단의 직접 우열로 해석하면 안 된다. 낮은 PPV와 높은 positive rate는 Recall 우선 임계값의 비용이며 양성 결과를 진단으로 사용할 수 없다는 근거다.

## 4. 실제 고정 입력 재현 결과

입력은 `docs/api/examples/tuned_rf25_valid_input.json`, 기준일은 `2026-08-31`을 사용했다. 같은 프로세스에서 반복한 전체 응답은 두 모델 모두 완전히 동일했다.

- 오늘이: 내부 점수 `0.057802753905042`, 임계값 이상, 허리둘레는 `estimated`
- 내일이: 점수 `0.022053512988`, `high`
- 두 결과 모두 `display_allowed=false`, `operational_model_activated=false` 또는 연구용 출력 상태이므로 공개 결과가 아니다.

재현 명령:

```bash
TEST_SHARED8_ARTIFACT=models/artifacts/candidates/diabetes_current_screening/knhanes-shared8-waist-sk180-v1/model.joblib \
TEST_RF25_ARTIFACT=models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1/model.joblib \
pytest -q tests/ml/test_actual_service_candidates.py
```

실제 호출은 `predict_research_model("shared8-waist", ...)`와 `predict_research_model("tomorrow-rf25", ...)`를 사용한다. 고정 응답 구조는 `docs/api/examples/today_tomorrow_xai_research_response.json`에 기록했다.

## 5. XAI 응답 계약

오늘이는 보정·앙상블까지 포함한 최종 출력 함수에 `exact_grouped_shap_missing_reference_v1`을 적용한다. 키·체중·BMI는 파생 관계를 보존하도록 하나의 `body_measurements` 그룹으로 묶고, 모든 그룹 조합을 계산한다. 기준점수는 모든 입력 그룹을 결측으로 둔 뒤 고정된 Train 전처리를 적용한 점수이며 모집단 평균이 아니다.

내일이는 고정 RF25의 positive class에 `treeshap_tree_path_dependent_v1`을 적용한다. 전처리 후 one-hot과 결측 indicator 기여는 원래 25개 변수 단위로 다시 합산한다. 두 설명 모두 `기준점수 + 전체 기여도 = 실제 점수`를 절대오차 `1e-8` 안에서 검증한다.

```json
{
  "status": "research_only",
  "method": "treeshap_tree_path_dependent_v1",
  "explanation_version": "three-factor-shap-v1",
  "output_space": "risk_score",
  "additive_to_score": true,
  "additivity_verified": true,
  "reference_value": 0.025139416834,
  "score": 0.022053512988,
  "items": [
    {
      "feature": "bmi",
      "display_name": "BMI",
      "direction": "increase",
      "display_group": "caution",
      "contribution": 0.005374786205,
      "absolute_contribution": 0.005374786205,
      "modifiable": true,
      "message": "입력 정보가 기준점수 대비 모델 점수를 높이는 방향으로 반영되었습니다."
    }
  ],
  "selection_policy": "elevated-2-caution-1-positive-otherwise-2-positive-1-caution-v1",
  "shap_claimed": true,
  "display_allowed": false,
  "limitations": ["not causal", "not a diagnosis", "correlated features affect attribution"]
}
```

계산 검증과 공개 승인은 별개다. 실제 SHAP이므로 `shap_claimed=true`이지만 `status=research_only`, `display_allowed=false`를 유지한다. 높은 결과는 주의 요인 2개+긍정 요인 1개, 낮은 결과는 긍정 요인 2개+주의 요인 1개를 절댓값 순으로 고른다. 해당 방향이 부족하면 억지로 세 개를 채우지 않는다. 상세 계약은 [SHAP 3요인 인계](XAI_THREE_FACTOR_HANDOFF.md)를 따른다.

## 6. 모델 결과 충돌 안내

프론트는 두 모델이 모두 승인·공개 가능한 경우에만 아래 결과 조합을 표시한다.

| 코드 | 조건 | 안내 원칙 |
|---|---|---|
| `CURRENT_SIGNAL_FUTURE_LOW` | 현재 높음, 미래 낮음 | 현재 신호 확인 우선; 미래 낮음이 현재 상태를 배제하지 않음 |
| `CURRENT_LOW_FUTURE_ELEVATED` | 현재 낮음, 미래 주의/높음 | 현재 진단이 아니라 정기 검사·생활습관 점검용 미래 선별 신호 |
| `BOTH_SIGNALS_ELEVATED` | 현재 높음, 미래 주의/높음 | 현재 의료기관 확인 우선 |
| `BOTH_SIGNALS_LOW` | 현재 낮음, 미래 낮음 | 낮음도 당뇨병 배제가 아니며 정기 확인 필요 |
| `MODEL_RESULT_INCOMPLETE` | 하나 이상 실패/누락 | 실패를 낮음으로 대체하지 않고 재시도 안내 |
| `MODEL_RESULT_NOT_PUBLIC` | 연구·미승인 결과 포함 | 내부 점수로 사용자 충돌 설명을 만들지 않음 |

백엔드와 프론트의 동일 규칙 구현은 각각 `src/ml/inference/model_explanations.py`의 `model_comparison_guidance`, `src/frontend/app.js`의 `modelComparisonGuidance`다.

## 7. 프론트 연결

두 분석은 이미 `Promise.all`로 병렬 요청된다. 각 `/predictions/{id}` 결과를 받은 뒤 두 모델의 `/predictions/{id}/risk-factors`도 병렬 조회한다. 요인 카드는 `status=approved`, `shap_claimed=true`인 검증된 SHAP 응답에서만 렌더링하며, 현재 연구 설명은 숨긴다. 모델 충돌 안내도 두 결과의 공개 승인 조건을 통과한 경우에만 조합별 문구를 표시한다.

현재의 연구 설명은 관리자용 `/api/v1/research/models/infer` 응답에만 포함된다. 공개 `/predictions/{id}/risk-factors`는 승인된 설명이 저장되기 전까지 `items=[]`, `display_allowed=false`, `shap_claimed=false`를 반환한다.

```javascript
const [current, future] = await Promise.all([
  requestPredictionModel("diabetes_current_screening"),
  requestPredictionModel("diabetes_incidence"),
]);
renderModelComparisonGuidance(
  { status: "succeeded", ...current },
  { status: "succeeded", ...future },
);
```

## 8. 지연시간 및 시간초과 점검

Mac 로컬, Python 3.13/scikit-learn 1.8.0/SHAP 0.52.0에서 고정 입력을 30회 측정했다. 네트워크·Redis·DB 시간은 제외한 모델 프로세스 실측이며 OS 파일 캐시는 통제하지 않았다.

| 구간 | 오늘이 | 내일이 |
|---|---:|---:|
| 최초 Artifact 검증+로드 | 283.1 ms | 71.4 ms |
| 전처리+기본 추론 중앙값 / p95 | 32.5 / 38.3 ms | 28.9 / 38.2 ms |
| SHAP 포함 전체 중앙값 / p95 | 74.2 / 99.8 ms | 74.7 / 87.8 ms |
| 최초 SHAP 호출, Artifact 로드 제외 | 115.3 ms | 11,914.7 ms |

기본 모델 계산은 30ms 안팎이므로 화면의 30~35초 시간초과를 단독으로 설명하지 못한다. 다만 내일이 첫 SHAP import에서 Matplotlib 임시 캐시·폰트 초기화 경고와 함께 약 11.9초가 측정되어 cold-start를 무시하면 안 된다. Worker 대기열, Redis 전달/폴링, DB 기록, 프로세스 재시작과 Artifact 미탑재 여부는 배포 로그가 없어 아직 원인을 확정할 수 없다. 현재 연구 Worker는 XAI를 모델 실행 안에서 계산하므로 운영 전 기본 결과와 설명 계산을 분리해야 한다.

운영 점검 로그에는 `queue_wait_ms`, `artifact_load_ms`, `preprocess_ms`, `predict_ms`, `explain_ms`, `persist_ms`, `end_to_end_ms`, `worker_pid`, `model_version`을 남긴다. 기본 결과를 먼저 저장한 뒤 XAI 실패는 모델 결과를 실패시키지 않도록 한다.

## 9. Release Gate 의견

현 상태는 공개 XAI·운영 경로 기준 **보류**다. Artifact 해시·고정 입력 재현·입력 계약·SHAP 가산성·오류 시 fail-closed는 확인했다. 다만 오늘이는 반복 확인된 과거 Test와 허리둘레 이중 추정 불확실성, 내일이는 낮은 PPV와 wave/외부 일반화 미완료가 남아 있다. 영향도 `큰/보통/작은` 경계, 설명 안정성, 승인 설명 저장·조회, 의료 안전 검토 후에만 XAI 공개 플래그를 승인할 수 있다.
