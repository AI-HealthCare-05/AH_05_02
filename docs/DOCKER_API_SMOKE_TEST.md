# Docker 로컬 API 연결 및 스모크 테스트

이 문서는 Docker에서 FastAPI를 실행하고 건강정보 예측 API가 정상적으로
호출되는지 확인하는 절차를 설명한다.

현재 예측 API는 Redis·DB를 사용하지 않는 동기식 임시 연동이다.

## 1. 준비

Docker Desktop을 실행하고 Docker Engine이 준비될 때까지 기다린다.

프로젝트 폴더로 이동한다.

```bash
cd /Users/bitsaem/Desktop/chronic-disease-lifestyle-challenge
```

`.env`가 없다면 예시 파일로 생성한다.

```bash
cp .env.example .env
```

실제 API 키나 비밀번호가 포함된 `.env`는 Git에 커밋하지 않는다.

Docker 연결 상태를 확인한다.

```bash
docker version
```

`Client`와 `Server` 정보가 모두 출력되면 정상이다.

## 2. 이미지 빌드 및 컨테이너 실행

```bash
docker compose up --build -d
```

실행 상태를 확인한다.

```bash
docker compose ps
```

`api` 서비스의 상태가 `Up`이고 다음 포트 연결이 표시되어야 한다.

```text
0.0.0.0:8000->8000/tcp
```

## 3. Health API 확인

```bash
curl http://localhost:8000/health
```

정상 응답:

```json
{"status":"ok"}
```

## 4. Swagger 확인

브라우저에서 다음 주소를 연다.

- <http://localhost/api/docs>

Docker는 호스트의 80번 포트와 8000번 포트를 모두 API 컨테이너에 연결한다.
Swagger 경로는 `/api/docs`이며 API 엔드포인트의 기본 경로는 `/api/v1`이다.
따라서 <http://localhost:8000/api/docs>로도 같은 화면을 열 수 있다.

## 5. 예측 API 확인

Swagger에서 `POST /api/v1/predictions/preview`를 선택하고 `Try it out`을
누른 뒤 다음 요청을 입력한다.

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

터미널에서는 다음과 같이 호출할 수 있다.

```bash
curl -X POST http://localhost:8000/api/v1/predictions/preview \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

## 6. 성공 판정 기준

- HTTP 상태 코드가 `200`이다.
- `condition`이 `diabetes`다.
- `model_type`이 `future_incidence`다.
- `risk_category`와 `risk_category_label`이 반환된다.
- `predicted_class`가 `0` 또는 `1`이다.
- `is_temporary`가 `true`다.
- 모델·타깃·입력·전처리·보정 버전이 포함된다.
- 진단·처방을 대신하지 않는다는 안전 문구가 포함된다.
- `risk_score` 또는 `score`와 같은 원시 모델 점수가 노출되지 않는다.

현재 `temporary-integration-v1` 결과와 위험 범주는 기술 연동 확인용이다.
실제 모델 함수와 최종 임계값이 확정된 결과가 아니다.

## 7. 로그 확인

```bash
docker compose logs api
```

다음을 확인한다.

- 애플리케이션 시작 오류가 없다.
- 요청이 정상 상태 코드로 처리된다.
- 사용자 건강정보 원문이나 개인정보가 로그에 출력되지 않는다.

실시간 로그를 확인하려면 다음 명령을 사용한다.

```bash
docker compose logs -f api
```

종료할 때는 `Ctrl+C`를 누른다.

## 8. 컨테이너 종료

```bash
docker compose down
```

이미지를 다시 빌드해야 하는 코드 변경이 있다면 다음에 다시 실행한다.

```bash
docker compose up --build -d
```

## 9. 문제 해결

### Docker API 권한 오류

```text
permission denied while trying to connect to the docker API
```

Docker Desktop이 완전히 실행됐는지 확인한 후 종료·재실행하고
`docker version`을 다시 확인한다.

### `.env` 파일 없음

```text
env file .../.env not found
```

```bash
cp .env.example .env
```

### API 컨테이너가 종료됨

```bash
docker compose ps
docker compose logs api
```

로그에서 Python import 오류, 포트 충돌 또는 환경변수 오류를 확인한다.

### 8000번 포트 충돌

8000번 포트를 사용 중인 프로세스나 다른 컨테이너를 종료한 후 다시 실행한다.

```bash
docker compose down
docker compose up --build -d
```
