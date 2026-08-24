from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeDocument:
    document_id: str
    title: str
    url: str
    text: str
    keywords: tuple[str, ...]


APPROVED_DOCUMENTS = (
    KnowledgeDocument(
        "kdca-diabetes",
        "질병관리청 국가건강정보포털 - 당뇨병",
        "https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5292",
        "당뇨병 예방과 관리를 위해 규칙적인 신체활동, 균형 있는 식사, 적정 체중 유지가 중요합니다.",
        ("당뇨", "혈당", "예방", "생활습관", "식사"),
    ),
    KnowledgeDocument(
        "who-activity",
        "WHO Guidelines on physical activity and sedentary behaviour",
        "https://www.who.int/publications/i/item/9789240015128",
        "성인은 건강 상태와 능력에 맞는 신체활동을 하고, 앉아 있는 시간을 줄이는 것이 권장됩니다.",
        ("운동", "걷기", "활동", "앉기", "신체활동"),
    ),
    KnowledgeDocument(
        "cdc-prevent-t2",
        "CDC PreventT2 Curriculum",
        "https://www.cdc.gov/diabetes-prevention/php/lifestyle-change-resources/t2-curriculum.html",
        "작고 구체적인 목표를 기록하고 실패 원인을 살펴 목표를 조정하는 방식은 생활습관 실천에 도움이 됩니다.",
        ("챌린지", "목표", "기록", "실패", "습관"),
    ),
    KnowledgeDocument(
        "kdca-hypertension",
        "질병관리청 국가건강정보포털 - 고혈압",
        "https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5300",
        "혈압은 올바른 방법으로 반복 측정하고, 높은 수치가 확인되면 의료진과 상담해야 합니다.",
        ("혈압", "고혈압", "측정", "상담"),
    ),
)

MEDICATION_PATTERN = re.compile(
    r"(약|복용|용량|처방).*(시작|중단|끊|늘|줄|변경)|(시작|중단|끊|늘|줄|변경).*(약|복용|용량|처방)"
)


def answer_with_sources(question: str) -> dict[str, object]:
    normalized = question.strip().casefold()
    if MEDICATION_PATTERN.search(normalized):
        return {
            "answer": "약의 시작·중단·용량 변경은 이 서비스가 안내할 수 없습니다. 처방한 의료진이나 약사와 상의해 주세요.",
            "answer_status": "medical_safety_refusal",
            "citations": [],
            "retrieval_method": "approved_document_keyword_v1",
        }
    scored = []
    for document in APPROVED_DOCUMENTS:
        score = sum(1 for keyword in document.keywords if keyword.casefold() in normalized)
        if score:
            scored.append((score, document))
    scored.sort(key=lambda item: (-item[0], item[1].document_id))
    selected = [item[1] for item in scored[:2]]
    if not selected:
        return {
            "answer": "승인된 자료에서 질문과 충분히 가까운 근거를 찾지 못했습니다. 질문을 운동·식사·혈압·생활습관처럼 구체적으로 적어 주세요.",
            "answer_status": "insufficient_evidence",
            "citations": [],
            "retrieval_method": "approved_document_keyword_v1",
        }
    return {
        "answer": " ".join(document.text for document in selected),
        "answer_status": "grounded",
        "citations": [
            {"document_id": document.document_id, "title": document.title, "url": document.url} for document in selected
        ],
        "retrieval_method": "approved_document_keyword_v1",
    }
