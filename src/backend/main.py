from fastapi import FastAPI

from src.backend.api.v1.router import api_router

app = FastAPI(
    title="만성질환 생활습관 챌린지 웹서비스",
    description="만성질환 위험 선별과 생활습관 챌린지를 제공하는 API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
