# 예측 분석 시간초과 처리 점검 (2026-09-08)

## 확인 결과

- 프론트는 오늘이와 내일이 작업을 순차 요청하고 있었음.
- 프론트 Polling은 35초 후 자체 종료했으며, 서버·Worker 기본 제한은 각각 30초였음.
- 백엔드는 작업 생성 시점에 `deadline_at`을 정하므로 큐 대기시간도 30초 제한에 포함됨.
- Worker는 작업 시작 후 모델 로딩과 추론 전체에 같은 30초 제한을 적용함.
- 부분 성공 결과 보존과 실패한 모델만 재시도하는 프론트 동작은 이미 구현되어 있었음.
- 로컬 Docker Worker가 컨테이너 안에서 `localhost:6379`를 바라봐 Redis Stream을 읽지 못하는 실행 설정을 확인함.

## 프론트 반영

- 오늘이·내일이 작업을 `Promise.all()`로 함께 시작하고 각 요청 내부에서 성공·실패를 독립 처리함.
- 한 모델이 실패해도 다른 모델의 성공 결과를 유지함.
- 재시도 시 실패한 모델만 다시 요청함.
- Polling 상한을 35초로 유지해, 두 모델 병렬 실행 시 체감 대기시간이 모델 하나의 제한시간 수준을 넘지 않도록 함.
- 입력 변경·로그인 세션 변경 시 이전 비동기 응답이 현재 화면 상태를 덮어쓰지 않도록 기존 보호 로직을 유지함.

## 로컬 Docker 실행 설정 반영

- Docker의 FastAPI와 AI Worker가 `redis:6379`, `mysql:3306`을 사용하도록 Compose 서비스 내부 주소를 명시함.
- 호스트에서 직접 실행하는 8022 서버의 localhost 포트 설정과 컨테이너 내부 서비스 주소가 섞이지 않도록 분리함.
- 현재 Compose 재실행에서는 DB 인증 변수가 전달되지 않아 Docker Worker가 MySQL 1045로 재시작했으므로 해당 Worker 3개는 중지함.
- Docker DB 비밀번호를 추측하거나 코드에 기록하지 않았고 `.env` 내용도 열거나 수정하지 않음.

## 8022 실제 연동 재검증

- 8022와 같은 DB 설정 및 전용 Redis Stream을 쓰는 로컬 Worker를 실행함.
- Redis `local8022-workers` 상태는 consumer 1, pending 0, lag 0으로 확인함.
- `scripts/s2_model_e2e.py`로 가입 → 건강정보 저장 → 오늘이 → 내일이 → 결과 저장을 재검증함.
- 결과는 `S2-MDL-PASS`이며 두 모델 모두 `succeeded`로 종료됨.
- 전체 실행은 약 6초 안에 끝났고, 수치·확률은 노출하지 않은 채 `display_allowed=false`, `operational_model_activated=false` 안전 조건을 유지함.

## 백엔드·Worker 후속 확인

- FastAPI와 AI Worker에 동일한 `PREDICTION_TIMEOUT_SECONDS`를 적용하고 실제 처리시간을 함께 측정해야 함.
- `queued_at`, `started_at`, `completed_at`, `worker_name`, `attempts`, `error_code`를 같은 `job_id`로 대조해야 함.
- 큐 대기 제한과 Worker 추론 제한을 서로 다른 설정으로 분리하는 계약 확정 필요함.
- Worker 시작 시 오늘이·내일이 Artifact와 전처리기를 사전 로딩하고, 실패 시 Health Check 실패로 표시하는 작업 필요함.
- 병렬 실행 전후의 CPU·메모리·Worker 처리량 측정 필요함.

## 판정

- 8022 로컬 시연 환경: 큐·Worker·두 모델 추론 성공까지 확인함.
- 프론트: 두 작업 병렬 시작, 35초 Polling, 부분 성공 보존을 테스트로 확인함.
- Docker Compose 전체 환경: DB 인증 전달과 FastAPI health 복구 후 별도 재검증이 필요함.
- 서버의 큐 대기·추론 제한 분리와 Worker 사전 로딩은 백엔드 후속 과제로 유지함.
