# EC2 운영 배포 체크리스트

## 1. 릴리스 PR 기준

- [ ] 모든 기능 PR은 `develop`에 병합되고, 릴리스 PR은 `develop → main`으로 생성한다.
- [ ] 릴리스 PR에는 포함 커밋, 변경 기능, DB 마이그레이션, 모델 버전·임계값 버전, 롤백 방법을 기록한다.
- [ ] CI, Ruff, Pytest 및 핵심 사용자 흐름 테스트가 릴리스 커밋에서 통과한다.
- [ ] 예측 결과가 진단·처방이 아닌 위험 선별·건강교육이라는 문구와 기진단자 차단 흐름을 다시 확인한다.
- [ ] 원본 의료데이터, 개인 건강정보, `.env`, API 키, joblib 모델 파일이 PR·이미지 빌드 컨텍스트에 포함되지 않았는지 확인한다.

릴리스 브랜치를 만들기 전에는 승인되지 않은 기능 PR을 임의로 포함하지 않는다. 기능별 리뷰·CI 완료 후, 담당자가 `develop`에 병합한 결과만 릴리스 후보로 삼는다.

## 2. EC2 및 네트워크 사전 조건

- [ ] Ubuntu LTS, Docker Engine, Docker Compose v2를 설치한다.
- [ ] EC2 보안 그룹 인바운드는 `22`(관리자 IP만), `80`, `443`만 허용한다. `3306`, `6379`, `8000`은 허용하지 않는다.
- [ ] Elastic IP 또는 도메인 DNS A 레코드를 준비한다. TLS 발급 전에는 도메인이 EC2 공인 IP를 가리켜야 한다.
- [ ] SSH 키 권한은 소유자 읽기 전용으로 제한하고, 운영 계정은 최소 권한을 사용한다.
- [ ] EC2 디스크 여유 공간, MySQL 볼륨 백업 위치, CloudWatch 또는 로그 수집 방식을 확인한다.

## 3. 비밀값·모델 준비

```bash
mkdir -p ~/ah05-release
cd ~/ah05-release
cp envs/example.prod.env .env
chmod 600 .env
```

- [ ] `.env`의 `SECRET_KEY`, DB 비밀번호 두 종류, AWS 자격증명을 서로 다른 충분히 긴 값으로 교체한다.
- [ ] `ENV=prod`, `DEMO_MODE=false`, `DB_GENERATE_SCHEMAS=false`를 유지한다.
- [ ] `MODEL_URI`는 승인된 모델만 가리키게 한다. 로컬 모델은 EC2의 Git 비추적 `models/`에 두고 `/app/storage/models/...` 경로를 사용한다.
- [ ] S3 모델이면 최소 권한의 읽기 전용 IAM 자격증명 또는 인스턴스 역할을 사용한다. 모델 파일·원본 의료데이터는 저장소에 올리지 않는다.
- [ ] `PREDICTION_MODEL_VERSION`, `PREDICTION_FEATURE_SCHEMA_VERSION`, `PREDICTION_THRESHOLD_VERSION`을 실제 승인 값으로 채운다.

## 4. 이미지 빌드·푸시

로컬에서 레지스트리에 먼저 안전하게 로그인한 뒤 실행한다. 비밀번호나 PAT를 명령행 인자로 넘기지 않는다.

```bash
docker login
export DOCKER_USER=your-dockerhub-user
export DOCKER_REPOSITORY=ah-05-02
./scripts/build-release-images.sh vX.Y.Z vX.Y.Z
```

## 5. 최초 HTTP 배포와 TLS 발급

```bash
./scripts/prepare-ec2-release.sh http .env
docker compose --env-file .env -f infra/docker/docker-compose.prod.yml run --rm --no-deps \
  certbot certonly --webroot -w /var/www/certbot -d "$SERVER_NAME" \
  --email "$CERTBOT_EMAIL" --agree-tos --no-eff-email
./scripts/prepare-ec2-release.sh https .env
docker compose --env-file .env -f infra/docker/docker-compose.prod.yml --profile tls up -d certbot
```

HTTP 상태로는 인증서 발급 확인에만 사용한다. 실제 공개 전에는 반드시 HTTPS 상태로 전환한다. Compose는 MySQL·Redis·FastAPI·AI Worker를 내부 네트워크에만 두며, EC2에 공개되는 포트는 Nginx의 `80/443`뿐이다.

## 6. 배포 후 확인

```bash
docker compose --env-file .env -f infra/docker/docker-compose.prod.yml ps
curl -fsS http://127.0.0.1/health
curl -fsS https://$SERVER_NAME/api/v1/ready
docker compose --env-file .env -f infra/docker/docker-compose.prod.yml logs --tail=100 fastapi ai-worker nginx
```

- [ ] `fastapi`, `mysql`, `redis`, `ai-worker`, `nginx` 상태가 정상이다.
- [ ] 외부에서 `https://도메인/health`와 `https://도메인/api/v1/ready`가 정상 응답한다.
- [ ] 회원가입 → 동의 → 적합성 → 건강정보 입력 → 예측 작업 생성/조회 → 챌린지 기록 흐름을 테스트 계정으로 확인한다.
- [ ] 기진단자 차단, 의료 안내 문구, RAG 출처 표기, 실패 작업 오류 응답을 확인한다.
- [ ] DB·Redis·FastAPI 포트가 외부에서 열리지 않았는지 보안 그룹과 `docker compose ps`를 함께 확인한다.

## 7. 장애·롤백

1. 배포 전 MySQL 논리 백업과 현재 이미지 태그를 기록한다.
2. 장애 발생 시 `.env`의 `APP_VERSION`, `AI_WORKER_VERSION`을 직전 검증 태그로 되돌린다.
3. `./scripts/prepare-ec2-release.sh https .env`로 이전 이미지를 다시 기동한다.
4. 스키마가 되돌릴 수 없는 변경이라면 DB 복구 계획을 먼저 승인받는다. 데이터 삭제나 임의의 다운그레이드 마이그레이션은 실행하지 않는다.
