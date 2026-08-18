from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
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


@app.get("/api/health", tags=["Health"])
async def health() -> dict[str, str]:
    await redis_client.ping()
    await connections.get("default").execute_query("SELECT 1")
    return {"status": "ok", "database": "ok", "redis": "ok"}
