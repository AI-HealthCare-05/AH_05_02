from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_forest_theme_is_loaded_last_and_owns_shared_tokens() -> None:
    html = (ROOT / "src/frontend/index.html").read_text(encoding="utf-8")
    theme = (ROOT / "src/frontend/forest-unified-theme.css").read_text(encoding="utf-8")

    assert "forest-unified-theme.css" in html
    assert html.index("forest-unified-theme.css") > html.index("wood-sign-theme.css")
    assert "--forest-wood-dark" in theme
    assert "--forest-paper" in theme
    assert ".signup-house-board" in theme
    assert ".eligibility-forest-board" in theme
    assert ".health-room-board" in theme
    assert "#workspace-panel-home" in theme


def test_signup_board_is_bounded_and_mobile_layout_is_single_column() -> None:
    theme = (ROOT / "src/frontend/forest-unified-theme.css").read_text(encoding="utf-8")

    assert "max-width: 900px !important" in theme
    assert "min-height: 0 !important" in theme
    assert "@media (max-width: 820px)" in theme
    assert "grid-template-columns: 1fr !important" in theme


def test_post_analysis_screens_do_not_use_legacy_negative_side_margins() -> None:
    theme = (ROOT / "src/frontend/forest-unified-theme.css").read_text(encoding="utf-8")

    assert ".screen.challenge-forest-screen.active" in theme
    assert '.screen[data-step="8"].active' in theme
    assert "margin: 0 !important" in theme
    assert "overflow-x: clip !important" in theme
