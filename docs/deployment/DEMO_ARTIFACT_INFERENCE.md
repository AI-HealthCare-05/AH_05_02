# SQLite 데모 배포의 승인 Artifact 추론

이 문서는 기존 사용자가 들어 있는 SQLite 데모 배포를 유지하면서 승인된 오늘이·내일이 모델을 실행하는 임시 배포 계약이다. 진단·처방 기능이 아니라 위험 선별·건강교육 결과만 제공한다.

## 필수 환경변수

```dotenv
DEMO_MODE=true
DEMO_ARTIFACT_INFERENCE_ENABLED=true
PREDICTION_PROVIDER=artifact
MODEL_PRELOAD_ENABLED=true
MODEL_URI=/app/models/artifacts/candidates/diabetes_incidence/rf25-tuned-education4-v2/model.joblib
MODEL_MANIFEST_URI=/app/models/registry/diabetes_incidence/candidates/rf25-tuned-education4-v2.json
CURRENT_SCREENING_RUNTIME=today14
CURRENT_SCREENING_MODEL_URI=/app/models/artifacts/candidates/diabetes_current_screening/knhanes-today14-sk180-service-v3/model.joblib
CURRENT_SCREENING_MANIFEST_URI=/app/models/registry/diabetes_current_screening/candidates/knhanes-today14-sk180-service-v3.json
```

모델 바이너리는 Git에 넣지 않는다. 서버의 `models/artifacts/`에 별도로 공급하고 Registry Manifest는 저장소 버전을 사용한다. FastAPI 이미지는 `ML_RESEARCH_RUNTIME=true` 빌드 인자가 필요하다. 저장소의 `docker-compose.yml`은 이를 기본 적용한다.

## 기동과 검증

```bash
docker compose -f docker-compose.yml -f docker-compose.demo.yml build fastapi
docker compose -f docker-compose.yml -f docker-compose.demo.yml up -d --force-recreate fastapi
docker compose -f docker-compose.yml -f docker-compose.demo.yml ps
curl -fsS http://127.0.0.1:8001/api/v1/ready
```

준비 응답에서 다음을 확인한다.

- `status=ready`
- `future_artifact_path_available=true`
- `current_artifact_path_available=true`
- `demo_artifact_inference_enabled=true`
- `worker_preload_required_for_release=false`

FastAPI 시작 시 두 모델을 한 번 적재해 해시·Manifest·입력 계약을 검증한다. 이후 요청은 프로세스별 메모리 캐시를 재사용한다. 파일 누락, 해시 불일치, 역직렬화 실패 또는 입력 계약 오류가 발생하면 작업은 `MODEL_NOT_READY`로 종료되며 실제 결과처럼 표시하지 않는다.

## SQLite 스키마

컨테이너 시작 시 `python -m app.core.db.upgrade_demo_sqlite`가 기존 SQLite를 보존한 채 필요한 nullable 컬럼만 추가한다. 적용 전에는 SQLite 파일을 복사해 백업한다. MySQL 전환은 사용자·인증 테이블과 전체 마이그레이션이 준비된 별도 작업으로 취급한다.
