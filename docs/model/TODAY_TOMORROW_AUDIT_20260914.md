# 오늘이·내일이 최신 검증 및 인계 결과

기준: 2026-09-14, PR #55 후속 변경. 이 문서의 로컬 검증 결과와 PR 원격 CI 결과는 구분하며 원격 상태는 PR checks에서 별도로 확인한다.

## 실제 모델 검증

| 항목 | 오늘이 | 내일이 |
|---|---|---|
| 모델 | knhanes-shared8-waist-sk180-research-v1 | rf25-tuned-spec40-v1 |
| 구성 | Logistic/RF 각각 OOF Platt 보정 후 0.7/0.3 | 튜닝 RF |
| sklearn | 1.8.0 | 1.8.0 |
| SHA-256 | aceafb1011afed055da727f63c996f1e35a711e0e01f3a38c349360d2f3ee8fc | e5067dacd50006b8d7681ef9e558a2a3488913ae1db58d15632c842623c05bf8 |
| 해시·로더 계약 | 통과 | 통과 |
| Manifest promotion_status | research_candidate_only | approved |
| operational_model_activated | false | false |
| 연구 추론 display_allowed | false | false |

오늘이 파일은 Manifest의 source 경로 `outputs/ml/knhanes_shared8_waist_sk180_v001/run01/model.joblib`, 내일이는 `models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1/model.joblib`을 명시적으로 공급해 검증했다. 이번 검증으로 PR 작업 폴더에 기본 배포 경로가 자동 공급된 것은 아니다. 파일을 Git에 추가하지 않았다.

내일이 Manifest에는 approved가 있으므로 이전 보고의 “두 모델 모두 research_candidate_only”는 부정확하다. 운영 활성화와 연구 응답 공개 차단은 별도이며, 이 검증에서 승인 정보를 변경하지 않았다.

## 입력·전처리·임계값

오늘이 내부 순서: `age, height_cm, weight_kg, bmi, waist_cm, sex, current_smoker, education`. BMI는 키·체중에서 계산한다. 허리둘레 실측은 보존하고 누락 시 Train-fitted 추정기를 사용한다. 교육 미입력은 NaN이다. 각 모델의 fitted 전처리와 보정기를 재학습하지 않고 그대로 사용했다.

내일이 25개 순서와 누락 정책은 [Manifest](../../models/registry/diabetes_incidence/candidates/rf25-tuned-spec40-v1.json)의 features/missing_value_policy가 기준이다. 필수 API 값 누락은 거부, 선택 수치형은 Train 중앙값+indicator, 선택 범주형은 Train 최빈값이다. 미상 진단력을 ‘없음’으로 만들지 않는다. 운동하지 않는다고 응답하면 일수·시간은 0으로 정규화한다.

두 모델의 기술적 입력 연령은 만 45~105세이고 기진단자는 제외한다. 오늘이 성능 표본은 KNHANES 19세 이상으로, 그 성능을 45~105세 서비스 모집단 성능이라고 표현하지 않는다.

- 오늘이 이진 경계: 0.025988709910244948 이상이면 신호 검출.
- 내일이: 0.017113354352510553 미만 low, 그 이상 high 경계 미만 caution, 0.021153602801262862 이상 high.
- 설명 기준점수와 분류 임계값은 서로 다르다. 기준점수보다 낮아도 임계값보다 높으면 high일 수 있다.

## 저장된 Test 성능 재계산

원자료 전체 Test 추론을 새로 실행한 것이 아니라 Manifest의 고정 TP/FN/TN/FP에서 비율을 재계산했다.

| 항목 | 오늘이 | 내일이 |
|---|---:|---:|
| TP / FN / TN / FP | 364 / 26 / 3985 / 5316 | 164 / 31 / 3102 / 4606 |
| Recall | 0.933333 | 0.841026 |
| Specificity | 0.428449 | 0.402439 |
| PPV | 0.064085 | 0.034382 |
| NPV | 0.993518 | 0.990105 |
| Positive Rate | 0.586111 | 0.603568 |

오늘이는 KNHANES 현재 선별, 내일이는 KLoSA 다음 조사까지 신규 의사진단 선별이다. 라벨과 모집단이 달라 직접 우열 비교에 쓰지 않는다.

## 실제 고정 입력과 XAI

`docs/api/examples/tuned_rf25_valid_input.json`, 기준일 2026-08-31을 사용했다. 반복 전체 응답 일치와 실제 기본 점수 일치를 확인했다.

| 항목 | 오늘이 | 내일이 |
|---|---|---|
| 점수 | 0.057802753905042 | 0.022053512988 |
| 결과 | 이진 신호 true | high |
| 설명 | exact_grouped_shap_missing_reference_v1 | treeshap_tree_path_dependent_v1 |
| 기준점수 | 0.034333847519 | 0.025139416834 |
| 가산성 | 통과 | 통과 |
| 선택 요인 | 주의: 나이·체격 정보, 긍정 없음 | 주의: BMI·교육 수준, 긍정: 나이 |

오늘이는 모든 그룹 조합을 계산한 정확한 Shapley 방식이며, 모든 입력 그룹을 결측으로 두고 fitted 정책을 적용한 기준을 사용한다. 이 기준은 비슷한 사용자 평균이 아니다. 키·체중·BMI는 공동 그룹이다. 내일이는 RF 학습 경로 빈도를 기준으로 한 TreeSHAP이며 one-hot/indicator를 원 변수로 합산한다.

낮음은 긍정 2+주의 1, 주의/높음은 주의 2+긍정 1을 선택한다. 오늘이는 이진 boolean으로 선택한다. 반대 방향이 부족하면 확인된 개수만 표시한다. 큰/보통/작은 영향 경계는 미검증 상태이므로 임의 생성하지 않는다.

