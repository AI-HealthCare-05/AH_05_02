from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .prototype import router

app = FastAPI(
    title="만성질환 생활습관 챌린지 API",
    description=("만성질환 위험 선별과 건강교육을 위한 프로토타입 API입니다. 결과는 의료 진단이나 처방이 아닙니다."),
    version="0.2.0-prototype",
)
app.include_router(router)

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def prototype_home() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health", tags=["system"])
@app.get("/api/v1/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/ready", tags=["system"])
def readiness_check() -> dict[str, object]:
    return {
        "status": "ready",
        "dependencies": {
            "database": "prototype-memory-store",
            "model_server": "mock-inference-adapter",
        },
    }
