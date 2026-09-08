# 튜닝 RF25 서버 연동 인계서

- 모델 키: `diabetes_incidence`
- 모델 버전: `rf25-tuned-spec40-v1`
- 상태: 연구 후보, 운영 미승인
- 목적: 향후 신규 당뇨병 의사진단 위험 선별과 건강교육
- 금지 용도: 진단, 처방, 약물 시작·중단·용량 변경, 응급환자 분류

## 1. 연동 후보와 성능

PID OOF 튜닝 RF25의 하이퍼파라미터와 25개 입력 순서를 고정했다. High 임계값은
Validation Specificity 0.43 이상에서 Recall을 최대화했다. Test는 임계값을
고정한 뒤 마지막 평가에만 사용했다.

| 항목 | 값 |
|---|---:|
| Recall | 0.8410256410 |
| Specificity | 0.4024390244 |
| AUROC | 0.6635616675 |
| AUPRC | 0.0485492388 |
| F1 | 0.0660624371 |
| Brier Score | 0.0238846650 |
| TP / FN | 164 / 31 |
| TN / FP | 3,102 / 4,606 |
| Test 표본 / 발생 | 7,903 / 195 |

발병자를 놓치지 않는 방향으로 설정했기 때문에 비발병자 중 약 59.8%가 high로
분류될 수 있다. 양성 결과는 진단이 아니라 추가 확인과 건강관리 안내 신호다.

## 2. Artifact와 버전

| 항목 | 값 |
|---|---|
| 서버 공급 경로 | `models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1/model.joblib` |
| 파일명 | `model.joblib` |
| 파일 크기 | 2,290,145 bytes |
| SHA-256 | `e5067dacd50006b8d7681ef9e558a2a3488913ae1db58d15632c842623c05bf8` |
| Manifest | `models/registry/diabetes_incidence/candidates/rf25-tuned-spec40-v1.json` |
| 입력 스키마 | `diabetes-incidence-api-25features-v1` |
| 특성 스키마 | `klosa_stage3_25features_v1` |
| 전처리 버전 | `train-median-indicator-mode-onehot-v1` |
| 임계값 버전 | `validation-spec043-caution-recall090-v1` |
| caution 임계값 | `0.017113354352510553` |
| high 임계값 | `0.021153602801262862` |

모델 바이너리는 Git에 커밋하지 않는다. 신뢰된 빌드 산출물 저장소나 서버 배포
볼륨으로 전달하고, Git에는 Manifest와 체크섬만 둔다. `joblib`은 임의 코드 실행
위험이 있으므로 Manifest의 SHA-256과 일치하는 내부 생성 파일만 로드한다.

## 3. 필수 입력

| 필드 | JSON 형식 | 단위·허용값 | 처리 |
|---|---|---|---|
| `birth_date` | string | `YYYY-MM-DD` | 기준일의 만 나이 계산; 미래 날짜 금지 |
| `sex` | string | `female`, `male` | 모델 `sex` |
| `height_cm` | number | 120~220 cm | BMI 계산 후 모델 입력에서 제외 |
| `weight_kg` | number | 25~250 kg | BMI 계산 후 모델 입력에서 제외 |
| `smoking_status` | string | `never`, `former`, `current` | 모델 범주형 입력 |
| `current_drinker` | boolean | `true`, `false` | 현재 음주 여부 |
| `regular_exercise` | boolean | `true`, `false` | 규칙적 운동 여부 |
| `exercise_days_per_week` | number | 0~7 일/주 | 비운동자는 0으로 강제 |
| `exercise_minutes` | number | 0~720 분/회 | 비운동자는 0으로 강제 |
| `previously_diagnosed_diabetes` | boolean | `false`만 추론 가능 | `true`면 발생모델 대상 아님 |

키 누락과 `null`은 허용하지 않는다. 키가 추가로 전달되면 현재 dataclass 계약에서
거부한다. 파생 BMI 허용 범위는 10~70 kg/m²다.

## 4. 선택 입력

선택 입력은 키 생략 또는 `null`을 허용한다. `null`을 정상 또는 `false`로
바꾸지 않는다. 수치형은 Train 중앙값과 결측 indicator, 범주형은 Train 최빈값과
one-hot 변환을 사용한다. 모든 전처리 통계는 Train에서만 학습됐다.

