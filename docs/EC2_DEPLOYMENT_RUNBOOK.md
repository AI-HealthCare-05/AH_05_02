# EC2 Docker 릴리스 운영 절차

## 목적과 적용 범위

이 문서는 Docker 이미지와 Docker Compose로 EC2에 배포하는 운영 절차다. 현재 서비스는 **건강교육·위험 선별용 데모**이며, 모델 검증과 의료 안전 승인이 완료되기 전 개인의 진단·처방 서비스로 운영하지 않는다.

참고한 배포 가이드의 핵심 순서는 `이미지 빌드·레지스트리 푸시 → EC2 환경변수·운영 설정 준비 → Compose 기동 → 헬스체크 → 도메인·HTTPS 적용`이다. 이 저장소에서는 해당 흐름을 `infra/docker/docker-compose.ec2.yml`과 `scripts/deploy_ec2_release.sh`로 재현한다.

## 사전 조건

- 배포 대상 변경은 `develop`에 병합되고 리뷰·CI가 통과된 커밋이어야 한다.
- Docker Hub 등 레지스트리에 `DOCKER_USER/DOCKER_REPOSITORY`가 준비되어 있고, 배포 담당자는 로컬에서 `docker login`을 마친 상태여야 한다.
- EC2의 `~/project/.env`에는 강한 무작위 `SECRET_KEY`, DB 비밀번호, 필요한 외부 API 키만 저장한다. `.env`는 전송·커밋·PR 첨부 금지다.
- 모델 바이너리와 원본 의료 데이터는 Git·이미지에 넣지 않는다. 검증된 모델 아티팩트는 EC2 `~/project/models`에 별도 반입하고 SHA-256을 확인한다.
- 보안 그룹은 공개 HTTP/HTTPS(80/443)만 필요한 범위로 허용한다. MySQL(3306), Redis(6379), FastAPI 내부 포트(8000)는 인터넷에 열지 않는다.

## 최초 EC2 준비

1. EC2에 Docker Engine과 Compose Plugin을 설치한다.
2. `~/project`에 배포 설정과 서버 전용 `.env`를 만든다.
3. `.env.example`을 출발점으로 사용하되 실제 비밀값은 새로 생성한다. `SERVER_NAME`에는 현재 EC2 공인 IP 또는 준비된 도메인을 설정한다.
4. Docker 레지스트리에서 private image를 쓴다면 EC2에서도 `docker login`을 수행한다.
5. `models` 디렉터리에 승인된 모델·매니페스트만 별도로 준비한다. 아티팩트가 없거나 `PREDICTION_PROMOTION_STATUS=candidate_only`이면 개발/데모 제공자로만 실행한다.

## 릴리스 배포

로컬에서 다음 환경변수를 설정한 후 실행한다. 비밀번호·토큰을 명령 인수로 넘기지 않는다.

```bash
docker login
export DOCKER_USER="registry-account"
export DOCKER_REPOSITORY="ah-05-02"
export APP_VERSION="v1.0.0"
export AI_WORKER_VERSION="v1.0.0"
export EC2_HOST="EC2-public-ip-or-dns"
export SSH_KEY="$HOME/.ssh/ec2-key.pem"
bash scripts/deploy_ec2_release.sh
```

이 스크립트는 리눅스 AMD64 이미지를 태그로 빌드·푸시하고, 운영 Compose와 Nginx 템플릿만 EC2로 복사한다. 서버의 `.env`, DB 볼륨, 모델 파일은 덮어쓰지 않는다.

## 배포 후 검증

EC2에서 다음을 확인한다.

```bash
cd ~/project
docker compose --env-file .env -f docker-compose.ec2.yml ps
curl --fail http://127.0.0.1/api/health
curl --fail http://127.0.0.1/api/docs
```

브라우저에서는 `/`의 레트로 표지와 `/api/health` 응답을 각각 확인한다. `mysql`, `redis`, `fastapi`, `ai-worker`, `nginx`의 상태가 정상이어야 한다. 모델 호출은 진단이 아닌 위험 선별 문구·안전 차단 동작까지 함께 점검한다.

## 롤백

문제가 발생하면 이전에 검증된 이미지 태그를 `.env`의 `APP_VERSION`, `AI_WORKER_VERSION`에 지정한 뒤 다음을 실행한다.

```bash
cd ~/project
docker compose --env-file .env -f docker-compose.ec2.yml pull
docker compose --env-file .env -f docker-compose.ec2.yml up -d
curl --fail http://127.0.0.1/api/health
```

DB 볼륨과 `.env`를 삭제하거나 재생성하지 않는다. 장애 원인을 로그와 함께 기록한 뒤 새 PR에서 수정한다.

## 도메인과 HTTPS

도메인의 A 레코드가 EC2 공인 IP를 가리킨 뒤에만 Certbot을 적용한다. HTTPS 설정·인증서 발급은 도메인 소유 및 DNS 변경 권한이 필요한 별도 작업이다. 도메인이 없는 현재 단계에서는 HTTP 데모를 유지하고, 의료·개인정보 입력을 실제 운영 데이터로 받지 않는다.
