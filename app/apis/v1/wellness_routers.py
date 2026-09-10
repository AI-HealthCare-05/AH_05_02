from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status

from app.apis.responses import envelope
from app.dependencies.security import get_request_user
from app.dtos.wellness import (
    FoodAnalysisConfirmRequest,
    FoodAnalysisRequest,
    NotificationPreferenceRequest,
    OcrDraftRequest,
    OcrHealthApplyRequest,
    QuizAnswerRequest,
    WearableConnectionRequest,
    WearableHealthCandidateApplyRequest,
    WearableImportRequest,
)
from app.models.users import User
from app.services.engagement import EngagementService
from app.services.wellness import WellnessService
from src.quiz.curriculum import week_number_for_document
from src.quiz.generator import generate_quizzes

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


@wellness_router.post("/wearables/file-previews")
async def preview_wearable_file(
    provider: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    user: Annotated[User, Depends(get_request_user)],
):
    _ = user
    raw = await file.read(20 * 1024 * 1024 + 1)
    await file.close()
    return envelope(WellnessService.preview_wearable_file(provider, raw))


@wellness_router.get("/wearables/daily-summaries")
async def wearable_summaries(
    user: Annotated[User, Depends(get_request_user)],
    start_date: date | None = None,
    end_date: date | None = None,
):
    end = end_date or date.today()
    start = start_date or end - timedelta(days=6)
    return envelope(await WellnessService().wearable_summaries(user, start, end))


@wellness_router.get("/wearables/health-candidates")
async def wearable_health_candidates(
    user: Annotated[User, Depends(get_request_user)],
    start_date: date | None = None,
    end_date: date | None = None,
):
    end = end_date or date.today()
    start = start_date or end - timedelta(days=6)
    return envelope(await WellnessService().wearable_health_candidates(user, start, end))


@wellness_router.patch("/wearables/health-candidates/{checkup_id}")
async def apply_wearable_health_candidates(
    checkup_id: int,
    request: WearableHealthCandidateApplyRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    return envelope(await WellnessService().apply_wearable_health_candidates(user, checkup_id, request))


@wellness_router.get("/health-education/quizzes")
async def list_health_education_quizzes(user: Annotated[User, Depends(get_request_user)]):
    # already_correct: 이 사용자가 이전 회차 등에서 이미 정답을 맞힌 문항 표시(노출 우선순위 조정용).
    # week_number/locked: 프론트가 더 이상 자체 weekByDocument 표를 들고 있지 않도록, 문서가 몇 주차
    # 커리큘럼인지와 지금 그 주차가 열렸는지를 함께 내려준다. 실제 제출 차단은 아래 answers 엔드포인트가 한다.
    engagement = EngagementService()
    correct_ids = await engagement.repo.correct_quiz_ids(user.id)
    current_week = await engagement.current_education_week(user.id)
    items = []
    for quiz in generate_quizzes():
        week_number = week_number_for_document(quiz.document_id)
        locked = current_week is not None and week_number is not None and week_number > current_week
        items.append(
            {
                **quiz.as_public_dict(),
                "already_correct": quiz.quiz_id in correct_ids,
                "week_number": week_number,
                "locked": locked,
            }
        )
    return envelope({"items": items, "current_week_number": current_week})


@wellness_router.post("/health-education/quizzes/{quiz_id}/answers")
async def answer_health_education_quiz(
    quiz_id: str,
    request: QuizAnswerRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    item = next((quiz for quiz in generate_quizzes() if quiz.quiz_id == quiz_id), None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="퀴즈를 찾을 수 없습니다.")
    engagement = EngagementService()
    week_number = week_number_for_document(item.document_id)
    if week_number is not None:
        current_week = await engagement.current_education_week(user.id)
        if current_week is not None and week_number > current_week:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{week_number}주차 문항이에요. {week_number}주차가 되면 풀 수 있어요.",
            )
    submitted = request.answer.strip()
    is_correct = submitted.casefold() == item.answer.strip().casefold()
    await engagement.repo.record_quiz_attempt(
        user_id=user.id,
        quiz_id=item.quiz_id,
        document_id=item.document_id,
        submitted_answer=submitted,
        is_correct=is_correct,
    )
    return envelope(
        {
            "quiz_id": item.quiz_id,
            "is_correct": is_correct,
            "correct_answer": item.answer,
            "explanation": item.explanation,
            "source": {
                "document_id": item.document_id,
                "title": item.source_title,
                "url": item.source_url,
                "checked_at": item.checked_at,
            },
        }
    )


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


@wellness_router.patch("/ocr-drafts/{draft_id}/health-checkups/{checkup_id}")
async def apply_ocr_to_health_checkup(
    draft_id: int,
    checkup_id: int,
    request: OcrHealthApplyRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    return envelope(await WellnessService().apply_ocr_to_health_checkup(user, draft_id, checkup_id, request))


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
    # §3 API 공통 조건(Cache-Control: private, no-store)은 app/main.py의
    # `_no_store_for_sensitive_reports` 미들웨어가 이 응답과 인증 실패(401) 응답에도 일괄 적용한다.
    return Response(
        content=build_korean_pdf(lines),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="gandang-weekly-report.pdf"'},
    )