| 필드 | JSON 형식 | 단위·허용값 | 결측 처리 |
|---|---|---|---|
| `annual_household_income_10k_krw` | number/null | 0~123,500, 만원/년 | `log1p` 후 중앙값·indicator |
| `health_satisfaction_score` | number/null | 0~100 | 중앙값·indicator |
| `economic_satisfaction_score` | number/null | 0~100 | 중앙값·indicator |
| `overall_quality_of_life_score` | number/null | 0~100 | 중앙값·indicator |
| `hypertension_diagnosis` | boolean/null | 진단 여부 | `yes/no/missing` 후 최빈값 |
| `cancer_diagnosis` | boolean/null | 진단 여부 | 동일 |
| `chronic_lung_disease_diagnosis` | boolean/null | 진단 여부 | 동일 |
| `liver_disease_diagnosis` | boolean/null | 진단 여부 | 동일 |
| `heart_disease_diagnosis` | boolean/null | 진단 여부 | 동일 |
| `cerebrovascular_disease_diagnosis` | boolean/null | 진단 여부 | 동일 |
| `psychiatric_disease_diagnosis` | boolean/null | 진단 여부 | 동일 |
| `arthritis_rheumatism_diagnosis` | boolean/null | 진단 여부 | 동일 |
| `education_level` | string/null | `code_1/2/3/4/97` | 최빈값·one-hot |
| `marital_status` | string/null | `code_1/2/3/4/5` | 최빈값·one-hot |
| `household_structure` | string/null | `single_person`, `multi_person` | 최빈값·one-hot |
| `depressed_feeling_last_week` | string/null | `code_1/2/3/4` | 최빈값·one-hot |
| `sleep_difficulty_last_week` | string/null | `code_1/2/3/4` | 최빈값·one-hot |

## 5. 고정 모델 입력 순서

서버가 직접 이 순서를 재구성하지 않는다. `build_standard_model_frame()`을 호출해
다음 25개 순서를 고정한다.

```text
age, sex, bmi, smoking_status, current_drinker, regular_exercise,
exercise_days_per_week, exercise_minutes, hypertension_diagnosis,
cancer_diagnosis, chronic_lung_disease_diagnosis, liver_disease_diagnosis,
heart_disease_diagnosis, cerebrovascular_disease_diagnosis,
psychiatric_disease_diagnosis, arthritis_rheumatism_diagnosis,
log_household_income, education_level, marital_status, household_structure,
health_satisfaction_score, economic_satisfaction_score,
overall_quality_of_life_score, depressed_feeling_last_week,
sleep_difficulty_last_week
```

당뇨병 진단·치료, 미래 차수 값과 정답을 직접 결정하는 변수는 포함하지 않는다.

## 6. 정상 입력과 응답

- 정상 입력: [`tuned_rf25_valid_input.json`](../api/examples/tuned_rf25_valid_input.json)
- 고정 응답: [`tuned_rf25_response.json`](../api/examples/tuned_rf25_response.json)

고정 기준일 `2026-08-31`에서 해당 입력은 다음 핵심 결과를 반환한다.

```json
{
  "risk_score": 0.022053512988,
  "risk_category": "high",
  "risk_category_label": "높음",
  "model_version": "rf25-tuned-spec40-v1",
  "feature_schema_version": "klosa_stage3_25features_v1",
  "input_schema_version": "diabetes-incidence-api-25features-v1",
  "threshold_version": "validation-spec043-caution-recall090-v1",
  "decision_threshold": 0.021153602801262862,
  "applicability": {
    "minimum_age": 45,
    "maximum_age": 105,
    "age_unit": "years"
  },
  "output_status": "research_screening_candidate_not_operationally_approved"
}
```

위험 범주는 `low`, `caution`, `high`이며 한글 표시는 `낮음`, `주의`, `높음`이다.
`risk_score`는 보정된 절대 발병확률로 해석하지 않는다.

## 7. 오류 입력과 서버 매핑

