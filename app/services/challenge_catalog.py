"""Versioned, source-backed challenge templates; goals are product design, not prescriptions.

Codes freeze daily obligations for existing cycles. Change the version/code, not
an existing goal, when revising this catalog in the future.
"""

from __future__ import annotations

from copy import deepcopy

CATALOG_VERSION = "evidence-v3"
DIFFICULTIES = ("easy", "moderate", "advanced")
FOCUSES = ("balanced", "diet", "activity")
SOURCES = {
    "drink": {
        "title": "대한당뇨병학회: 당뇨인 제로칼로리 음료 괜찮을까",
        "url": "https://new.diabetes.or.kr/bbs/?code=news&mode=view&number=2030",
    },
    "fiber": {
        "title": "미국당뇨병학회(ADA): 식이섬유와 탄수화물",
        "url": "https://diabetes.org/food-nutrition/understanding-carbs/get-to-know-carbs",
    },
    "activity": {
        "title": "대한당뇨병학회: 운동 자주 묻는 질문",
        "url": "https://www.diabetes.or.kr/bbs/?category=M&code=faq",
    },
    "prevention": {
        "title": "NIDDK: 제2형 당뇨병 예방",
        "url": "https://www.niddk.nih.gov/health-information/diabetes/overview/preventing-type-2-diabetes",
    },
}
_METADATA: dict[str, dict] = {}


def _item(code, title, category, domain, difficulty, count, minutes, verification, description, source_key):
    source = SOURCES[source_key]
    if domain == "hydration":
        goal = "오늘 음료 선택 또는 개인 수분 지침 준수 1회 확인"
        safety = "물의 양을 늘리는 과제가 아닙니다. 수분 제한이 있으면 의료진 지침을 지킨 것으로 체크하세요."
    elif category == "diet":
        goal = f"하루 {count}끼에서 실천 · 대표 사진 1장"
        safety = "전체 식사량을 늘리거나 끼니를 거르지 마세요. 알레르기·신장질환 등 개인별 치료식 지침이 우선입니다."
    else:
        goal = f"하루 누적 {minutes}분 · 나누어 실천 가능"
        safety = "통증·어지럼·심한 호흡곤란이 있으면 중단하세요. 운동 제한이 있으면 의료진과 목표를 조정하세요."
    _METADATA[code] = {
        "catalog_version": CATALOG_VERSION,
        "domain": domain,
        "difficulty": difficulty,
        "verification_type": verification,
        "always_include": domain == "hydration",
        "goal": {"target_count": count, "target_minutes": minutes, "period": "day"},
        "goal_basis": "서비스의 단계별 실천 목표이며 연구에서 검증된 개인별 처방량이 아닙니다.",
        "verification_scope": (
            "대표 사진의 채소 포함 여부만 확인합니다. 끼니 횟수·섭취량·실제 섭취는 본인 기록입니다."
            if verification == 1
            else "사진 제출 여부만 확인합니다. 통곡물·영양성분·운동 시간의 진위를 자동 판정하지 않습니다."
            if verification == 2
            else "본인의 실천 여부를 체크합니다. 의료적 검증이 아닙니다."
        ),
        "photo_review_target": "vegetable" if verification == 1 else None,
        "supporting_sources": [source, SOURCES["prevention"]],
        "weekly_guidance": (
            "중강도 유산소 주 150분 이상은 일반 권고입니다. 처음에는 작은 목표부터, 개인 상태에 맞게 늘리세요."
            if category == "activity"
            else None
        ),
    }
    return {
        "code": code,
        "title": title,
        "category": category,
        "daily_goal": goal,
        "description": description,
        "safety_copy": safety,
        "source_title": source["title"],
        "source_url": source["url"],
    }


