from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.backend.api.v1.router import api_router
from src.backend.core.exceptions import PredictionNotAllowedError

app = FastAPI(
    title="만성질환 생활습관 챌린지 웹서비스",
    description="만성질환 위험 선별과 생활습관 챌린지를 제공하는 API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.include_router(api_router, prefix="/api/v1")

# API_SPEC.md v2 SS1 "공통 오류 응답 형식": pydantic error type -> fixed field code.
# Extend this map as new validators/constraints are added.
_FIELD_ERROR_CODES = {
    "greater_than_equal": "OUT_OF_RANGE",
    "less_than_equal": "OUT_OF_RANGE",
    "greater_than": "OUT_OF_RANGE",
    "less_than": "OUT_OF_RANGE",
    "extra_forbidden": "UNSUPPORTED_FIELD",
    "missing": "REQUIRED_FIELD_MISSING",
    "value_error": "INVALID_VALUE",
}


@app.exception_handler(PredictionNotAllowedError)
def handle_prediction_not_allowed(request: Request, exc: PredictionNotAllowedError) -> JSONResponse:
    """SERVICE_SCOPE_AND_SAFETY_COPY.md SS6-2: policy-blocked prediction requests are 403, not 422."""
    return JSONResponse(
        status_code=403,
        content={
            "error": {
                "code": "PREDICTION_NOT_ALLOWED",
                "message": exc.message,
                "trace_id": str(uuid4()),
                "reason_codes": [exc.reason_code],
                "next_action": exc.next_action,
            }
        },
    )


@app.exception_handler(RequestValidationError)
def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """API_SPEC.md v2 SS1: every endpoint's 422 must use the common error envelope.

    FastAPI's default RequestValidationError response ({"detail": [...]}) does
    not match {error: {code, message, trace_id, fields[]}}, so this replaces it.
    """
    fields = []
    for error in exc.errors():
        loc = [str(part) for part in error["loc"] if part != "body"]
        reason = error["msg"]
        if reason.startswith("Value error, "):
            reason = reason[len("Value error, ") :]
        fields.append(
            {
                "field": ".".join(loc) if loc else "body",
                "code": _FIELD_ERROR_CODES.get(error["type"], "INVALID_VALUE"),
                "reason": reason,
            }
        )
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "입력값을 다시 확인해주세요.",
                "trace_id": str(uuid4()),
                "fields": fields,
            }
        },
    )


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
