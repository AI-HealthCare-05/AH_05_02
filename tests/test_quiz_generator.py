"""RAG 승인 문서 기반 규칙 기반 퀴즈 생성기 테스트."""

from __future__ import annotations

from src.quiz.generator import generate_quizzes
from src.rag.engine import APPROVED_DOCUMENTS


def test_generation_is_deterministic():
    first = [item.as_dict() for item in generate_quizzes()]
    second = [item.as_dict() for item in generate_quizzes()]
    assert first == second


def test_every_quiz_item_is_grounded_in_an_approved_document():
    document_ids = {document.document_id for document in APPROVED_DOCUMENTS}
    for item in generate_quizzes():
        assert item.document_id in document_ids
        assert item.source_title
        assert item.source_url.startswith("https://")
        assert item.checked_at


def test_ox_items_only_generated_when_a_unit_number_exists_in_the_source_text():
    items = generate_quizzes()
    ox_by_doc = {item.document_id: item for item in items if item.quiz_type == "ox"}
    # 숫자+단위 표현이 없는 문서는 OX 문항을 만들지 않는다.
    assert "kdca-diabetes" not in ox_by_doc
    assert "who-activity" not in ox_by_doc
    assert "cdc-prevent-t2" not in ox_by_doc
    # 숫자+단위 표현이 있는 문서는 OX 문항이 생성된다.
    assert "diabetes-or-kr-exercise" in ox_by_doc
    assert "kdca-diabetes-diet" in ox_by_doc


def test_ox_answer_matches_whether_the_question_text_was_altered():
    items = generate_quizzes()
    ox_by_doc = {item.document_id: item for item in items if item.quiz_type == "ox"}
    original = {document.document_id: document.text for document in APPROVED_DOCUMENTS}

    for document_id, item in ox_by_doc.items():
        question_contains_original_sentence = original[document_id] in item.question
        if item.answer == "참":
            assert question_contains_original_sentence
        else:
            assert item.answer == "거짓"
            assert not question_contains_original_sentence
        # 참/거짓과 무관하게 해설에는 항상 정확한 원문이 노출된다.
        assert original[document_id] in item.explanation


def test_ox_false_variant_changes_only_the_targeted_number():
    # diabetes-or-kr-exercise 원문의 "일주일에 3일 이상"이 거짓 버전에서는 배로 늘어난 숫자로 바뀐다.
    items = generate_quizzes()
    item = next(i for i in items if i.quiz_id == "ox-diabetes-or-kr-exercise")
    assert item.answer == "거짓"
    assert "6일" in item.question
    assert "3일" not in item.question
    # 나머지 문장 내용은 그대로 유지된다.
    assert "산책, 조깅, 맨손체조, 자전거 타기 같은 가벼운 전신 운동이 권장됩니다." in item.question


def test_fill_in_blank_options_contain_exactly_one_correct_answer():
    items = generate_quizzes()
    blanks = [item for item in items if item.quiz_type == "fill_in_blank"]
    assert blanks
    for item in blanks:
        assert item.options is not None
        assert len(item.options) == 4
        assert len(set(item.options)) == 4
        assert item.options.count(item.answer) == 1
        assert "＿＿＿＿" in item.question
        assert item.answer not in item.question  # 정답 단어 자체는 가려져 있어야 함


def test_fill_in_blank_prefers_a_different_answer_per_document_when_possible():
    # 문서마다 서로 다른 정답 키워드를 우선 배정해 같은 단어만 반복 출제되지 않도록 한다.
    items = generate_quizzes()
    blanks = [item for item in items if item.quiz_type == "fill_in_blank"]
    answers = [item.answer for item in blanks]
    # 12개 문서 중 대부분은 서로 다른 키워드를 정답으로 갖는다(완전한 유일성까지는 보장하지 않음).
    assert len(set(answers)) >= len(answers) - 1


def test_public_dict_hides_answer_and_explanation():
    # 조회 API가 사용할 표현에는 정답·해설이 없어야 풀기 전에 정답이 보이지 않는다.
    for item in generate_quizzes():
        public = item.as_public_dict()
        assert "answer" not in public
        assert "explanation" not in public
        assert public["question"] == item.question
        assert public["options"] == (list(item.options) if item.options is not None else None)


def test_generate_quizzes_accepts_a_custom_document_subset():
    target_ids = {
        "kdca-hypertension",
        "kdca-diabetes",
        "who-activity",
        "cdc-prevent-t2",
        "kdca-diabetes-diet",
    }
    subset = tuple(document for document in APPROVED_DOCUMENTS if document.document_id in target_ids)
    items = generate_quizzes(subset)
    assert items
    assert all(item.document_id in target_ids for item in items)


def test_fill_in_blank_skipped_when_too_few_peer_documents_for_distractors():
    # 빈칸 채우기는 다른 문서의 키워드에서 오답을 뽑는다. 함께 넘긴 문서가 1개뿐이면
    # 오답 후보가 없어 억지로 문제를 만들지 않고 건너뛴다.
    subset = tuple(document for document in APPROVED_DOCUMENTS if document.document_id == "kdca-hypertension")
    assert generate_quizzes(subset) == []
