import asyncio
from pathlib import Path

from app.main import app, carrot_forest, forest_manifest, forest_service_worker

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

    for label in ("오늘의 퀘스트", "5명 공동 목표", "옷장 · 창고", "배치한 오브젝트"):
        assert label in html
    for landmark in ("drawMap", "drawTree", "당근밭", "공동 나무"):
        assert landmark in html + script
    for key in ("ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", 'w: "up"', 'a: "left"'):
        assert key in script
    assert html.count('data-move="') == 4
    assert 'width="1536" height="1024"' in html
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


def test_world_studio_workspace_controls_are_explicit() -> None:
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")

    for label in ("당근의 숲 작업실", "작업 도구", "ASSET LIBRARY", "SCENE OBJECTS"):
        assert label in html
    for control_id in ("reset-position", "zoom-toggle", "avatar-coordinate", "object-count"):
        assert f'id="{control_id}"' in html
    assert html.count("data-workspace-target=") == 4
    assert "scrollIntoView" in script
    assert 'classList.toggle("is-zoomed")' in script


def test_world_interactions_music_and_separated_storage_are_explicit() -> None:
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")

    for control_id in ("music-toggle", "interaction-prompt", "world-dialog", "chat-panel"):
        assert f'id="{control_id}"' in html
    assert 'id="wardrobe-list"' in html
    assert 'id="storage-list"' in html
    assert html.count("data-action=") == 5
    for key in (
        'event.key === "q"',
        'event.key === "r"',
        'event.key === "c"',
        'event.key === "x"',
        'event.key === "e"',
    ):
        assert key in script
    for behavior in ("CozyForestMusic", "toggleRide", "toggleSit", "openWorldDialog"):
        assert behavior in script
    assert "fillPixelRect(x - 14, y - 15, 28, 14" in script


def test_world_uses_high_resolution_pixel_renderer_and_detail_layers() -> None:
    script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")

    assert "const RENDER_SCALE = 2" in script
    assert "context.setTransform(RENDER_SCALE" in script
    for renderer in (
        "drawHouse",
        "drawCarrotPlot",
        "drawSharedTree",
        "drawPond",
        "drawFence",
        "drawFlower",
    ):
        assert f"function {renderer}" in script
    assert "requestAnimationFrame(animateWorld)" in script


def test_avatar_studio_has_renamed_categories_live_preview_and_save_flow() -> None:
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    css = (ROOT / "src/frontend/forest-game.css").read_text(encoding="utf-8")

    assert 'id="avatar-studio"' in html
    assert 'id="avatar-preview-canvas" width="560" height="640"' in html
    assert 'id="avatar-item-grid"' in html
    for label in (
        "완성형 코디",
        "헤어",
        "의상",
        "액세서리",
        "모자",
        "안경",
        "아우라",
        "이펙트",
        "탈것",
        "펫",
        "말풍선",
    ):
        assert f'label: "{label}"' in script
    assert "찌르기 이펙트" not in script
    for behavior in ("renderAvatarStudio", "renderAvatarPreview", "avatarDraftHistory", "avatar-studio-save"):
        assert behavior in script
    assert ".avatar-studio-layout" in css
    assert '.avatar-item-card[aria-pressed="true"]' in css


def test_group_tabs_reward_ceremony_and_profile_are_interactive() -> None:
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    css = (ROOT / "src/frontend/forest-game.css").read_text(encoding="utf-8")

    for control_id in (
        "group-remaining",
        "reward-celebration",
        "reward-reveal-name",
        "open-profile",
        "profile-dialog",
        "profile-nickname",
        "profile-avatar-canvas",
    ):
        assert f'id="{control_id}"' in html
    for behavior in (
        "activateInspectorPanel",
        "playRewardCelebration",
        "generateNickname",
        "renderProfileAvatar",
        "profile-form",
    ):
        assert behavior in script
    assert "renderInventory(reward)" in script
    assert "reward-flight" in css
    assert "rewardArrival" in css
    assert "newItemArrival" in css


def test_full_preset_clears_loose_decorations_and_uses_valid_glasses_ids() -> None:
    script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    compositor = (ROOT / "src/frontend/avatar-compositor.js").read_text(encoding="utf-8")

    assert (
        'const presetDecorationReset = { aura: "none", effect: "none", vehicle: "none", pet: "none", speech: "none" }'
        in script
    )
    assert "...presetDecorationReset, preset: linkedPreset" in script
    assert 'activeAvatarCategory !== "preset" && avatarDraft[activeAvatarCategory]' in script
    assert "cosmeticSchemaVersion: 2" in script
    assert "Object.assign(state.avatar.cosmetics, presetDecorationReset" in script
    assert 'glasses: "round"' not in script
    assert "context.ellipse(lensX, 123, 14, 10" in compositor


