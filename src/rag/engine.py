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
    # 정보 확인일(YYYY-MM-DD). 근거 문서·링크가 갱신되면 이 값도 함께 갱신한다
    # (docs/frontend/challenge-evidence.md의 "근거 확인일과 버전" 관리 원칙과 동일).
    checked_at: str


APPROVED_DOCUMENTS = (
    KnowledgeDocument(
        "kdca-diabetes",
        "질병관리청 국가건강정보포털 - 당뇨병",
        "https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5292",
        "당뇨병 예방과 관리를 위해 규칙적인 신체활동, 균형 있는 식사, 적정 체중 유지가 중요합니다.",
        ("당뇨", "혈당", "예방", "생활습관", "식사"),
        checked_at="2026-09-09",
    ),
    KnowledgeDocument(
        "kdca-diabetes-exercise",
        "질병관리청 국가건강정보포털 - 당뇨환자의 운동요법",
        "https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=3390",
        "당뇨병 위험이 높은 사람은 중등도 강도의 유산소 운동을 주 150분 이상, 근력 운동을 주 2회 이상 하면 당뇨병 예방에 도움이 됩니다.",
        ("당뇨", "운동", "예방", "유산소", "근력운동", "혈당"),
        checked_at="2026-09-09",
    ),
    KnowledgeDocument(
        "diabetes-or-kr-exercise",
        "대한당뇨병학회 - 당뇨병과 운동",
        "https://www.diabetes.or.kr/general/exercise/exercise_01.php",
        "당뇨병 환자는 일주일에 3일 이상, 숨이 조금 찰 정도의 강도로 하루 30~60분 정도 운동하는 것이 좋습니다. 산책, 조깅, 맨손체조, 자전거 타기 같은 가벼운 전신 운동이 권장됩니다.",
        ("당뇨", "운동", "빈도", "강도", "예방", "혈당"),
        checked_at="2026-09-09",
    ),
    KnowledgeDocument(
        "diabetes-or-kr-exercise-intensity",
        "대한당뇨병학회 - 혈당 낮추는 가장 효과적인 유산소 운동은?",
        "https://www.diabetes.or.kr/bbs/?code=news&mode=view&number=1196",
        "운동 강도는 '약간 힘들다'고 느껴지는 정도(자각인지도 12~14)가 적당하며, 숨이 약간 차고 옆 사람과 대화가 가능한 정도가 좋습니다. 목표 심박수는 최대심박수(220-나이)에 원하는 운동 강도(%)를 곱해서 계산할 수 있습니다.",
        ("당뇨", "운동", "강도", "심박수", "유산소운동", "혈당"),
        checked_at="2026-09-09",
    ),
    KnowledgeDocument(
        "kdca-diabetes-diet",
        "질병관리청 국가건강정보포털 - 당뇨환자의 식이요법",
        "https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=3388",
        "당뇨병 환자는 탄수화물을 전체 에너지의 55~65% 정도로 섭취하면 혈당 개선에 도움이 됩니다. 채소는 즙보다 생채소로, 과일은 주스보다 생과일로 섭취하는 것이 좋으며, 음주는 남자 2잔, 여자 1잔을 넘지 않도록 합니다.",
        ("당뇨", "식이요법", "탄수화물", "식사", "음주", "혈당"),
        checked_at="2026-09-09",
    ),
    KnowledgeDocument(
        "kdca-prediabetes",
        "질병관리청 국가건강정보포털 - 당뇨병전단계, 정상으로 되돌릴 수 있을까요?",
        "https://health.kdca.go.kr/healthinfo/biz/health/ntcnInfo/healthSourc/thtimtCntnts/thtimtCntntsView.do?thtimt_cntnts_sn=41",
        "당뇨병전단계는 매년 약 8%가 당뇨병으로 진행하지만, 체중을 5~7% 이상 줄이고 지방 섭취를 전체 열량의 25% 이하로, 신체활동을 주 150분 이상으로 늘리는 생활습관 교정을 통해 당뇨병으로의 진행을 58%까지 억제할 수 있습니다. 당뇨병전단계인 경우 매년 1회 정도 정기적으로 혈당 검사를 받는 것이 좋습니다.",
        ("당뇨", "전단계", "예방", "위험군", "체중감량", "생활습관"),
        checked_at="2026-09-09",
    ),
    KnowledgeDocument(
        "kdca-diabetes-complications",
        "질병관리청 국가건강정보포털 - 당뇨병 만성합병증",
        "https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=2351",
        "당뇨병의 만성합병증은 망막병증·신장질환·신경병증 같은 미세혈관 합병증과 관상동맥질환·뇌졸중 같은 대혈관 합병증으로 나뉩니다. 2형당뇨병은 진단과 동시에 안과검진을 받아야 하며, 식사는 제때에 반찬은 골고루 양은 알맞게 섭취하고 규칙적으로 운동하며 정기적으로 병원을 방문하는 것이 중요합니다.",
        ("당뇨", "합병증", "검진", "망막", "신장", "신경병증"),
        checked_at="2026-09-09",
    ),
    KnowledgeDocument(
        "samsunghospital-diabetes-management",
        "삼성서울병원 당뇨교육실 - 당뇨병 관리방법",
        "https://www.samsunghospital.com/dept/main/index.do?DP_CODE=DM&MENU_ID=008",
        "당뇨병 관리는 혈당뿐 아니라 혈압, 체중, 콜레스테롤을 함께 관리하는 것이 중요합니다. 당뇨인의 일반적인 혈압조절 목표는 130/80mmHg 미만이며, 콜레스테롤은 적어도 1년에 한 번 이상 검사받아야 합니다. 비만한 당뇨인이 체중감량을 통해 표준체중을 유지하면 혈당뿐 아니라 혈압과 콜레스테롤도 함께 낮아질 수 있습니다.",
        ("당뇨", "혈압", "콜레스테롤", "체중", "관리목표", "합병증"),
        checked_at="2026-09-09",
    ),
    KnowledgeDocument(
        "who-activity",
        "WHO Guidelines on physical activity and sedentary behaviour",
        "https://www.who.int/publications/i/item/9789240015128",
        "성인은 건강 상태와 능력에 맞는 신체활동을 하고, 앉아 있는 시간을 줄이는 것이 권장됩니다.",
        ("운동", "걷기", "활동", "앉기", "신체활동"),
        checked_at="2026-09-09",
    ),
    KnowledgeDocument(
        "cdc-prevent-t2",
        "CDC PreventT2 Curriculum",
        "https://www.cdc.gov/diabetes-prevention/php/lifestyle-change-resources/t2-curriculum.html",
        "작고 구체적인 목표를 기록하고 실패 원인을 살펴 목표를 조정하는 방식은 생활습관 실천에 도움이 됩니다.",
        ("챌린지", "목표", "기록", "실패", "습관"),
        checked_at="2026-09-09",
    ),
    KnowledgeDocument(
        "kdca-hypertension",
        "질병관리청 국가건강정보포털 - 고혈압",
        "https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5300",
        "혈압은 올바른 방법으로 반복 측정하고, 높은 수치가 확인되면 의료진과 상담해야 합니다.",
        ("혈압", "고혈압", "측정", "상담"),
        checked_at="2026-09-09",
    ),
    KnowledgeDocument(
        "kdca-hyperglycemia-emergency",
        "질병관리청 국가건강정보포털 - 고혈당",
        "https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5304",
        "고혈당이 미진단 상태로 의심되면 의료기관에서 확인해야 하며, 의식 변화 등 응급상황이 나타나면 즉시 응급조치가 필요합니다.",
        ("고혈당", "응급", "의식", "저혈당", "쇼크"),
        checked_at="2026-08-19",
    ),
)