def _build_catalog() -> tuple[dict, ...]:
    items = [
        _item(
            "v3_hydration_choice",
            "당 음료 대신 물 · 개인 수분 지침 확인",
            "hydration",
            "hydration",
            "easy",
            1,
            None,
            3,
            "음료를 선택할 때 물을 우선하고 당이 든 음료는 줄여요. 이미 당 음료를 마시지 않았다면 그 실천을 확인해요. 수분 제한 중이면 정해진 지침을 지켰는지 확인해요.",
            "drink",
        )
    ]
    for index, difficulty in enumerate(DIFFICULTIES, start=1):
        items.extend(
            [
                _item(
                    f"v3_vegetable_{difficulty}",
                    "채소 반찬을 포함한 식사",
                    "diet",
                    "fiber_diet",
                    difficulty,
                    index,
                    None,
                    1,
                    "평소 식사 구성 안에 비전분 채소를 포함해요. 실천한 끼니 수를 적고 대표 식사 사진을 제출해요. 사진은 채소 포함 여부만 확인해요.",
                    "fiber",
                ),
                _item(
                    f"v3_wholegrain_{difficulty}",
                    "정제 곡물 일부를 통곡물·콩류로 바꾸기",
                    "diet",
                    "fiber_diet",
                    difficulty,
                    index,
                    None,
                    2,
                    "전체 식사량은 늘리지 않고 흰밥·흰빵 일부를 통곡물·잡곡·콩류로 바꿔요. 실천한 끼니 수와 대표 사진을 남겨요. 섬유소는 무리하지 않고 서서히 늘려요.",
                    "fiber",
                ),
                _item(
                    f"v3_walk_{difficulty}",
                    "내 몸에 맞게 꾸준히 걷기",
                    "activity",
                    "aerobic_activity",
                    difficulty,
                    1,
                    index * 10,
                    2,
                    "걷기 시간을 나누어 누적해요. 가능한 경우 대화할 수 있을 정도의 중강도로 걷고, 운동 후 안전한 곳에서 활동 기록 화면이나 사진을 남겨요.",
                    "activity",
                ),
                _item(
                    f"v3_indoor_aerobic_{difficulty}",
                    "실내에서 유산소 활동 이어가기",
                    "activity",
                    "aerobic_activity",
                    difficulty,
                    1,
                    index * 10,
                    2,
                    "안전한 실내 걷기 또는 익숙한 실내 자전거로 활동 시간을 누적해요. 넘어질 위험이 없는 환경에서 실천하고 종료 후 기록 화면이나 사진을 남겨요.",
                    "activity",
                ),
            ]
        )
    return tuple(items)


CHALLENGE_V3_CATALOG = _build_catalog()


def metadata_for(code: str) -> dict:
    return deepcopy(_METADATA.get(code, {}))


def recommendation_policy(focus: str, difficulty: str, rotation: int = 0) -> dict:
    if focus not in FOCUSES or difficulty not in DIFFICULTIES or not 0 <= rotation <= 1_000_000:
        raise ValueError("Invalid challenge preference, difficulty or rotation")
    index = DIFFICULTIES.index(difficulty)
    # Never raise a non-preferred domain beyond the difficulty the user selected.
    diet_level = DIFFICULTIES[max(0, index - (focus == "activity"))]
    activity_level = DIFFICULTIES[max(0, index - (focus == "diet"))]
    return {
        "catalog_version": CATALOG_VERSION,
        "focus": focus,
        "difficulty": difficulty,
        "domain_levels": {"hydration": "common", "fiber_diet": diet_level, "aerobic_activity": activity_level},
        "daily_count": 3,
        "rotation": rotation,
        "notice": "음료·식단·운동 각 1개를 유지합니다. 선호 영역은 선택한 단계, 다른 영역은 한 단계 가볍게 제안합니다. 쉬움에서는 모두 작은 목표로 시작합니다. 후보는 반복될 수 있습니다.",
    }


def recommend_codes(focus: str, difficulty: str, rotation: int = 0) -> list[str]:
    levels = recommendation_policy(focus, difficulty, rotation)["domain_levels"]
    diet = ("wholegrain", "vegetable")[rotation % 2]
    activity = ("walk", "indoor_aerobic")[(rotation // 2) % 2]
    return ["v3_hydration_choice", f"v3_{diet}_{levels['fiber_diet']}", f"v3_{activity}_{levels['aerobic_activity']}"]
