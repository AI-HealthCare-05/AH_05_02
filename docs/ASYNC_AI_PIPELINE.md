# 비동기 AI 작업 파이프라인

## 바로 실행

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-ai-pipeline.ps1
```

`start-local.ps1`은 Windows 한글 경로에서 Docker Compose의 동시 빌드가 실패하는 경우를 피하기 위해 FastAPI와 AI Worker 이미지를 순서대로 빌드한다.

Swagger UI: <http://localhost/api/docs>

## 실행 흐름

1. `POST /api/v1/ai-jobs`가 MySQL에 작업 이력을 생성한다.
2. FastAPI가 Redis Stream `ai:jobs`에 작업을 `XADD`한다.
3. `ai-workers` Consumer Group의 Worker 3개 중 하나가 `XREADGROUP`으로 작업을 가져온다.
4. Worker는 시작·완료·실패 상태를 MySQL과 Redis에 기록한다.
5. `GET /api/v1/ai-jobs/{job_id}`로 최종 상태를 조회한다.
6. `GET /api/v1/ai-jobs/{job_id}/events`는 SSE로 상태 변경을 전송한다.
7. 장시간 미처리 Pending 작업은 `XAUTOCLAIM`으로 다른 Worker가 회수한다.

## 작업 종류

- `demo_inference`: 모델 없이 전체 파이프라인을 검증하는 안전한 데모 작업
- `model_inference`: `MODEL_URI`의 scikit-learn/joblib 모델로 추론하는 작업

`model_inference` 요청의 `payload.features`에는 모델 학습 때와 같은 순서의 숫자 배열을 전달한다.

## 모델 저장소

- 로컬: 모델 파일을 저장소의 `models/`에 두고 `MODEL_URI=/app/storage/models/model.joblib`
- AWS S3: `MODEL_URI=s3://버킷/경로/model.joblib`

로컬 `models/`는 Worker에서 읽기 전용으로 마운트된다. S3 모델은 `/app/storage/cache`에 내려받는다. S3를 사용할 때만 `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`를 배포 환경변수로 주입한다. 비밀값은 Git에 저장하지 않는다.

## 의료 안전

데모와 모델 추론 결과는 위험 선별 보조용이며 진단·처방으로 표시하지 않는다. 실제 당뇨 예측 모델을 연결할 때는 학습·검증·테스트 분리, 데이터 누수 점검, 모델 버전 고정과 의료 안전 테스트를 별도로 수행한다.
