"""RAG 근거 문서(APPROVED_DOCUMENTS)를 4주 건강교육 커리큘럼 주차에 배정하는 표.

지금까지는 이 매핑이 `src/frontend/app.js`의 `weekByDocument`에만 있었는데, 주차별 퀴즈 잠금을
백엔드에서 강제하려면 백엔드도 같은 매핑을 알아야 한다. 그래서 여기를 단일 기준(source of truth)으로
삼고, `/health-education/quizzes` 응답에 문서마다 week_number를 실어 보내 프론트가 자체 표 대신 이
값을 쓰도록 바꿨다(`assignGeneratedQuizzes`의 `weekByDocument` 하드코딩 제거).

문서를 추가·삭제할 때는 이 표도 같이 갱신해야 한다.
"""

from __future__ import annotations

DOCUMENT_WEEK_NUMBER: dict[str, int] = {
    "kdca-diabetes": 1,
    "kdca-prediabetes": 1,
    "kdca-diabetes-complications": 1,
    "diabetes-or-kr-definition": 1,
    "diabetes-or-kr-symptoms": 1,
    "diabetes-or-kr-diagnosis": 1,
    "diabetes-or-kr-type1": 1,
    "kda-guideline-screening": 1,
    "dbpia-prediabetes-young-adults": 1,
    "diabetes-or-kr-footcare": 1,
    "diabetes-or-kr-checkup-schedule": 1,
    "kdca-diabetes-exercise": 2,
    "diabetes-or-kr-exercise": 2,
    "diabetes-or-kr-exercise-intensity": 2,
    "who-activity": 2,
    "dbpia-cgm-exercise-pilot": 2,
    "kda-guideline-cgm": 2,
    "kdca-diabetes-diet": 3,
    "samsunghospital-diabetes-management": 3,
    "diabetes-or-kr-treatment-goals": 3,
    "diabetes-or-kr-hypoglycemia": 3,
    "diabetes-or-kr-gestational": 3,
    "kda-guideline-glycemic-targets": 3,
    "dbpia-htn-diabetes-lifestyle": 3,
    "cdc-prevent-t2": 4,
    "kdca-hypertension": 4,
    "kdca-hyperglycemia-emergency": 4,
    "diabetes-or-kr-stress": 4,
    "diabetes-or-kr-mind": 4,
    "diabetes-or-kr-smoking": 4,
}


def week_number_for_document(document_id: str) -> int | None:
    return DOCUMENT_WEEK_NUMBER.get(document_id)
