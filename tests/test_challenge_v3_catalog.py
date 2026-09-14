"""Pure contract checks for immutable, source-backed V3 challenge templates."""

import pytest

from app.services.challenge_catalog import (
    CATALOG_VERSION,
    CHALLENGE_V3_CATALOG,
    DIFFICULTIES,
    FOCUSES,
    metadata_for,
    recommend_codes,
    recommendation_policy,
)


def test_catalog_has_thirteen_versioned_items_and_separate_goal_and_proof_axes():
    codes = [item["code"] for item in CHALLENGE_V3_CATALOG]
    assert len(codes) == len(set(codes)) == 13
    assert all(code.startswith("v3_") for code in codes)
    metadata = [metadata_for(code) for code in codes]
    assert {item["domain"] for item in metadata} == {"hydration", "fiber_diet", "aerobic_activity"}
    assert {item["verification_type"] for item in metadata} == {1, 2, 3}
    assert {item["difficulty"] for item in metadata} == set(DIFFICULTIES)
    water = next(item for item in metadata if item["domain"] == "hydration")
    assert water["always_include"] is True and water["verification_type"] == 3
    assert water["goal"] == {"target_count": 1, "target_minutes": None, "period": "day"}
    for item in CHALLENGE_V3_CATALOG:
        detail = metadata_for(item["code"])
        assert item["source_title"] and item["source_url"].startswith("https://")
        assert item["safety_copy"] and detail["catalog_version"] == CATALOG_VERSION
        assert detail["goal_basis"] and detail["verification_scope"]
        if detail["verification_type"] == 1:
            assert detail["photo_review_target"] == "vegetable"
            assert "wholegrain" not in item["code"]
        if detail["domain"] != "hydration":
            index = DIFFICULTIES.index(detail["difficulty"]) + 1
            target = detail["goal"]
            assert (target["target_minutes"] or target["target_count"]) == (
                10 * index if detail["domain"] == "aerobic_activity" else index
            )


@pytest.mark.parametrize("focus", FOCUSES)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_recommendations_preserve_three_domains_and_never_increase_nonpreferred_difficulty(focus, difficulty):
    policy = recommendation_policy(focus, difficulty)
    selected_index = DIFFICULTIES.index(difficulty)
    for rotation in range(8):
        codes = recommend_codes(focus, difficulty, rotation)
        assert len(codes) == len(set(codes)) == 3
        assert codes == recommend_codes(focus, difficulty, rotation)
        assert codes[0] == "v3_hydration_choice"
        details = [metadata_for(code) for code in codes]
        assert {item["domain"] for item in details} == set(policy["domain_levels"])
        for item in details[1:]:
            assert item["difficulty"] == policy["domain_levels"][item["domain"]]
            assert DIFFICULTIES.index(item["difficulty"]) <= selected_index
    if selected_index and focus != "balanced":
        less_preferred = "aerobic_activity" if focus == "diet" else "fiber_diet"
        assert DIFFICULTIES.index(policy["domain_levels"][less_preferred]) == selected_index - 1


def test_refresh_cycles_are_bounded_deterministic_and_metadata_is_defensively_copied():
    choices = {tuple(recommend_codes("balanced", "easy", rotation)) for rotation in range(4)}
    assert len(choices) == 4
    assert recommend_codes("balanced", "easy", 0) == recommend_codes("balanced", "easy", 4)
    assert recommend_codes("balanced", "easy", 1_000_000)[0] == "v3_hydration_choice"
    detail = metadata_for("v3_hydration_choice")
    detail["goal"]["target_count"] = 100
    assert metadata_for("v3_hydration_choice")["goal"]["target_count"] == 1
    assert metadata_for("unknown") == {}


@pytest.mark.parametrize(
    ("focus", "difficulty", "rotation"),
    [("unknown", "easy", 0), ("balanced", "hard", 0), ("diet", "easy", -1), ("diet", "easy", 1_000_001)],
)
def test_invalid_recommendation_policy_is_rejected(focus, difficulty, rotation):
    with pytest.raises(ValueError):
        recommendation_policy(focus, difficulty, rotation)
