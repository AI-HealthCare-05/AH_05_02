FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 1. uv 설치 (공식 이미지에서 복사해오는 가장 깔끔한 방법)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 2. 의존성 패키지 관리 파일을 컨테이너 내부에 복사합니다.
COPY pyproject.toml uv.lock ./

# 3. pyproject.toml에 명시된 의존성 패키지 중에서 'app' 그룹만 설치합니다.
ARG ML_RESEARCH_RUNTIME=false
RUN if [ "$ML_RESEARCH_RUNTIME" = "true" ]; then \
      uv sync --group app --group modeling --no-dev --frozen; \
    else uv sync --group app --no-dev --frozen; fi

# 4. 로컬 소스 코드를 컨테이너 내부로 복사합니다.
COPY ./app ./app
COPY ./src/frontend ./src/frontend
COPY ./src/rag ./src/rag
COPY ./src/ml ./src/ml
COPY ./models/registry ./models/registry

# 5. 해당 이미지를 활용하여 도커컨테이너 실행시 실행되는 명령어입니다.
# FastAPI를 uvicorn을 활용하여 비동기 환경으로 서버를 실행합니다.
# --no-sync 옵션은 uv run시 uv.lock파일과 환경에 설치된 패키지들을 비교하여 없는 패키지를 설치하기 때문에
# 불필요한 의존성을 설치하지 않기 위해 사용합니다.
CMD ["sh", "app/start-fastapi.sh", "--workers", "3"]
