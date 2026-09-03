"""V2.1 joint constraint selection. Review availability is a server capability, not user input."""

import copy
import itertools
import json
from pathlib import Path

from app.dtos.challenge_v2 import V2Preferences

NOTICE = "앱 시작용 목표이며 진단·처방·예방 효과를 의미하지 않습니다. 의료진 지침이 우선입니다."
SOURCES = {
    "S1": "https://doi.org/10.1056/NEJMoa012512",
    "S2": "https://doi.org/10.2337/dc13-0084",
    "S3": "https://doi.org/10.2337/dc11-1931",
    "S4": "https://www.cdc.gov/diabetes/healthy-eating/diabetes-meal-planning.html",
    "S5": "https://www.ncbi.nlm.nih.gov/books/NBK566046/",
    "S6": "https://www.niddk.nih.gov/health-information/kidney-disease/chronic-kidney-disease-ckd/healthy-eating-adults-chronic-kidney-disease",
    "S7": "https://www.nhlbi.nih.gov/health/sleep-deprivation/healthy-sleep-habits",
    "S8": "https://www.cdc.gov/healthy-weight-growth/healthy-eating/nutrition-label.html",
    "S9": "https://www.nhs.uk/live-well/exercise/strength-exercises/",
}
DESIGN = json.loads(
    (Path(__file__).resolve().parents[2] / "docs/CHALLENGE_CATALOG_V2_20260903.json").read_text("utf-8")
)


def catalog() -> list[dict]:
    result = []
    for source in DESIGN["templates"]:
        item = copy.deepcopy(source)
        item["safety"] = NOTICE
        if item["domain"] == "activity":
            item["safety"] += " 흉통·심한 숨참·실신감·어지럼·통증 시 중단하고 의료 도움을 받으세요."
        if item["family_id"] == "H02":
            item["safety"] += " 구간별 실제 섭취량만 기록하세요. 0mL도 유효하며 더 마실 필요는 없습니다."
        item["sources"] = [{"title": ref, "url": SOURCES[ref]} for ref in item["evidence_refs"]]
        item["pilot_enabled"] = item["family_id"] != "A03"
        item["visual_criteria"] = (
            ["vegetable_visible"]
            + ([] if item["difficulty"] == "E" else ["protein_food_visible", "carbohydrate_food_visible"])
            if item["family_id"] == "D01"
            else ["serving_matches", "sugar_matches"]
            + ([] if item["difficulty"] == "E" else ["carbohydrate_matches", "same_category"])
            + (["same_basis_comparison_correct"] if item["difficulty"] == "H" else [])
            if item["family_id"] == "D02"
            else []
        )
        result.append(item)
        if item["family_id"] in {"D01", "D02", "D03", "A01"}:
            alternative = copy.deepcopy(item)
            alternative.update(
                code=item["code"] + "-C",
                proof_type="T3",
                required_uploads=0,
                completion_basis="self_report",
                pilot_enabled=True,
                alternative_for=item["code"],
            )
            alternative["title"] = {
                "D01": "예정된 식사 구성 돌아보기",
                "D02": "영양표시 읽고 내용 기록하기",
                "D03": "예정된 식사 시각·내용 기록하기",
                "A01": "식후 편안한 걷기 자가 기록",
            }[item["family_id"]]
            alternative["safety"] += " 사진 없는 접근성 대안이며 실제 섭취·영양소를 검증하지 않습니다."
            result.append(alternative)
    return result


def eligible(item: dict, pref: V2Preferences, review_available: bool = False) -> bool:
    if not item["pilot_enabled"]:
        return False
    family = item["family_id"]
    if "EMH".index(item["difficulty"]) > "EMH".index(pref.max_difficulty):
        return False
    if item["domain"] == "activity" and not (pref.safety_confirmed and pref.exercise_allowed):
        return False
    if family == "D01" and not (
        pref.safety_confirmed
        and pref.dietary_changes_allowed
        and not pref.therapeutic_diet
        and not pref.swallowing_restriction
        and not pref.food_allergy
    ):
        return False
    if family in {"D01", "D03"} and item["target_sessions"] > pref.planned_meals:
        return False
    if family == "H01" and (
        not pref.safety_confirmed
        or pref.fluid_restriction
        or pref.swallowing_restriction
        or pref.therapeutic_diet
        or item["target_sessions"] > pref.sugary_drink_opportunities
    ):
        return False
    if item["proof_type"] == "T1" and not review_available:
        return False
    return item["proof_type"] == "T3" or (pref.photo_consent and pref.photo_accessible)


def candidates_for(pref, review_available=False, recent=None):
    candidates = [x for x in catalog() if eligible(x, pref, review_available)]
    codes = {x["code"] for x in candidates}
    candidates = [x for x in candidates if x.get("alternative_for") not in codes]
    counts = {}
    for item in recent or []:
        counts[item["family_id"]] = counts.get(item["family_id"], 0) + 1
    return [x for x in candidates if counts.get(x["family_id"], 0) < x["weekly_candidate_days"]["max"]]


def mix_valid(items):
    return (
        len(items) == 3
        and {x["proof_type"] for x in items} == {"T1", "T2", "T3"}
        and {x["difficulty"] for x in items} == {"E", "M", "H"}
        and len({x["family_id"] for x in items}) == 3
    )


def exceptions_for(items, pref, review_available):
    reasons = []
    if not review_available:
        reasons.append("real_visual_review_unavailable")
    if not pref.photo_consent or not pref.photo_accessible:
        reasons.append("photo_consent_or_accessibility")
    if {x["difficulty"] for x in items} != {"E", "M", "H"}:
        reasons.append("difficulty_safety_or_preference_limit")
    if not mix_valid(items):
        reasons.append("proof_mix_safety_accessibility_or_weekly_limit")
    return reasons


def select_plan(pref: V2Preferences, day_ordinal: int, recent=None, review_available=False) -> dict:
    candidates = candidates_for(pref, review_available, recent)
    preferred = DESIGN["policy"]["sample_plans"][pref.mode].copy()
    available = {x["code"] for x in candidates}
    substitutions = []
    for i, code in enumerate(preferred):
        if code.startswith("H01") and code not in available:
            preferred[i] = code.replace("H01", "H02")
            substitutions.append({"from": code, "to": preferred[i], "reason": "no_eligible_existing_drink_opportunity"})
    desired = {
        "diet_focus": {"diet": 2, "routine": 1},
        "activity_focus": {"activity": 2, "diet": 1},
        "balanced": {"diet": 1, "activity": 1, "routine": 1},
    }[pref.mode]
    # Enumerate complete combinations before ranking; no top-three approximation.
    choices = [
        list(combo)
        for n in (3, 2, 1)
        for combo in itertools.combinations(candidates, n)
        if len({x["family_id"] for x in combo}) == n and sum(x["proof_type"] == "T1" for x in combo) <= 1
    ]
    exact = [combo for combo in choices if mix_valid(combo)]

    def score(combo):
        domains = [x["domain"] for x in combo]
        return (
            len(combo),
            len({x["difficulty"] for x in combo}),
            len({x["proof_type"] for x in combo}),
            sum(min(domains.count(k), v) for k, v in desired.items()),
            sum(x["code"] in preferred for x in combo),
            sum(x["family_id"] in DESIGN["policy"]["core_priority_families"] for x in combo),
        )

    selected = sorted(max(exact or choices, key=score), key=lambda x: "EMH".index(x["difficulty"])) if choices else []
    return {
        "items": selected,
        "proof_mix_exception_reason": exceptions_for(selected, pref, review_available),
        "substitutions": [s for s in substitutions if s["to"] in {x["code"] for x in selected}],
    }