def test_basic_avatar_has_four_direction_walk_and_integrated_scooter_animation() -> None:
    script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    worker = (ROOT / "src/frontend/forest-sw.js").read_text(encoding="utf-8")
    assets = (
        ROOT / "src/frontend/assets/carrot-forest-basic-walk-atlas-v1.png",
        ROOT / "src/frontend/assets/carrot-forest-basic-scooter-atlas-v1.png",
    )

    for asset in assets:
        assert asset.exists()
        assert asset.stat().st_size > 100_000
        assert asset.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        assert asset.name in worker
    assert "drawAnimatedBasicWorldAvatar" in script
    assert "const directionRow = { down: 0, up: 1, left: 2, right: 3 }" in script
    assert "const directionColumn = { down: 0, up: 1, left: 2, right: 3 }" in script
    assert "walkingUntil" in script
    assert "walkAnimationFrame" in script
    assert "state.avatar.direction = direction" in script
    assert "drawLayeredAvatarPreview" in script
    assert "renderCatalogThumbnailCanvases" in script


def test_five_extra_presets_keep_directional_walk_vehicle_and_accessory_layers() -> None:
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    worker = (ROOT / "src/frontend/forest-sw.js").read_text(encoding="utf-8")
    preset_assets = (
        "carrot-forest-preset-red-bow-v1.png",
        "carrot-forest-preset-cow-hood-v1.png",
        "carrot-forest-preset-midnight-v1.png",
        "carrot-forest-preset-blue-cap-v1.png",
        "carrot-forest-preset-teal-bob-v1.png",
    )

    for preset in ("red_bow", "cow_hood", "midnight", "blue_cap", "teal_bob"):
        assert f'value="{preset}"' in html
        assert f"{preset}:" in script
    for asset_name in preset_assets:
        asset = ROOT / "src/frontend/assets" / asset_name
        assert asset.exists()
        assert asset.stat().st_size > 100_000
        assert asset_name in worker
    assert "presetBundles" in script
    assert "stylePresetByItem" in script
    assert "drawAnimatedAccessoryOverlay" in script
    assert "drawPreviewAccessoryOverlay" in script
    assert '{ id: "preset", label: "완성형 코디"' in script
    assert "if (drawAnimatedBasicWorldAvatar(avatar, cosmetics, x, y)) return" in script
    assert "else if (basicWalkAtlas.complete" in script
    assert "motionRow * 4 + directionColumn" in script


def test_avatar_studio_uses_original_pixel_sprite_atlases_instead_of_emoji_previews() -> None:
    script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    css = (ROOT / "src/frontend/forest-game.css").read_text(encoding="utf-8")
    avatar_atlas = ROOT / "src/frontend/assets/carrot-forest-avatar-atlas-v1.png"
    cosmetics_atlas = ROOT / "src/frontend/assets/carrot-forest-cosmetics-atlas-v1.png"

    for asset in (avatar_atlas, cosmetics_atlas):
        assert asset.exists()
        assert asset.stat().st_size > 100_000
        assert asset.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert "drawAtlasCell" in script
    assert "avatarSpriteIndex" in script
    assert "drawGeneratedWorldAvatar" in script
    assert "carrot-forest-avatar-atlas-v1.png" in css
    assert "carrot-forest-cosmetics-atlas-v1.png" in css


def test_world_scene_transitions_visual_storage_cats_and_fishing_are_connected() -> None:
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    css = (ROOT / "src/frontend/forest-game.css").read_text(encoding="utf-8")
    worker = (ROOT / "src/frontend/forest-sw.js").read_text(encoding="utf-8")
    asset_names = (
        "carrot-forest-world-v2.png",
        "carrot-forest-home-v1.png",
        "carrot-forest-garden-v1.png",
        "carrot-forest-cat-pets-v1.png",
        "carrot-forest-storage-atlas-v1.png",
    )

    assert 'id="scene-exit"' in html
    for scene in ('switchScene("home")', 'switchScene("garden")', 'switchScene("world")'):
        assert scene in script
    for action in ("enter_home", "enter_garden", "rest", "water", "fish", "exit_scene"):
        assert f'action === "{action}"' in script
    assert "state.fishCaught" in script
    assert "state.fishing" in script
    assert "blue_eyes_white_cat" in script
    assert "gold_eyes_orange_cat" in script
    assert "catPetAtlas" in script
    assert "storage-icon-item" in script
    assert "storage-sprite-thumb" in css
    for asset_name in asset_names:
        asset = ROOT / "src/frontend/assets" / asset_name
        assert asset.exists()
        assert asset.stat().st_size > 100_000
        assert asset.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        assert asset_name in worker


def test_pixel_game_is_installable_pwa() -> None:
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    manifest = (ROOT / "src/frontend/forest.webmanifest").read_text(encoding="utf-8")
    worker = (ROOT / "src/frontend/forest-sw.js").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")

    assert {"/manifest.webmanifest", "/forest-sw.js"}.issubset(paths)
    assert 'rel="manifest" href="/manifest.webmanifest"' in html
    assert 'id="install-pwa"' in html
    assert '"display": "standalone"' in manifest
    assert '"sizes": "192x192"' in manifest
    assert '"sizes": "512x512"' in manifest
    assert "beforeinstallprompt" in script
    assert 'id="forest-boot" role="status"' in html
    assert "forest-style-ready" in html
    assert "forest-local-pwa-reset-v20" in html
    assert "registration.unregister()" in html
    assert 'classList.add("forest-script-ready")' in script
    assert "localDemoOrigin" in script
    assert "const CORE_SHELL" in worker
    assert "Promise.allSettled" in worker
    assert 'serviceWorker.register("/forest-sw.js", { scope: "/forest" })' in script
    assert 'url.pathname.startsWith("/api/")' in worker
    assert "carrot-forest-avatar-atlas-v1.png" in worker
    assert "carrot-forest-cosmetics-atlas-v1.png" in worker


