from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from tortoise import connections

from app.apis.v1 import v1_routers
from app.core.db.databases import initialize_tortoise
from app.core.redis import close_redis, redis_client


@asynccontextmanager
async def lifespan(_: FastAPI):
    await redis_client.ping()
    yield
    await close_redis()


app = FastAPI(
    default_response_class=ORJSONResponse,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
initialize_tortoise(app)

app.include_router(v1_routers)

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "src" / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health", tags=["Health"])
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
async def health() -> dict[str, str]:
    await redis_client.ping()
    await connections.get("default").execute_query("SELECT 1")
    return {"status": "ok", "database": "ok", "redis": "ok"}


@app.get("/api/v1/ready", tags=["Health"])
async def ready() -> dict[str, object]:
    await redis_client.ping()
    await connections.get("default").execute_query("SELECT 1")
    from app.prediction.contracts import ACTIVE_MODEL

    return {
        "status": "ready",
        "dependencies": {"database": "ready", "redis": "ready", "prediction_provider": "configured"},
        "active_model": {
            "model_key": ACTIVE_MODEL.model_key,
            "version": ACTIVE_MODEL.version,
            "promotion_status": ACTIVE_MODEL.promotion_status,
        },
    }
