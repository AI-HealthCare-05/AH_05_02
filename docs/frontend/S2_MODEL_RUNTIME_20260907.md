# S2-MDL 실제 모델 연결

## 목적

`POST /api/v1/prediction-jobs`로 생성한 오늘이·내일이 작업을 Redis Worker가 실제 연구 모델로 추론하고, 결과와 모델 출처를 MySQL에 저장한 뒤 프론트가 안전한 로컬 QA 표시를 받을 수 있게 한다.

이 연결은 연구 후보 모델의 운영 승인을 의미하지 않는다. 로컬 QA에서도 다음 값은 유지한다.

- `display_allowed=false`
- `operational_model_activated=false`
- 원시 점수·개인 확정 발병확률·위험요인 비공개
- 오늘이와 내일이 결과를 비교·평균·합산하지 않음

## 관련 PR 기준

1. #36: 오늘이 shared7 및 미래 first-interval 모델·계약
2. #28: E2E 통합 진단 기준
3. #30: 미래 전망 UI 구조
4. #27, #26, #22, #17, #16: 모델 분리·RF25·추론·실험·안전 표시 기반

## 로컬 모델 배치

모델 바이너리는 Git에 커밋하지 않는다. 전달받은 파일의 SHA-256이 레지스트리와 일치할 때만 Worker가 로딩한다.

```text
models/artifacts/candidates/diabetes_current_screening/knhanes-shared7-sk180-v1/model.joblib
models/artifacts/candidates/diabetes_incidence/rf25-first-interval-survival-ensemble-v1/model.joblib
```

기대 SHA-256:

```text
오늘이 6946553dd321189caa6fda207edd3f7a190b8fe1ed007b9a152958ea1cf2e86f
내일이 36323bad1ba2c115f8c52c4c6460220b960a5bae43787be5b029e2d90d3d488f
```

## 환경 설정

`.env.example`의 경로를 배포 환경에 맞추고 로컬 QA에서만 아래 플래그를 켠다.

```dotenv
S2_MODEL_RUNTIME_ENABLED=true
ML_SHARED7_MODEL_URI=/app/models/artifacts/candidates/diabetes_current_screening/knhanes-shared7-sk180-v1/model.joblib
ML_FIRST_INTERVAL_MODEL_URI=/app/models/artifacts/candidates/diabetes_incidence/rf25-first-interval-survival-ensemble-v1/model.joblib
```

`S2_MODEL_RUNTIME_ENABLED=false`이면 기존 승인·개발 provider 경로가 그대로 동작한다.

## 데이터 흐름

```text
프론트 건강정보 저장
  -> POST /prediction-jobs (current_screening)
  -> Redis Worker -> shared7 실제 추론
  -> predictions + prediction_jobs.result 저장
  -> GET /predictions/{id} -> 로컬 QA 등급만 표시

프론트 건강정보 저장
  -> POST /prediction-jobs (incidence)
  -> Redis Worker -> first-interval 실제 추론
  -> predictions + prediction_jobs.result 저장
  -> GET /predictions/{id} -> 2·4·6년 신호 등급만 표시
```

`prediction_jobs.result`에는 감사·재현을 위한 내부 연구 출력이 저장된다. 공개 API는 내부 점수와 임계값을 내보내지 않는다.

## 진단

서버와 Worker를 실행한 뒤 다음 명령으로 가입부터 API 결과 조회까지 확인한다.

```bash
python scripts/s2_model_e2e.py --base-url http://127.0.0.1:8022
```

성공 기준은 `S2-MDL-PASS`이며, 모델 버전·2/4/6년 구간·공개 차단 플래그를 함께 검사한다.

오류 시 `FRONTEND_DATA_CONNECTION_RULEBASE_20260906.md`의 S2 코드로 보고한다.