def test_phaser_premium_avatar_engine_and_offline_assets_are_connected() -> None:
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    game_script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    phaser_script = (ROOT / "src/frontend/forest-phaser.js").read_text(encoding="utf-8")
    worker = (ROOT / "src/frontend/forest-sw.js").read_text(encoding="utf-8")

    assert 'id="phaser-world" role="application"' in html
    assert "/static/vendor/phaser-3.90.0.min.js" in html
    assert "/static/forest-phaser.js" in html
    for category in ("preset", "aura", "effect", "vehicle", "pet", "speech"):
        assert f'id: "{category}"' in game_script
    for event_name in (
        "forest-avatar-updated",
        "forest-avatar-draft",
        "forest-phaser-position",
        "forest-phaser-interact",
    ):
        assert event_name in game_script or event_name in phaser_script
    for preset in ("red_bow", "cow_hood", "midnight", "blue_cap", "teal_bob"):
        assert preset in phaser_script
        assert f"carrot-forest-avatar-{preset}-normalized-v2.png" in phaser_script
    assert "directionRows" in phaser_script
    assert "setPremiumFrame" in phaser_script
    assert "this.compositeTexture.refresh" in phaser_script
    assert "this.keys.R.isDown" in phaser_script
    assert 'this.load.spritesheet("cat-pets"' in phaser_script
    assert "gold_eyes_orange_cat" in phaser_script
    assert "Phaser.Scale.FIT" in phaser_script
    assert "gandang-carrot-forest-pwa-v23" in worker
    assert "/static/assets/lpc/" not in worker
    assert "/static/avatar-compositor.js" in html
    assert "CarrotAvatarCompositor" in phaser_script
    assert "const NAMEPLATE_Y = -126" in phaser_script
    assert "const AVATAR_RENDER_SCALE = 0.43" in phaser_script
    assert (ROOT / "src/frontend/vendor/phaser-3.90.0.min.js").stat().st_size > 1_000_000
    assert (ROOT / "src/frontend/vendor/PHASER_LICENSE.txt").exists()


def test_modular_avatar_v3_has_exact_layer_cells_and_runtime_wiring() -> None:
    import struct

    atlas = ROOT / "src/frontend/assets/carrot-forest-modular-avatar-atlas-v3.png"
    raw = atlas.read_bytes()
    width, height = struct.unpack(">II", raw[16:24])
    compositor = (ROOT / "src/frontend/avatar-compositor.js").read_text(encoding="utf-8")
    game_script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    phaser_script = (ROOT / "src/frontend/forest-phaser.js").read_text(encoding="utf-8")

    assert (width, height) == (224 * 4, 288 * 11)
    assert (ROOT / "scripts/build_modular_avatar_atlas.py").exists()
    for row in range(1, 11):
        assert f": {row}" in compositor
    assert "drawModularFrame" in compositor
    assert "carrot-forest-modular-avatar-atlas-v3.png" in game_script
    assert "carrot-forest-modular-avatar-atlas-v3.png" in phaser_script


def test_normalized_avatar_atlases_have_exact_cells_and_reproducible_manifest() -> None:
    import json
    import struct

    manifest_path = ROOT / "src/frontend/assets/carrot-forest-avatar-manifest-v2.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["cell_width"] == 224
    assert manifest["cell_height"] == 288
    assert (ROOT / "scripts/build_carrot_avatar_atlases.py").exists()
    assert (ROOT / "requirements-assets.txt").exists()
    for preset, config in manifest["presets"].items():
        image_path = ROOT / "src/frontend/assets" / config["file"]
        raw = image_path.read_bytes()
        width, height = struct.unpack(">II", raw[16:24])
        assert width == 224 * 4
        assert height == 288 * config["rows"]
        assert len(config["frames"]) == 4 * config["rows"]
        for frame in config["frames"]:
            left, top, right, bottom = frame["normalized_bbox"]
            assert 0 <= left < right <= manifest["cell_width"]
            assert 0 <= top < bottom <= manifest["cell_height"]
        assert preset in ("red_bow", "cow_hood", "midnight", "blue_cap", "teal_bob")


def test_pwa_route_response_contracts() -> None:
    manifest_response = asyncio.run(forest_manifest())
    worker_response = asyncio.run(forest_service_worker())

    assert manifest_response.media_type == "application/manifest+json"
    assert manifest_response.headers["cache-control"] == "no-cache"
    assert worker_response.media_type == "text/javascript"
    assert worker_response.headers["service-worker-allowed"] == "/forest"
