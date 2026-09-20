import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "src" / "frontend"


def test_main_pages_reference_the_shared_site_icon_set() -> None:
    for relative_path in ("index.html", "intro-retro.html", "suin/index.html"):
        html = (FRONTEND / relative_path).read_text(encoding="utf-8")
        assert 'href="/favicon.ico"' in html
        assert 'href="/static/assets/gandang-site-icon-32.png"' in html
        assert 'href="/static/assets/gandang-site-icon-180.png"' in html
        assert 'href="/static/site.webmanifest"' in html


def test_site_icon_assets_and_manifest_are_complete() -> None:
    assert (FRONTEND / "favicon.ico").read_bytes().startswith(b"\x00\x00\x01\x00")

    for size in (32, 180, 192, 512):
        icon = FRONTEND / "assets" / f"gandang-site-icon-{size}.png"
        assert icon.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    manifest = json.loads((FRONTEND / "site.webmanifest").read_text(encoding="utf-8"))
    assert manifest["name"] == "간당간당"
    assert {icon["sizes"] for icon in manifest["icons"]} == {"192x192", "512x512"}


def test_root_favicon_route_uses_the_compact_brand_icon() -> None:
    main = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert '@app.get("/favicon.ico", include_in_schema=False)' in main
    assert 'FRONTEND_DIR / "favicon.ico"' in main
