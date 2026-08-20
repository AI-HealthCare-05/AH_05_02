# 건강정보 입력·예측 API 임시 연동

오늘 구현은 모델 연결을 확인하기 위한 **동기식 임시 API**다. Redis·DB 저장과
`/prediction-jobs` 비동기 처리는 포함하지 않는다.

## 수인 전달용 요청 예시

```http
POST /api/v1/predictions/preview
Content-Type: application/json
```

```json
{
  "birth_date": "1970-01-01",
  "sex": "female",
  "height_cm": 160,
  "weight_kg": 60,
  "smoking_status": "never",
  "current_drinker": false,
  "regular_exercise": true,
  "exercise_days_per_week": 3,
  "exercise_minutes": 40,
  "previously_diagnosed_diabetes": false
}
```

## 수인 전달용 응답 예시

```json
{
  "data": {
    "prediction_id": "e7c31ac6-d938-431c-9cf8-ab76c67717bb",
    "condition": "diabetes",
    "model_type": "future_incidence",
    "data_source": "klosa",
    "target_horizon": "next_wave_about_2y",
    "risk_category": "moderate",
    "risk_category_label": "주의",
    "predicted_class": 0,
    "model_version": "temporary-integration-v1",
    "target_definition_version": "klosa-diabetes-incidence-next-wave-v1",
    "input_schema_version": "diabetes-incidence-input-v1",
    "feature_schema_version": "diabetes-incidence-input-v1",
    "preprocessing_version": "temporary-preprocessing-v1",
    "calibration_version": "none-v1",
    "predicted_at": "2026-08-20T03:20:04Z",
    "is_temporary": true,
    "safety_notice": {
      "summary": "다음 약 2년의 관찰기간 동안 신규 당뇨병 진단 위험을 선별한 참고 결과입니다.",
      "is_medical_diagnosis": false,
      "message": "이 결과는 의료진의 진단이나 처방을 대신하지 않습니다."
    }
  }
}
```

원시 모델 점수는 API 응답에 노출하지 않는다. 현재 위험 범주는 연동 확인용 임시값이며
최종 임계값이 아니다.

모델 입력은 아래 allowlist만 허용한다. `birth_date`, `height_cm`, `weight_kg`는
각각 `age`, `bmi` 계산에만 쓰고 `previously_diagnosed_diabetes`는 적합성 차단에만 쓴다.

```text
age, sex, bmi, smoking_status, current_drinker, regular_exercise,
exercise_days_per_week, exercise_minutes
```

## 준혁 확인·공유 사항

- 실제 단일 사용자 추론 함수의 모듈 경로와 함수 시그니처
- 입력 형식(dict, DataFrame 또는 배열), 정확한 컬럼 순서와 자료형
- `female`, 흡연, 음주, 신체활동의 최종 인코딩
- 결측값 허용 여부와 대체 방법
- 반환값 구조, 양성 클래스 정의, 보정 확률 여부
- 모델·타깃·입력 스키마·보정·임계값 버전
- 최종 위험 범주 임계값과 위험·보호 요인 반환 방식

실제 함수가 전달되면 `src/ml/inference/diabetes_model.py`의
`predict_single_user()` 내부만 교체한다.

## 멘토 확인 사항

- 운영 API를 동기식으로 유지할지 `/api/v1/prediction-jobs` 비동기로 전환할지
- Redis에 둘 단기 상태와 DB에 남길 요청·완료·실패 최소 이력
- 최종 위험 범주 임계값 승인 및 사용자 공개 범위
