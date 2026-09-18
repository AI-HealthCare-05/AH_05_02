import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from tortoise import connections

from app.apis.v1 import v1_routers
from app.core import config
from app.core.db.databases import initialize_tortoise
from app.core.redis import close_redis, redis_client
from app.middleware.challenge_upload_limit import ChallengeUploadLimit


async def _preload_embedded_demo_models() -> None:
    """Load and verify both approved artifacts before accepting demo traffic."""
    from app.prediction.providers import load_standard_model
    from src.ml.inference.diabetes_current_screening import load_current_screening_model

    await asyncio.gather(
        asyncio.to_thread(load_standard_model),
        asyncio.to_thread(
            load_current_screening_model,
            manifest_path=Path(config.CURRENT_SCREENING_MANIFEST_URI),
            model_path=config.CURRENT_SCREENING_MODEL_URI,
        ),
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not config.DEMO_MODE:
        await redis_client.ping()
    if config.DEMO_MODE and config.DEMO_ARTIFACT_INFERENCE_ENABLED:
        await _preload_embedded_demo_models()
    from app.services.challenge_v2_retention import retention_loop

    retention = asyncio.create_task(retention_loop())
    try:
        yield
    finally:
        retention.cancel()
        with suppress(asyncio.CancelledError):
            await retention
    if not config.DEMO_MODE:
        await close_redis()


app = FastAPI(
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
initialize_tortoise(app)
app.add_middleware(ChallengeUploadLimit)

app.include_router(v1_routers)

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


_APP_ENTRY_QUERY_KEYS = frozenset({"intro", "auth", "preview", "resume", "workspace", "invite_token"})
_RETRO_INTRO_URL = "/static/intro-retro.html?v=20260917-server-entry-v1"


@app.get("/", include_in_schema=False)
async def home(request: Request) -> Response:
    """Show the retro introduction before the customer interface.

    Authentication, invitation, preview, and signed-in resume links keep serving the
    application directly.  A server redirect is intentional here: some embedded or
    privacy-restricted browsers disable ``window.location.replace``, which made the
    previous client-only entry guard unreliable.
    """
    if not _APP_ENTRY_QUERY_KEYS.intersection(request.query_params):
        response = RedirectResponse(_RETRO_INTRO_URL, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response

    response = FileResponse(FRONTEND_DIR / "index.html")
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


@app.get("/forest", include_in_schema=False)
async def carrot_forest() -> FileResponse:
    response = FileResponse(FRONTEND_DIR / "forest.html")
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


@app.get("/service", include_in_schema=False)
async def suin_service() -> FileResponse:
    """Namespaced September 7 frontend; shares the forest's host-only session."""
    response = FileResponse(FRONTEND_DIR / "suin" / "index.html")
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
async def ready(response: Response) -> dict[str, object]:
    if not config.DEMO_MODE:
        await redis_client.ping()
    await connections.get("default").execute_query("SELECT 1")
    from app.prediction.contracts import ACTIVE_MODEL, CURRENT_SCREENING_MODEL
    from app.vision.food_vision import food_vision_is_configured

    future_artifact_available = config.PREDICTION_PROVIDER != "artifact" or Path(config.MODEL_URI).is_file()
    current_artifact_path = (
        config.ML_SHARED8_MODEL_URI
        if config.CURRENT_SCREENING_RUNTIME == "shared8-waist"
        else config.CURRENT_SCREENING_MODEL_URI
    )
    current_artifact_available = bool(current_artifact_path) and Path(current_artifact_path).is_file()
    food_vision_ready = config.FOOD_VISION_PROVIDER != "local_kfood" or food_vision_is_configured()
    operational_ready = (
        (not ACTIVE_MODEL.operational_model_activated or future_artifact_available)
        and (not CURRENT_SCREENING_MODEL.operational_model_activated or current_artifact_available)
        and food_vision_ready
    )
    if not operational_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if operational_ready else "not_ready",
        "dependencies": {
            "database": "ready",
            "redis": "embedded-demo" if config.DEMO_MODE else "ready",
            "prediction_provider": config.PREDICTION_PROVIDER,
            "future_artifact_path_available": future_artifact_available,
            "current_artifact_path_available": current_artifact_available,
            "food_vision_ready": food_vision_ready,
            "demo_artifact_inference_enabled": config.DEMO_ARTIFACT_INFERENCE_ENABLED,
            "worker_preload_required_for_release": not (config.DEMO_MODE and config.DEMO_ARTIFACT_INFERENCE_ENABLED),
        },
        "active_model": {
            "model_key": ACTIVE_MODEL.model_key,
            "version": ACTIVE_MODEL.version,
            "promotion_status": ACTIVE_MODEL.promotion_status,
        },
        "current_screening_model": {
            "model_key": CURRENT_SCREENING_MODEL.model_key,
            "version": CURRENT_SCREENING_MODEL.version,
            "runtime": config.CURRENT_SCREENING_RUNTIME,
            "promotion_status": CURRENT_SCREENING_MODEL.promotion_status,
            "operational_model_activated": CURRENT_SCREENING_MODEL.operational_model_activated,
        },
    }
