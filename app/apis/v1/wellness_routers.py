from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.apis.responses import envelope
from app.dependencies.security import get_request_user
from app.dtos.wellness import (
    FoodAnalysisConfirmRequest,
    FoodAnalysisRequest,
    NotificationPreferenceRequest,
    OcrDraftRequest,
    RagQuestionRequest,
    WearableConnectionRequest,
    WearableImportRequest,
)
from app.models.users import User
from app.services.engagement import EngagementService
from app.services.wellness import WellnessService
from src.rag.engine import answer_with_sources

wellness_router = APIRouter(tags=["Wellness extensions"])


def _pdf_text(value: str) -> str:
    return "FEFF" + value.encode("utf-16-be").hex().upper()


def build_korean_pdf(lines: list[str]) -> bytes:
    commands = ["BT", "/F1 16 Tf", "50 800 Td"]
    for index, line in enumerate(lines):
        if index:
            commands.extend(["0 -28 Td", "/F1 10 Tf"])
        commands.append(f"<{_pdf_text(line)}> Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type0 /BaseFont /HYSMyeongJo-Medium /Encoding /UniKS-UCS2-H /DescendantFonts [6 0 R] >>",
        b"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /HYSMyeongJo-Medium /CIDSystemInfo << /Registry (Adobe) /Ordering (Korea1) /Supplement 2 >> >>",
    ]
    result = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(result))
        result.extend(f"{number} 0 obj\n".encode())
        result.extend(obj)
        result.extend(b"\nendobj\n")
    xref = len(result)
    result.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    result.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        result.extend(f"{offset:010d} 00000 n \n".encode())
    result.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(result)


@wellness_router.post("/wearables/connections", status_code=status.HTTP_201_CREATED)
async def connect_wearable(request: WearableConnectionRequest, user: Annotated[User, Depends(get_request_user)]):
    return envelope(await WellnessService().connect_wearable(user, request))


@wellness_router.get("/wearables/connections")
async def wearable_connections(user: Annotated[User, Depends(get_request_user)]):
    return envelope(await WellnessService().wearable_connections(user))


@wellness_router.post("/wearables/daily-summaries/import")
async def import_wearable(request: WearableImportRequest, user: Annotated[User, Depends(get_request_user)]):
    return envelope(await WellnessService().import_wearable(user, request))


@wellness_router.get("/wearables/daily-summaries")
async def wearable_summaries(
    user: Annotated[User, Depends(get_request_user)],
    start_date: date | None = None,
    end_date: date | None = None,
):
    end = end_date or date.today()
    start = start_date or end - timedelta(days=6)
    return envelope(await WellnessService().wearable_summaries(user, start, end))


@wellness_router.post("/health-education/questions")
async def ask_health_education(request: RagQuestionRequest, user: Annotated[User, Depends(get_request_user)]):
    _ = user
    result = answer_with_sources(request.question)
    result["medical_notice"] = "일반 건강교육 정보이며 개인 진단·처방을 대신하지 않습니다."
    return envelope(result)


@wellness_router.post("/food-analyses", status_code=status.HTTP_201_CREATED)
async def analyze_food(request: FoodAnalysisRequest, user: Annotated[User, Depends(get_request_user)]):
    return envelope(await WellnessService().food_analysis(user, request))


@wellness_router.patch("/food-analyses/{analysis_id}/confirm")
async def confirm_food(
    analysis_id: int, request: FoodAnalysisConfirmRequest, user: Annotated[User, Depends(get_request_user)]
):
    return envelope(await WellnessService().confirm_food(user, analysis_id, request))


@wellness_router.post("/ocr-drafts", status_code=status.HTTP_201_CREATED)
async def create_ocr_draft(request: OcrDraftRequest, user: Annotated[User, Depends(get_request_user)]):
    return envelope(await WellnessService().ocr_draft(user, request))


@wellness_router.post("/ocr-drafts/{draft_id}/confirm")
async def confirm_ocr_draft(draft_id: int, user: Annotated[User, Depends(get_request_user)]):
    return envelope(await WellnessService().confirm_ocr(user, draft_id))


@wellness_router.get("/notification-preferences")
async def get_notification_preferences(user: Annotated[User, Depends(get_request_user)]):
    return envelope(await WellnessService().notification_preferences(user))


@wellness_router.put("/notification-preferences")
async def update_notification_preferences(
    request: NotificationPreferenceRequest, user: Annotated[User, Depends(get_request_user)]
):
    return envelope(await WellnessService().update_notification_preferences(user, request))


@wellness_router.get("/notifications")
async def notifications(user: Annotated[User, Depends(get_request_user)]):
    return envelope(await WellnessService().notifications(user))


@wellness_router.get("/weekly-reports/current/pdf")
async def weekly_report_pdf(user: Annotated[User, Depends(get_request_user)]) -> Response:
    report = await EngagementService().weekly_report(user)
    lines = [
        "간당간당 주간 건강 리포트",
        f"상태: {report.get('status', '-')}",
        f"기록 요약: {report.get('record_summary', report.get('message', '기록 없음'))}",
        "주의: 생활습관 기록은 질병 진단, 치료 효과 또는 위험 감소를 의미하지 않습니다.",
    ]
    return Response(
        content=build_korean_pdf(lines),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="gandang-weekly-report.pdf"'},
    )
