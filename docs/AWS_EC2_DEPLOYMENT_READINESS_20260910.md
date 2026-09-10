# AWS EC2 MVP 배포 준비 (2026-09-10)

## 권장 구조

첫 베타 시연은 단일 EC2에서 Nginx, FastAPI, AI Worker, Redis, MySQL을 Docker Compose로 실행한다. 외부에는 80/443만 공개하고 MySQL·Redis는 로컬 인터페이스와 Docker 내부 네트워크에서만 접근한다.

운영 규모가 커지면 RDS, ElastiCache, ECR/ECS로 분리한다. 현재 단계에서 곧바로 분리하면 비용과 운영 복잡도가 커지므로 베타 검증 이후 결정한다.

## 이번에 준비한 항목

- 루트·정적 파일·API를 모두 FastAPI로 전달하는 Nginx 설정
- Redis·MySQL의 외부 공개 방지 유지
- 웨어러블, 건강검진 텍스트 추출, 퀴즈, 챌린지 카탈로그를 FastAPI 이미지에 포함
- 오늘이와 내일이가 같은 AI Worker 이미지와 동일한 모델 마운트를 사용하도록 통일
- 모델 파일은 Git과 Docker 이미지에서 제외하고 EC2의 `/opt/ah05/models/artifacts`를 읽기 전용으로 마운트
- 배포 전 AWS 로그인, 환경값, 모델 파일, Docker, Git 상태를 검사하는 Windows 스크립트

## 실행 전 필수 준비

1. AWS CLI 로그인과 기본 리전을 `ap-northeast-2`로 설정한다.
2. Docker가 실행되는 개발 PC 또는 EC2 환경을 준비한다.
3. `envs/.prod.env`를 생성하고 실제 값은 Git에 올리지 않는다.
4. `MODEL_ARTIFACTS_PATH=/opt/ah05/models/artifacts`를 설정한다.
5. 오늘이·내일이 모델 파일과 manifest를 EC2의 동일한 상대 경로에 배치한다.
6. 공개 전 모델의 승인 상태와 결과 표시 정책을 확인한다. 후보 모델을 승인 모델처럼 표시하지 않는다.

## AWS 리소스 생성 전 결정

- EC2 인스턴스 유형과 운영 시간: 모델 메모리를 고려해 8GB 이상부터 부하 검증
- 고정 IP 또는 도메인 사용 여부
- `ENV=prod`에서는 로그인 갱신 쿠키가 HTTPS 전용이므로 안정적인 베타 로그인에는 도메인과 TLS가 필요
- 22번 포트 허용 IP: 전체 공개 금지, 관리자 IP만 허용
- S3 모델 저장소 사용 여부와 EC2 IAM Role 권한
- 베타 데이터 보관 기간과 삭제 책임자

## 사전 점검

```powershell
powershell -ExecutionPolicy Bypass -File scripts/aws-deploy-preflight.ps1
```

점검 결과에는 비밀값의 실제 내용이 출력되지 않는다.

## 배포 후 Smoke Test

- `/health`: 프로세스 생존 확인
- `/api/v1/health`: DB·Redis 연결 확인
- `/api/v1/ready`: 모델 설정과 준비 상태 확인
- 회원가입 → 건강정보 입력 → 오늘이·내일이 요청 → 결과 → 챌린지 → 리포트
- 동의 철회 후 신규 건강정보·예측·챌린지 차단
- AI Worker 중단·시간초과·재시도 안내
- 새로고침과 다른 브라우저에서 당근의 숲 서버 상태 유지

## 아직 실행하지 않은 항목

- 과금되는 EC2·EBS·Elastic IP·S3 생성
- 보안그룹 변경
- 운영 비밀값 입력
- 모델 아티팩트 업로드
- 실제 도메인·TLS 발급

위 항목은 AWS 계정·리전·예산·접근 IP를 확인한 뒤 실행한다.
