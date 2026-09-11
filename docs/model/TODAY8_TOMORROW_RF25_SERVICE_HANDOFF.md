# 오늘이 8변수·내일이 RF25 서비스 연동 인계

## 연동 후보

두 출력은 서로 다른 질문에 답하므로 점수나 임계값을 합치지 않는다.

| 구분 | 모델 버전 | 목적 | 임계값 | 상태 |
|---|---|---|---:|---|
| 오늘이 | `knhanes-shared8-waist-sk180-research-v1` | 현재 당뇨 관련 위험 신호 선별 | `0.025988709910244948` | 연구 후보·운영 미승인 |
| 내일이 | `rf25-tuned-spec40-v1.1-sav` | 다음 관찰 시점 신규 의사진단 위험 선별 | caution `0.01725507070479405`, high `0.02120045257343795` | 연구 후보·운영 미승인 |

오늘이 8변수 순서는 `age`, `height_cm`, `weight_kg`, `bmi`, `waist_cm`, `sex`,
`current_smoker`, `education`으로 고정한다. API는 `birth_date`, `height_cm`,
`weight_kg`, `waist_cm`, `sex`, `smoking_status`, `education_level`을 받고 나이와 BMI를
결정적으로 계산한다. `waist_cm`은 cm 단위 45~160 또는 `null`이다. 실측값은 덮어쓰지
않고, `null`일 때만 Train fold에서 학습된 허리둘레 추정기와 내부 파생변수를 사용한다.
따라서 추정 허리둘레를 임상 측정값처럼 표시하면 안 된다.

내일이는 `diabetes-incidence-api-25features-v1` 계약을 유지한다. 필수 필드 누락과
만 45~105세 밖 입력은 거부하며, 선택 수치형은 Train 중앙값+결측 indicator,
선택 범주형은 Train 최빈값으로 처리한다. 기존 당뇨 진단자는 발생 코호트 대상이 아니다.

## 성능

고정 연도 분할은 Train 2016~2020, Validation 2021~2022, Test 2023~2024다.
오늘이 임계값은 Validation Specificity 0.42 이상에서 Recall을 최대화했다.

| 모델 | Validation R/S | Test R/S | Test PPV | Test AUROC | Test AUPRC | Test TP/FN/TN/FP |
|---|---|---|---:|---:|---:|---|
| 오늘이 8변수 sklearn 1.8 | 0.9325 / 0.4323 | 0.9333 / 0.4284 | 0.0641 | 0.7712 | 0.1175 | 364/26/3985/5316 |
| 내일이 RF25 | 별도 KLoSA Validation 선택 | 0.8359 / 0.4054 | 0.0343 | 0.6634 | 0.0484 | 163/32/3125/4583 |

데이터셋·라벨·분할이 다르므로 두 행은 우열 비교용이 아니다. 과거 Test가 반복 조회된
historical holdout이라는 한계도 유지한다.

## Artifact 공급 및 실행

모델 바이너리는 Git에 올리지 않는다. 신뢰된 전달 경로에서 받은 파일을 체크섬 검증 후
배치한다.

```bash
python scripts/provision-models.py \
  --today-shared8 /trusted/today8/model.joblib \
  --tomorrow /trusted/tomorrow-rf25/model.joblib
```

- 오늘이 경로: `models/artifacts/candidates/diabetes_current_screening/knhanes-shared8-waist-sk180-v1/model.joblib`
- 오늘이 SHA-256: `aceafb1011afed055da727f63c996f1e35a711e0e01f3a38c349360d2f3ee8fc`
- 내일이 경로: `models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1.1-sav/model.joblib`
- 내일이 SHA-256: `b96eaf408982399782073fce97977bef874012cf7d90551120da60266df68ddd`

관리자 연구 API에서는 `/api/v1/research/models/shared8-waist/predict`와
`/api/v1/research/models/tomorrow-rf25/predict`를 사용할 수 있다. 공개 활성화가 아니며
`ML_RESEARCH_ENDPOINTS_ENABLED=true`가 필요하다. Worker 오늘이를 시험하려면
`CURRENT_SCREENING_RUNTIME=shared8-waist`를 명시한다. 기본값 `v061`에는 변화가 없다.

오늘이 재현 명령은 다음과 같다. 원자료와 출력 Artifact는 Git에서 제외한다.

```bash
python -m src.ml.evaluation.reproduce_knhanes_shared7_sk180 \
  --handoff-dir /trusted/today_v061_team \
  --output-dir outputs/ml/knhanes_shared8_waist_sk180_v001/new_run \
  --variant shared8-waist
```

결과는 진단·처방이 아니라 위험 선별과 건강교육 보조 정보로만 사용한다.
