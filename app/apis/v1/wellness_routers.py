from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from typing import Annotated
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, Response, status
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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

PDF_FONT = "NanumGothic"
PDF_FONT_PATH = Path(__file__).resolve().parents[2] / "assets" / "fonts" / "NanumGothic-Regular.ttf"
RISK_LABELS = {"low": "낮음", "caution": "주의", "high": "높음"}
WEEKDAY_LABELS = ("월", "화", "수", "목", "금", "토", "일")


def _register_pdf_font() -> None:
    if PDF_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(PDF_FONT, PDF_FONT_PATH))


def _report_date(value: object) -> str:
    if isinstance(value, date):
        return value.strftime("%Y.%m.%d")
    if isinstance(value, str):
        try:
            return date.fromisoformat(value).strftime("%Y.%m.%d")
        except ValueError:
            return value
    return "-"


def _report_percent(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "0%"
    return f"{int(number)}%" if number.is_integer() else f"{number:.1f}%"


def build_weekly_report_pdf(  # noqa: C901
    report: dict[str, object], *, generated_on: date | None = None
) -> bytes:
    """Create a readable A4 report from the same data used by the weekly report screen."""
    _register_pdf_font()
    generated_on = generated_on or date.today()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="주간 건강 리포트",
        author="간당간당",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName=PDF_FONT,
        fontSize=24,
        leading=30,
        textColor=colors.HexColor("#17223B"),
        alignment=0,
        spaceAfter=3 * mm,
    )
    subtitle = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName=PDF_FONT,
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#68726E"),
        spaceAfter=1.5 * mm,
    )
    section = ParagraphStyle(
        "ReportSection",
        parent=styles["Heading2"],
        fontName=PDF_FONT,
        fontSize=14,
        leading=24,
        textColor=colors.HexColor("#17223B"),
        spaceBefore=7 * mm,
        spaceAfter=4 * mm,
    )
    body = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontName=PDF_FONT,
        fontSize=9.5,
        leading=15,
        textColor=colors.HexColor("#23314C"),
    )
    small = ParagraphStyle("ReportSmall", parent=body, fontSize=8.2, leading=12, textColor=colors.HexColor("#68726E"))
    metric_label = ParagraphStyle(
        "MetricLabel", parent=small, alignment=TA_CENTER, textColor=colors.HexColor("#68726E")
    )
    metric_value = ParagraphStyle(
        "MetricValue", parent=body, alignment=TA_CENTER, fontSize=17, leading=22, textColor=colors.HexColor("#23764B")
    )

    def paragraph(value: object, style: ParagraphStyle = body) -> Paragraph:
        return Paragraph(escape(str(value)), style)

    def footer(canvas, doc) -> None:  # type: ignore[no-untyped-def]
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#DCE4E0"))
        canvas.line(20 * mm, 13 * mm, A4[0] - 20 * mm, 13 * mm)
        canvas.setFont(PDF_FONT, 7.5)
        canvas.setFillColor(colors.HexColor("#7A837F"))
        canvas.drawCentredString(A4[0] / 2, 8.5 * mm, "간당간당 · 진단·처방이 아닌 위험 선별과 건강교육 서비스")
        canvas.drawRightString(A4[0] - 20 * mm, 8.5 * mm, str(doc.page))
        canvas.restoreState()

    story: list[object] = [
        Paragraph("주간 건강 리포트", title),
        Paragraph("간당간당 · 생활습관 챌린지 기록", subtitle),
    ]
    period = report.get("period") if isinstance(report.get("period"), dict) else {}
    cycle = report.get("cycle") if isinstance(report.get("cycle"), dict) else {}
    if period:
        period_text = f"기간: {_report_date(period.get('start_date'))} ~ {_report_date(period.get('end_date'))}"
        if cycle:
            period_text += f" ({cycle.get('cycle_number', '-')}회차 · {cycle.get('week_number', '-')}주차)"
        period_text += f"  |  생성일: {generated_on.strftime('%Y.%m.%d')}"
    else:
        period_text = f"생성일: {generated_on.strftime('%Y.%m.%d')}"
    story.extend(
        [
            Paragraph(period_text, subtitle),
            Spacer(1, 2 * mm),
            Table(
                [[""]],
                colWidths=[document.width],
                rowHeights=[0.4],
                style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#DCE4E0"))]),
            ),
        ]
    )

    if report.get("status") != "ready":
        story.extend(
            [
                Paragraph("이번 주 기록", section),
                Table(
                    [
                        [paragraph("아직 이번 주 기록이 없어요", body)],
                        [paragraph(report.get("message", "챌린지를 시작하고 오늘의 실천을 기록해 주세요."), small)],
                    ],
                    colWidths=[document.width],
                    style=TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF8F2")),
                            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#BCDCC7")),
                            ("LEFTPADDING", (0, 0), (-1, -1), 14),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                            ("TOPPADDING", (0, 0), (-1, -1), 10),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                        ]
                    ),
                ),
            ]
        )
    else:
        completion = report.get("completion") if isinstance(report.get("completion"), dict) else {}
        details = report.get("challenge_details") if isinstance(report.get("challenge_details"), list) else []
        story.extend([Paragraph("핵심 요약", section), Spacer(1, 2 * mm)])
        metrics = Table(
            [
                [
                    paragraph("연속 실천일", metric_label),
                    paragraph("전체 완료율", metric_label),
                    paragraph("이번 주 총 실천", metric_label),
                ],
                [
                    paragraph(f"{completion.get('streak_days', 0)}일", metric_value),
                    paragraph(_report_percent(completion.get("rate", 0)), metric_value),
                    paragraph(f"{completion.get('completed', 0)}회", metric_value),
                ],
            ],
            colWidths=[document.width / 3] * 3,
            rowHeights=[11 * mm, 17 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF8F2")),
                    ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#BCDCC7")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            ),
        )
        story.append(metrics)

        story.extend([Paragraph("챌린지별 실천 기록", section), Spacer(1, 2 * mm)])
        days: list[dict[str, object]] = []
        if details and isinstance(details[0], dict) and isinstance(details[0].get("daily_records"), list):
            days = details[0]["daily_records"]
        day_headers = []
        for entry in days:
            raw_date = entry.get("date")
            parsed_date = raw_date if isinstance(raw_date, date) else date.fromisoformat(str(raw_date))
            day_headers.append(WEEKDAY_LABELS[parsed_date.weekday()])
        table_data: list[list[object]] = [
            [paragraph("챌린지", small), *[paragraph(label, small) for label in day_headers], paragraph("합계", small)]
        ]
        for detail in details:
            if not isinstance(detail, dict):
                continue
            marks = []
            for record in detail.get("daily_records", []):
                completed = record.get("is_completed") if isinstance(record, dict) else None
                marks.append("●" if completed is True else "-")
            table_data.append(
                [
                    paragraph(detail.get("title", "챌린지"), body),
                    *[paragraph(mark, body) for mark in marks],
                    paragraph(f"{detail.get('completed', 0)}/{detail.get('planned', len(days))}", body),
                ]
            )
        day_width = 10 * mm if days else 0
        first_width = document.width - (day_width * len(days)) - 18 * mm
        challenge_table = Table(
            table_data,
            colWidths=[first_width, *([day_width] * len(days)), 18 * mm],
            repeatRows=1,
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F1EB")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D7D4CB")),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TEXTCOLOR", (1, 1), (-2, -1), colors.HexColor("#23764B")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            ),
        )
        story.append(challenge_table)

        barriers = report.get("barrier_details") if isinstance(report.get("barrier_details"), list) else []
        barrier_lines = []
        for item in barriers[:5]:
            if not isinstance(item, dict):
                continue
            memo = f" · {item['note']}" if item.get("note") else ""
            barrier_lines.append(
                paragraph(
                    f"· {_report_date(item.get('date'))} {item.get('challenge_title', '선택한 챌린지')} - {item.get('reason_label', '기타')}{memo}",
                    body,
                )
            )
        if not barrier_lines:
            barrier_lines = [paragraph("이번 주에 기록된 어려움 메모가 없습니다.", small)]
        story.extend([Paragraph("실천하지 못한 이유 메모", section), Spacer(1, 1.5 * mm)])
        story.extend(barrier_lines)

        adjustment = report.get("next_adjustment") if isinstance(report.get("next_adjustment"), dict) else {}
        story.extend([Paragraph("다음 주 실천 제안", section), Spacer(1, 1.5 * mm)])
        story.append(
            Table(
                [[paragraph(adjustment.get("message", "현재 목표를 이어가세요."), body)]],
                colWidths=[document.width],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F8F6")),
                        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#DCE4E0")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 12),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                        ("TOPPADDING", (0, 0), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ]
                ),
            )
        )

        risk_label = RISK_LABELS.get(str(report.get("recent_risk_category")), "표시 가능한 승인 결과 없음")
        story.extend([Paragraph("최근 위험 신호", section), Spacer(1, 1.5 * mm)])
        story.append(
            Table(
                [[paragraph(risk_label, ParagraphStyle("RiskValue", parent=body, fontSize=15, leading=20))]],
                colWidths=[document.width],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F1EB")),
                        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D7D4CB")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 12),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                        ("TOPPADDING", (0, 0), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ]
                ),
            )
        )

    disclaimer = report.get("disclaimer", "생활습관 기록은 진단이나 치료 효과를 의미하지 않습니다.")
    story.append(Spacer(1, 4 * mm))
    story.append(
        KeepTogether(
            [
                Table(
                    [[paragraph(f"안내 · {disclaimer} 건강 상태에 대한 정확한 판단은 의료진과 상담하세요.", small)]],
                    colWidths=[document.width],
                    style=TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF6E5")),
                            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E8C680")),
                            ("LEFTPADDING", (0, 0), (-1, -1), 12),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                            ("TOPPADDING", (0, 0), (-1, -1), 9),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                        ]
                    ),
                )
            ]
        )
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


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
    return Response(
        content=build_weekly_report_pdf(report),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="gandang-weekly-report.pdf"'},
    )
