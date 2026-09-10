"""RAG 승인 문서 기반 규칙 기반(rule-based) 퀴즈 자동 생성기.

`src/rag/engine.py`의 `APPROVED_DOCUMENTS`(질병관리청·대한당뇨병학회 등 검토된 출처)를
입력으로 받아, 생성형 AI 없이 정규식/문자열 규칙만으로 두 종류의 퀴즈를 만든다.

- OX(참/거짓) 퀴즈: 문서 본문에서 숫자+단위 표현(예: "150분", "130/80mmHg")을 찾아
  그대로 두면 참, 숫자를 규칙적으로 바꾸면 거짓 문항이 된다. 어느 버전을 낼지는
  document_id 해시로 결정하므로 항상 같은 문서는 같은 결과를 낸다(재현 가능).
- 빈칸 채우기(4지선다) 퀴즈: 문서의 키워드 중 본문에 실제로 등장하는 첫 키워드를
  빈칸으로 가리고, 다른 문서들의 키워드 중 이 문서 본문에 나오지 않는 것들을
  오답 후보로 사용한다.

두 방식 모두 새로운 의학적 주장을 만들어내지 않고, 이미 검토·승인된 문서의 문장·
숫자·키워드만 재배열한다. 숫자/키워드를 추출하지 못하는 문서는 해당 유형의 퀴즈를
만들지 않고 건너뛴다(억지로 만들지 않음).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from src.rag.engine import APPROVED_DOCUMENTS, KnowledgeDocument

_BLANK = "＿＿＿＿"

_UNIT_NUMBER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\d+(?:\.\d+)?\s*mmHg"),
    re.compile(r"\d+(?:\.\d+)?\s*bpm"),
    re.compile(r"\d+(?:\.\d+)?\s*분"),
    re.compile(r"\d+(?:\.\d+)?\s*%"),
    re.compile(r"\d+(?:\.\d+)?\s*일"),
    re.compile(r"\d+(?:\.\d+)?\s*회"),
    re.compile(r"\d+(?:\.\d+)?\s*시간"),
    re.compile(r"\d+(?:\.\d+)?\s*년"),
)

_LEADING_NUMBER = re.compile(r"\d+(?:\.\d+)?")


@dataclass(frozen=True)
class QuizItem:
    quiz_id: str
    document_id: str
    quiz_type: str  # "ox" | "fill_in_blank"
    question: str
    options: tuple[str, ...] | None  # OX는 None(항상 참/거짓), 빈칸은 4지선다
    answer: str
    explanation: str
    source_title: str
    source_url: str
    checked_at: str

    def as_dict(self) -> dict[str, object]:
        """정답·해설을 포함한 전체 표현. 채점 로직이나 테스트에서만 사용하고,
        정답 제출 전 사용자에게 그대로 노출하지 않는다(as_public_dict 참고)."""
        return {
            "quiz_id": self.quiz_id,
            "document_id": self.document_id,
            "quiz_type": self.quiz_type,
            "question": self.question,
            "options": list(self.options) if self.options is not None else None,
            "answer": self.answer,
            "explanation": self.explanation,
            "source_title": self.source_title,
            "source_url": self.source_url,
            "checked_at": self.checked_at,
        }

    def as_public_dict(self) -> dict[str, object]:
        """정답·해설을 뺀 조회용 표현. 퀴즈 목록 조회 API는 이 형태만 반환해야
        사용자가 풀기 전에 정답을 미리 볼 수 없다."""
        return {
            "quiz_id": self.quiz_id,
            "document_id": self.document_id,
            "quiz_type": self.quiz_type,
            "question": self.question,
            "options": list(self.options) if self.options is not None else None,
            "source_title": self.source_title,
            "source_url": self.source_url,
            "checked_at": self.checked_at,
        }


def _stable_int(*parts: str) -> int:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _format_number(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}"


def _find_first_unit_number(text: str) -> re.Match[str] | None:
    best: re.Match[str] | None = None
    for pattern in _UNIT_NUMBER_PATTERNS:
        match = pattern.search(text)
        if match and (best is None or match.start() < best.start()):
            best = match
    return best


def _perturb_number_span(text: str, match: re.Match[str]) -> str | None:
    matched = match.group(0)
    number_match = _LEADING_NUMBER.match(matched)
    if not number_match:
        return None
    original_value = float(number_match.group(0))
    if original_value <= 0:
        return None
    perturbed_value = original_value * 2
    perturbed_matched = _LEADING_NUMBER.sub(_format_number(perturbed_value), matched, count=1)
    return text[: match.start()] + perturbed_matched + text[match.end() :]


def _make_ox_item(document: KnowledgeDocument) -> QuizItem | None:
    match = _find_first_unit_number(document.text)
    if match is None:
        return None
    false_text = _perturb_number_span(document.text, match)
    if false_text is None:
        return None

    use_false_version = _stable_int("ox", document.document_id) % 2 == 0
    if use_false_version:
        question_text = false_text
        answer = "거짓"
    else:
        question_text = document.text
        answer = "참"

    return QuizItem(
        quiz_id=f"ox-{document.document_id}",
        document_id=document.document_id,
        quiz_type="ox",
        question=f"다음 설명은 맞을까요, 틀릴까요? \"{question_text}\"",
        options=None,
        answer=answer,
        explanation=f"정확한 설명: {document.text}",
        source_title=document.title,
        source_url=document.url,
        checked_at=document.checked_at,
    )


def _make_fill_in_blank_item(
    document: KnowledgeDocument,
    all_documents: tuple[KnowledgeDocument, ...],
    used_keywords: set[str],
) -> QuizItem | None:
    candidates = [kw for kw in document.keywords if len(kw) >= 2 and kw in document.text]
    if not candidates:
        return None
    # 문서 집합 전체의 다양성을 위해, 아직 다른 문서의 정답으로 쓰이지 않은 키워드를 우선한다.
    # 후보가 전부 이미 쓰였다면(작은 문서 집합에서는 흔함) 첫 후보로 되돌아간다.
    correct_keyword = next((kw for kw in candidates if kw not in used_keywords), candidates[0])
    used_keywords.add(correct_keyword)

    # 정답 단어가 문장에 여러 번 등장하면 전부 가린다. 하나만 가리면 뒤에 남은
    # 동일 단어를 보고 정답을 바로 알 수 있기 때문이다.
    masked_text = document.text.replace(correct_keyword, _BLANK)

    distractor_pool = sorted(
        {
            kw
            for other in all_documents
            if other.document_id != document.document_id
            for kw in other.keywords
            if kw != correct_keyword and kw not in document.text
        }
    )
    if len(distractor_pool) < 3:
        return None
    # 매 문서마다 다른 오답 조합이 나오도록 문서 해시로 시작 위치를 정해 순환 선택한다.
    pool_size = len(distractor_pool)
    start = _stable_int("distractor", document.document_id) % pool_size
    distractors = [distractor_pool[(start + i) % pool_size] for i in range(3)]

    options = [correct_keyword, *distractors]
    insert_at = _stable_int("blank", document.document_id) % 4
    if insert_at != 0:
        options[0], options[insert_at] = options[insert_at], options[0]

    return QuizItem(
        quiz_id=f"blank-{document.document_id}",
        document_id=document.document_id,
        quiz_type="fill_in_blank",
        question=f"빈칸에 알맞은 단어를 고르세요: \"{masked_text}\"",
        options=tuple(options),
        answer=correct_keyword,
        explanation=f"정답은 \"{correct_keyword}\"입니다. 원문: {document.text}",
        source_title=document.title,
        source_url=document.url,
        checked_at=document.checked_at,
    )


def generate_quizzes(documents: tuple[KnowledgeDocument, ...] = APPROVED_DOCUMENTS) -> list[QuizItem]:
    """승인된 문서들로부터 규칙 기반 퀴즈 목록을 생성한다.

    숫자·키워드 조건을 만족하지 못하는 문서는 해당 유형을 건너뛰므로,
    문서 수 대비 생성되는 퀴즈 수는 문서마다 0~2개로 다를 수 있다.
    """
    items: list[QuizItem] = []
    used_keywords: set[str] = set()
    for document in documents:
        ox_item = _make_ox_item(document)
        if ox_item is not None:
            items.append(ox_item)
        blank_item = _make_fill_in_blank_item(document, documents, used_keywords)
        if blank_item is not None:
            items.append(blank_item)
    return items
