from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from tortoise import connections

from app.apis.v1 import v1_routers
from app.core import config
from app.core.db.databases import initialize_tortoise
from app.core.redis import close_redis, redis_client


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not config.DEMO_MODE:
        await redis_client.ping()
    yield
    if not config.DEMO_MODE:
        await close_redis()


app = FastAPI(
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
initialize_tortoise(app)

app.include_router(v1_routers)

# report-v1.4-draft §3 API 공통 조건: 민감 응답(리포트류)은 Cache-Control: private, no-store를
# 권장한다. 라우터 안에서 개별적으로 response.headers를 설정하면 200 응답에는 적용되지만, 그
# 라우트가 HTTPException을 던지는 에러 응답(404/422/401 등)은 FastAPI가 별도의 응답 객체를 새로
# 만들어 처리하므로 헤더가 유실된다. 이 미들웨어는 응답이 성공이든 예외에서 나온 것이든 상관없이
# 해당 경로 전부에 헤더를 강제로 붙여서 그 사각지대를 없앤다.
_SENSITIVE_REPORT_PATH_PREFIXES = ("/api/v1/reports", "/api/v1/weekly-reports")


@app.middleware("http")
async def _no_store_for_sensitive_reports(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith(_SENSITIVE_REPORT_PATH_PREFIXES):
        response.headers["Cache-Control"] = "private, no-store"
    return response


FRONTEND_DIR = Path(__file__).resolve().parents[1] / "src" / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/forest", include_in_schema=False)
async def carrot_forest() -> FileResponse:
    response = FileResponse(FRONTEND_DIR / "forest.html")
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


@app.get("/manifest.webmanifest", include_in_schema=False)
async def forest_manifest() -> FileResponse:
    response = FileResponse(
        FRONTEND_DIR / "forest.webmanifest",
        media_type="application/manifest+json",
    )
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/forest-sw.js", include_in_schema=False)
async def forest_service_worker() -> FileResponse:
    response = FileResponse(FRONTEND_DIR / "forest-sw.js", media_type="text/javascript")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Service-Worker-Allowed"] = "/forest"
    return response


@app.get("/health", tags=["Health"])
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
async def health() -> dict[str, str]:
    if not config.DEMO_MODE:
        await redis_client.ping()
    await connections.get("default").execute_query("SELECT 1")
    return {
        "status": "ok",
        "database": "ok",
        "redis": "embedded-demo" if config.DEMO_MODE else "ok",
    }


@app.get("/api/v1/ready", tags=["Health"])
async def ready() -> dict[str, object]:
    if not config.DEMO_MODE:
        await redis_client.ping()
    await connections.get("default").execute_query("SELECT 1")
    from app.prediction.contracts import ACTIVE_MODEL

    return {
        "status": "ready",
        "dependencies": {
            "database": "ready",
            "redis": "embedded-demo" if config.DEMO_MODE else "ready",
            "prediction_provider": "configured",
        },
        "active_model": {
            "model_key": ACTIVE_MODEL.model_key,
            "version": ACTIVE_MODEL.version,
            "promotion_status": ACTIVE_MODEL.promotion_status,
        },
    }