API 필드: `status, method, explanation_version, model_version, output_space, reference_value, score, additivity_verified, additive_to_score, shap_claimed, display_allowed, selection_policy, selection_status, items, all_items, other_contribution`. `items`는 최대 3개, 나머지는 감사용 전체 기여 및 잔여 합계다. 숫자·원인·진단을 과장하지 않는 한글 문구를 포함한다.

## 충돌 안내와 프론트 연결

| 오늘이 | 내일이 | 코드·안내 |
|---|---|---|
| 신호 있음 | low | CURRENT_SIGNAL_FUTURE_LOW: 현재 신호 확인 우선, 미래 낮음으로 현재 상태를 배제하지 않음 |
| 신호 없음 | caution/high | CURRENT_LOW_FUTURE_ELEVATED: 현재 진단 의미 없이 미래 선별 정보 안내 |
| 신호 있음 | caution/high | BOTH_SIGNALS_ELEVATED: 현재 의료기관 확인 우선 |
| 신호 없음 | low | BOTH_SIGNALS_LOW: 낮은 선별 결과가 질병 배제는 아님 |
| 누락/실패 | 모든 상태 | MODEL_RESULT_INCOMPLETE: 낮음으로 대체하지 않음 |

백엔드 규칙은 `model_explanations.py:model_comparison_guidance`, 프론트는 `app.js:modelComparisonGuidance`다. 두 모델 모두 공개 가능할 때만 결과 조합 안내를 제공한다.

프론트의 `runPrediction`은 모델 요청 및 두 risk-factors 조회를 병렬 수행한다. `renderXaiExplanationLists`와 `selectXaiFactors`가 승인된 요인을 방향별로 골라 최대 3개 표시한다. 단독 오늘이와 부분 실패 재시도도 지원한다. [실제 JSON 예시](../api/examples/today_tomorrow_xai_research_response.json)와 [세부 계약](XAI_THREE_FACTOR_HANDOFF.md)을 함께 전달한다.

현재 공개 `/predictions/{id}/risk-factors`는 승인 설명 저장 경로가 없어 빈 목록을 반환한다. 실제 설명은 관리자 연구 추론 API 응답에 있다. **계약·렌더링 코드는 준비됐지만 실제 사용자에게 공개하는 종단 연결은 아직 완료 상태가 아니다.** 승인·저장 경로 없이 공개 플래그를 켜지 않는다.

## 새 지연시간 측정

Mac/Python 3.13/sklearn 1.8.0/SHAP 0.52.0, 고정 입력 30회. 기본 추론은 전처리 포함, XAI 포함은 연구 응답 전체. Redis/DB/HTTP 및 큐 대기 제외. 최초 로드는 새 Python 프로세스에서 수행했으나 OS 파일 캐시는 통제하지 않았다.

| 구간 | 오늘이 | 내일이 |
|---|---:|---:|
| Artifact 로드 | 283.1ms | 71.4ms |
| 기본 추론 중앙값 / p95 | 32.5 / 38.3ms | 28.9 / 38.2ms |
| XAI 포함 중앙값 / p95 | 74.2 / 99.8ms | 74.7 / 87.8ms |
| 최초 XAI 포함 호출 (로드 제외) | 115.3ms | 11914.7ms |

내일이 첫 호출에서 SHAP import와 Matplotlib 임시 글꼴 캐시 생성 경고가 발생했다. 최초 초기화 지연이 약 11.9초 전체의 어느 비중인지 분해 측정하지 않았으므로 단일 원인으로 확정하지 않는다. 워밍 후 지연만 보고 최초 요청 지연을 배제하면 안 된다.

코드 확인: Worker 모델 실행 한도는 30초, 프론트 폴링 예산은 35초다. Worker의 `update_job/set_status/publish`와 예측 후 DB 저장은 모델 `wait_for` 밖이다. 프론트 35초에는 대기열·저장 지연도 포함된다. 또한 폴링 루프는 각 HTTP await 전후마다 강제로 중단하지 않으므로 엄밀한 전체 요청 상한과 다르다.

오늘이 연구 Worker 경로는 `predict_research_model`을 호출하므로 XAI가 현재 모델 실행 경로에 포함되어 있다. 후속 risk-factors 조회가 있다고 계산까지 비동기로 분리된 것은 아니다. XAI 분리 작업은 후속 운영 과제다. 실제 배포 큐·Redis·DB 로그는 이번 검증에서 확보하지 않았으므로 30초대 시간초과의 실운영 원인은 미확정이다.

재현:

```bash
python scripts/audit_today_tomorrow_xai.py \
  --today-artifact /path/to/today/model.joblib \
  --tomorrow-artifact /path/to/tomorrow/model.joblib --repeats 30
```

## 검증 및 완료 경계

- 실제 두 해시, 전처리 계약, 고정 입력 반복 추론, XAI 가산성: 통과.
- 성능·임계값 비교: 저장된 검증 결과 기준 완료.
- SHAP 응답·2+1 선택·충돌 안내·프론트 코드·실제 JSON: 제공.
- 파일 누락 시 오류, 설명 실패 시 빈 요인, 미승인 공개 차단: 테스트 통과.
- 관련 Python 테스트: 116 passed, 2 skipped. 프론트: 17 passed.
- 실운영 end-to-end 지연 원인 확정, 공개 설명 저장/조회, 의료·운영 승인: 미완료.
- 원격 CI 상태는 PR #55 checks에서 별도로 확인한다.

스킵된 선택 검증을 포함한 결과를 전체 데이터 재평가 또는 운영 검증 완료라고 표현하지 않는다. `Release Gate`는 공개 XAI·운영 경로 기준 보류다.
