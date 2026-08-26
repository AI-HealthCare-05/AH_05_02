import asyncio
from pathlib import Path

from app.main import app, carrot_forest

ROOT = Path(__file__).resolve().parents[1]


def test_forest_has_independent_web_route() -> None:
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    response = asyncio.run(carrot_forest())
    html = Path(response.path).read_text(encoding="utf-8")
    assert "/forest" in paths
    assert "당근의 숲 (Beta)" in html
    assert 'id="forest-canvas"' in html


def test_pixel_game_exposes_required_map_movement_and_group_progress() -> None:
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")

    for label in ("오늘의 퀘스트", "5명 공동 목표", "옷장과 창고", "배치한 오브젝트"):
        assert label in html
    for landmark in ("drawMap", "drawTree", "당근밭", "공동 나무"):
        assert landmark in html + script
    for key in ("ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", 'w: "up"', 'a: "left"'):
        assert key in script
    assert html.count('data-move="') == 4
    assert 'width="768" height="512"' in html
    assert "image-rendering:pixelated" in (ROOT / "src/frontend/forest-game.css").read_text(encoding="utf-8")


def test_pixel_game_state_reward_and_adapter_contract_are_explicit() -> None:
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")

    assert "DemoForestAdapter" in script
    assert "ApiForestAdapter" in script
    assert "/challenge-cycles/current" in html
    assert "/user-challenges/{id}/logs/{date}" in html
    assert "/forest/spaces/{group_id}" in html
    assert script.count("completed: 3") == 4
    assert "completed >= 15" in script
    assert "state.rewardClaimed" in script
    assert "state.avatar.equipped" in script
    assert "state.placed.push" in script
    assert "localStorage" in script


def test_pixel_game_accessibility_and_excluded_features() -> None:
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    css = (ROOT / "src/frontend/forest-game.css").read_text(encoding="utf-8")
    combined = html + (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")

    assert "게임 내용으로 바로가기" in html
    assert 'role="status"' in html
    assert 'role="progressbar"' in html
    assert 'aria-label="아바타 이동 버튼"' in html
    assert "min-height:48px" in css
    for excluded in ("유료 가챠", "현금 결제", "건강정보 공개", "아이템 등급은 희소성"):
        assert excluded not in combined