| 사례 | 예시 | 코어 오류 | 권장 HTTP·코드 |
|---|---|---|---|
| 필수값 누락 | [`tuned_rf25_error_missing_required.json`](../api/examples/tuned_rf25_error_missing_required.json) | `ValueError: invalid diabetes risk input` | 422 `ML_INPUT_MISSING` |
| 범위 오류 | [`tuned_rf25_error_out_of_range.json`](../api/examples/tuned_rf25_error_out_of_range.json) | `height_cm must be between 120 and 220` | 422 `ML_INPUT_OUT_OF_RANGE` |
| 적용 연령 외 | [`tuned_rf25_error_unsupported_age.json`](../api/examples/tuned_rf25_error_unsupported_age.json) | `outside the model-supported range 45-105` | 422 `ML_POPULATION_UNSUPPORTED` |
| 기진단자 | `previously_diagnosed_diabetes=true` | `ineligible for an incidence screening model` | 422 `ML_POPULATION_INELIGIBLE` |
| 모델 미탑재 | 파일 없음 | `ModelArtifactUnavailableError` | 503 `ML_MODEL_UNAVAILABLE` |
| SHA 불일치·계약 오류 | 변조 또는 잘못된 Artifact | `ModelContractError` | 503 `ML_MODEL_CONTRACT_ERROR` |

오류 입력에 기본 점수, `1.0`, `high`를 만들어 반환하지 않는다. 건강 입력 원문은
오류 로그에 기록하지 않고 요청 식별자와 오류 코드만 남긴다.

## 8. 서버 재현 명령

저장소 루트에서 실행한다.

```bash
UV_CACHE_DIR=/tmp/uv-cache uv sync --group app --group ai --group dev
./scripts/ml-experiment.sh validate
UV_CACHE_DIR=/tmp/uv-cache ./scripts/ml-experiment.sh run rf_25features_tuned_spec40_v001
```

실행 결과를 신뢰된 서버 경로에 공급한다.

```bash
mkdir -p models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1
cp outputs/ml/rf_25features_tuned_spec40_v001/<UTC_RUN_ID>/model.joblib \
  models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1/model.joblib
openssl dgst -sha256 \
  models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1/model.joblib
```

고정 입력을 서버와 동일한 함수로 실행한다.

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python -m src.ml.inference.diabetes_standard \
  --input-json docs/api/examples/tuned_rf25_valid_input.json \
  --as-of-date 2026-08-31
```

백엔드에서는 `predict_diabetes_risk(payload, as_of_date=...)`를 호출한다. Manifest,
Artifact 경로를 변경해야 할 때만 `manifest_path`, `model_path`를 명시한다.

## 9. 백엔드 전달 사항

- 프로세스 시작 또는 첫 요청에서 Manifest, 파일 존재, SHA-256, 특성 순서,
  임계값 버전을 검증한다.
- Artifact를 요청마다 다시 로드하지 말고 검증된 인스턴스를 캐시한다.
- 기준일을 서버에서 명시적으로 전달해 나이 계산 재현성을 보장한다.
- `ValueError`는 입력 422, Artifact·계약 오류는 503으로 분리한다.
- 입력 원문과 건강정보를 애플리케이션 로그에 기록하지 않는다.
- 연구용 후보이므로 운영 활성화 플래그는 `false`로 유지한다.

## 10. 프론트엔드 전달 사항

- 입력 화면은 필수 10개와 선택 17개만 전송한다.
- 사용자에게는 `낮음/주의/높음` 범주와 건강교육 안내를 표시한다.
- 보정되지 않은 `risk_score`를 백분율 발병확률로 표시하지 않는다.
- 적용 연령은 45~105세이며 기진단자는 신규 발생 위험 추론 대상이 아니다.
- `high`는 당뇨병 확진이 아니라 추가 검사·상담을 고려할 위험 신호다.
- 약물 변경이나 치료 효과를 암시하는 문구를 표시하지 않는다.

## 11. 적용 연령과 한계

- 지원 연령: 추론 기준일 만 45~105세
- 대상: 기저시점 당뇨병 의사진단이 없는 KLoSA 유사 인구
- 라벨: 다음 관찰 시점의 신규 의사진단 자기보고
- 외부 검증: 미완료; KNHANES 또는 별도 코호트 검증 필요
- Test 반복 조회: 선행 실험에서 동일 분할을 반복 확인했으므로 성능 낙관 가능
- 낮은 AUPRC와 Specificity: high 판정의 다수가 실제 비발병자일 수 있음
- 자기보고·탈락 편향과 관찰 간격 차이의 영향을 받을 수 있음
- 절대확률 보정과 임상적 유용성 검증이 완료되지 않음

이 후보는 위험 선별·건강교육 연구용이며 의료진의 진단, 검사와 치료 결정을
대체하지 않는다.
