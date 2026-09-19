# 예측 작업(Prediction Job) 오류 코드 안내 — 프론트엔드 공유용

작성일: 2026-09-08
대상: `POST /api/v1/prediction-jobs` (오늘이 `diabetes_current_screening`, 내일이 `diabetes_incidence`) 및 `GET /api/v1/prediction-jobs/{job_id}` 응답 처리

이 문서는 실제 Docker 환경에서 4가지 장애 상황(모델 파일 없음 x2, Redis 장애, 타임아웃)을 직접 재현해서 확인한 결과를 바탕으로 작성했습니다. 표에 "검증"이라고 표시된 항목은 오늘 실제로 재현해서 응답을 확인한 것이고, "코드 확인"은 코드상 존재는 확인했지만 실제로 트리거해서 응답을 보지는 않은 항목입니다.

## 1. 작업 생성 단계 오류 (HTTP 응답, `POST /prediction-jobs`)

작업 생성 자체가 실패하면 `job_id`가 발급되지 않고, HTTP 에러 응답으로 바로 내려옵니다. 이 경우 폴링할 대상이 없으므로 프론트는 이 응답만 보고 바로 처리하면 됩니다.

| error_code | HTTP | 상황 | retryable | 확인 상태 |
|---|---|---|---|---|
| `MODEL_NOT_READY` | 503 | 요청한 model_key에 활성화된(is_active) 모델이 없음 (예: 모레노/`diabetes_lifetime_risk`) | false | 검증 (스모크 테스트) |
| `QUEUE_UNAVAILABLE` | 503 | Redis 작업 큐에 연결 불가 | **true** | 검증 |

**QUEUE_UNAVAILABLE 실제 응답 예시:**
```json
{"detail":{"error_code":"QUEUE_UNAVAILABLE","message":"Redis 작업 큐에 연결할 수 없습니다.","retryable":true}}
```
HTTP 503으로 내려옵니다. 안내 문구 예시: "일시적으로 서버가 혼잡합니다. 잠시 후 다시 시도해 주세요."

## 2. 작업 처리 단계 오류 (`GET /prediction-jobs/{job_id}` 폴링 결과, `status: "failed"`)

작업 생성은 성공(`job_id` 발급)했지만 Worker가 처리하는 도중 실패한 경우입니다. 폴링 응답의 `status`가 `"failed"`로 오고, `error_code`/`retryable`/`retry_after_seconds` 필드를 보고 분기하면 됩니다.

| error_code | 상황 | retryable | retry_after_seconds | 확인 상태 |
|---|---|---|---|---|
| `TIMEOUT` | 추론이 제한 시간(기본 30초) 내에 끝나지 않음 | **true** | **30** | 검증 |
| `MODEL_UNAVAILABLE` | 오늘이(현재선별) 모델 아티팩트 파일 없음 | false | null | 검증 |
| `MODEL_CONTRACT_INVALID` | 오늘이 모델 아티팩트가 매니페스트와 계약 불일치(SHA256/threshold 등) | false | null | 코드 확인 |
| `ML_MODEL_UNAVAILABLE` | 내일이(RF25) 또는 연구용(shared7/first-interval) 모델 아티팩트 파일 없음 | false | null | 검증 |
| `ML_MODEL_CONTRACT_ERROR` | 내일이/연구용 모델 계약 불일치 | false | null | 코드 확인 |
| `ML_INPUT_MISSING` | 입력값 중 필수 항목 누락 | false | null | 코드 확인 |
| `ML_POPULATION_UNSUPPORTED` | 나이 등 모델 지원 범위를 벗어남 | false | null | 코드 확인 |
| `ML_POPULATION_INELIGIBLE` | 내일이 모델 대상이 아닌 인구집단(예: 이미 당뇨 진단자) | false | null | 코드 확인 |
| `ML_INPUT_OUT_OF_RANGE` | 위 세 가지 외의 입력값 범위 오류 | false | null | 코드 확인 |
| `INFERENCE_FAILED` | 위 어디에도 해당하지 않는 미분류 오류 (예상치 못한 예외) | false | null | 코드 확인 |

**TIMEOUT 실제 응답 예시** (`PREDICTION_TIMEOUT_SECONDS=1`로 낮춰서 재현):
```json
{
  "status": "failed",
  "error_code": "TIMEOUT",
  "retryable": true,
  "retry_after_seconds": 30
}
```

**MODEL_UNAVAILABLE / ML_MODEL_UNAVAILABLE**는 모델 파일을 실제로 치워서 재현했고, 두 워커(오늘이/내일이) 모두 정상적으로 즉시(`failed`, 1초 이내) 종결되는 것을 확인했습니다. 재시도해도 같은 이유로 계속 실패하므로 `retryable: false`입니다.

## 3. 프론트 처리 가이드

- **`retryable: true`인 경우만** (`QUEUE_UNAVAILABLE`, `TIMEOUT`) 자동/수동 재시도 UI를 노출하세요. `retry_after_seconds`가 있으면 그 시간만큼 대기 후 재시도를 권장합니다.
- **`retryable: false`인 경우**는 같은 요청을 반복해도 결과가 바뀌지 않으므로, 재시도 버튼 대신 "잠시 후 다시 이용해 주세요" 또는 상황에 맞는 안내(예: `ML_POPULATION_INELIGIBLE`이면 "이 서비스 대상이 아닙니다")로 처리하세요.
- **가짜 결과 없음**: 위 오류 상황 전부 `status: "failed"`이고 `prediction_id: null`입니다. 즉 실패 시 절대 임의의 예측값이나 기본값이 화면에 노출되지 않습니다. 프론트도 `status`를 반드시 확인한 뒤에만 결과 필드를 렌더링해야 합니다.
- **폴링 타임아웃**: 20회(약 40초) 폴링 후에도 `status`가 `succeeded`/`failed`로 안 바뀌면 (네트워크 문제 등) "처리가 지연되고 있습니다" 안내와 함께 나중에 확인할 수 있는 링크(`status_url`)를 보여주는 걸 권장합니다.

## 4. 검증 방법 (재현 스크립트)

이 표의 "검증" 항목들은 `scripts/failure-injection-test.sh`로 재현했습니다. 필요하면 언제든 재실행해서 회귀 확인이 가능합니다.

```bash
bash scripts/failure-injection-test.sh model-today      # MODEL_UNAVAILABLE
bash scripts/failure-injection-test.sh model-tomorrow    # ML_MODEL_UNAVAILABLE
bash scripts/failure-injection-test.sh redis             # QUEUE_UNAVAILABLE
bash scripts/failure-injection-test.sh timeout           # TIMEOUT
```