EMERGENCY_SYMPTOM_PATTERN = re.compile(
    r"의식(을|이)?\s*(잃|없|흐려|저하)"
    r"|정신(을|이)?\s*(잃|없)"
    r"|숨(을|이)?\s*(못\s*쉬|쉬기\s*힘들|가쁘|막히)"
    r"|호흡\s*곤란"
    r"|가슴\s*(통증|답답|조이)"
    r"|흉통"
    r"|(팔|다리|얼굴)\s*마비|마비.{0,4}(팔|다리|얼굴)|반신\s*마비|편측\s*마비"
    r"|경련|발작"
    r"|말이\s*어눌|발음이\s*이상"
    r"|심한\s*어지럼|어지러워서\s*(쓰러|주저앉)|쓰러졌"
    r"|저혈당\s*쇼크|혼수(상태)?"
    r"|응급실|119"
)

MEDICATION_PATTERN = re.compile(
    r"(약|복용|용량|처방).*(시작|중단|끊|늘|줄|변경)|(시작|중단|끊|늘|줄|변경).*(약|복용|용량|처방)"
)


def _citation(document: KnowledgeDocument) -> dict[str, object]:
    return {
        "document_id": document.document_id,
        "title": document.title,
        "url": document.url,
        "checked_at": document.checked_at,
    }


def answer_with_sources(question: str) -> dict[str, object]:
    normalized = question.strip().casefold()

    if EMERGENCY_SYMPTOM_PATTERN.search(normalized):
        emergency_doc = next(doc for doc in APPROVED_DOCUMENTS if doc.document_id == "kdca-hyperglycemia-emergency")
        return {
            "answer": (
                "가슴 통증, 의식 저하, 심한 호흡곤란, 마비, 경련 같은 증상은 응급상황일 수 있습니다. "
                "이 서비스의 답변을 기다리지 말고 지금 바로 119에 연락하거나 가까운 응급실을 방문하세요."
            ),
            "answer_status": "emergency_redirect",
            "citations": [_citation(emergency_doc)],
            "retrieval_method": "approved_document_keyword_v1",
        }

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
        "citations": [_citation(document) for document in selected],
        "retrieval_method": "approved_document_keyword_v1",
    }
