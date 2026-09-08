from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.apis.responses import envelope
from app.dependencies.security import get_request_user
from app.models.users import User
from app.services.reports import VALID_PERIODS, PeriodKey, ReportService, resolve_report_id

reports_router = APIRouter(tags=["Lifestyle reports"])


@reports_router.get("/reports")
async def get_report(
    user: Annotated[User, Depends(get_request_user)],
    period: str = Query(...),
) -> dict[str, object]:
    if period not in VALID_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "INVALID_PERIOD",
                "message": "period는 week, four-week, all 중 하나여야 합니다.",
                "retryable": False,
            },
        )
    return envelope(await ReportService().build_report(user, period))  # type: ignore[arg-type]


@reports_router.get("/reports/{report_id}/cycles")
async def get_report_cycles(
    report_id: str,
    user: Annotated[User, Depends(get_request_user)],
    cursor: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
) -> dict[str, object]:
    period: PeriodKey
    period, _as_of = resolve_report_id(report_id)
    if period != "all":
        # Only the `all` report has a cycle history to page through — a well-formed but
        # wrong-period report_id gets the same non-disclosing 404 as a garbage one.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "REPORT_NOT_FOUND", "message": "리포트를 찾을 수 없습니다.", "retryable": False},
        )
    return envelope(await ReportService().cycles_page(user, cursor, limit))
