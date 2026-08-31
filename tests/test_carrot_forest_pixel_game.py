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
    assert html.count("data-action=") == 8
    for key in (
        'event.key === "q"',
        'event.key === "r"',
        'event.key === "c"',
        'event.key === "x"',
        'event.key === "e"',
        'event.key === "z"',
        'event.key === "0"',
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
        "피부",
        "헤어",
        "헤어 색",
        "상의",
        "상의 색",
        "하의",
        "하의 색",
        "신발",
        "신발 색",
        "얼굴",
        "모자",
        "안경",
        "아우라",
        "이펙트",
        "탈것",
        "펫",
        "말풍선",
        "동작",
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


def test_forest_onboarding_rag_collaboration_and_tool_routes_are_connected() -> None:
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    app_script = (ROOT / "src/frontend/app.js").read_text(encoding="utf-8")

    for control_id in (
        "start-prediction-flow",
        "challenge-flow-dialog",
        "forest-rag-form",
        "group-goal-form",
        "add-family-colleague",
        "inventory-dialog",
    ):
        assert f'id="{control_id}"' in html
    for step in ("이동 가능 확인", "건강정보 입력", "분석결과", "챌린지"):
        assert step in html
    for style in ("운동 중심", "식단 중심", "내가 조합하기"):
        assert style in html
    assert "오늘까지의 챌린지 결과를 토대로 챌린지 생성 중" in html
    assert "내 생활습관 지도" in html
    assert "내 생활습관 지도(RAG)" not in html
    assert "사진 인증 없이" not in html
    assert "당뇨 예방 챌린지" in html
    assert "who.int/publications" in script
    assert "cdc.gov/diabetes-prevention" in script
    assert 'window.location.href = "/?step=2"' in script
    assert "/?step=8&amp;workspace=together" in html
    assert "renderInventoryDialog" in script
    assert "groupGoalMemo" in script
    assert 'requestedView.get("workspace")' in app_script


def test_full_preset_clears_loose_decorations_and_uses_valid_glasses_ids() -> None:
    script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    compositor = (ROOT / "src/frontend/avatar-compositor.js").read_text(encoding="utf-8")

    assert (
        'const presetDecorationReset = { aura: "none", effect: "none", vehicle: "none", pet: "none", speech: "none" }'
        in script
    )
    assert "...presetDecorationReset, preset: linkedPreset" in script
    assert 'categoryId !== "preset" && avatarDraft[categoryId]' in script
    assert "cosmeticSchemaVersion: 3" in script
    assert "Object.assign(state.avatar.cosmetics, presetDecorationReset" in script
    assert 'glasses: "round"' not in script
    assert "context.ellipse(lensX, 123 + headAdjustmentY + glassesOffsetY, 14, 10" in compositor


def test_avatar_spacing_and_world_scale_can_be_tuned_by_user() -> None:
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    compositor = (ROOT / "src/frontend/avatar-compositor.js").read_text(encoding="utf-8")
    phaser = (ROOT / "src/frontend/forest-phaser.js").read_text(encoding="utf-8")

    for key in ("headOffsetY", "outfitOffsetY", "glassesOffsetY", "worldScale"):
        assert f'data-avatar-tuning="{key}"' in html
        assert key in script
    assert 'id="avatar-tuning-reset"' in html
    assert "avatarTuningDraft" in script
    assert "headOffsetY" in compositor
    assert "this.avatar.tuning.worldScale" in phaser


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
    assert '{ id: "lpcHair", label: "헤어"' in script
    assert '{ id: "lpcOutfit", label: "상의"' in script
    assert '{ id: "lpcBottom", label: "하의"' in script
    assert '{ id: "lpcShoes", label: "신발"' in script
    assert "if (drawAnimatedBasicWorldAvatar(avatar, cosmetics, x, y)) return" in script
    assert "basicWalkAtlas.complete && basicWalkAtlas.naturalWidth" in script
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
    assert "forest-local-pwa-reset-v32" in html
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

    assert 'id="phaser-world" role="application"' in html
    assert "/static/vendor/phaser-3.90.0.min.js" in html
    assert "/static/forest-phaser.js" in html
    for category in (
        "lpcHair",
        "lpcOutfit",
        "lpcBottom",
        "lpcShoes",
        "aura",
        "effect",
        "vehicle",
        "pet",
        "speech",
        "pose",
    ):
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
    assert 'this.load.spritesheet("lpc-pets"' in phaser_script
    assert "carrot-forest-lpc-pets-v1.png" in phaser_script


def test_lpc_avatar_expansion_storage_reward_and_sit_toggle_contract() -> None:
    game_script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    phaser_script = (ROOT / "src/frontend/forest-phaser.js").read_text(encoding="utf-8")
    engine = (ROOT / "src/frontend/lpc-avatar-engine.js").read_text(encoding="utf-8")
    manifest = (ROOT / "src/frontend/assets/lpc-pack/manifest.json").read_text(encoding="utf-8")
    worker = (ROOT / "src/frontend/forest-sw.js").read_text(encoding="utf-8")

    for category in ("bodyType", "face", "lpcExpression", "lpcEyebrow", "lpcNose", "lpcEyes", "lpcWrinkles"):
        assert f'id: "{category}"' in game_script
    assert "selected-check" in game_script
    assert "action-view-only" in game_script
    assert "storageObjectCodes" in game_script
    assert 'reward_cow: { name: "행운의 젖소"' in game_script
    assert 'reward_cow: { name: "행운의 젖소", kind: "object"' in game_script
    assert 'const rewardPool = ["reward_cow"]' in game_script
    assert "희귀 꾸미기 오브젝트" in game_script
    assert 'state.rewardClaimed && !state.inventory.includes("reward_cow")' in game_script
    assert 'name: "세준"' in game_script
    assert "event.repeat" in phaser_script
    assert "this.add.ellipse(0, 0" in phaser_script
    assert "pendingImages" in engine
    assert '"category": "expression"' in manifest
    for asset in (
        "carrot-forest-storage-atlas-v2.png",
        "carrot-forest-reward-cow-v1.png",
        "carrot-forest-lpc-pets-v1.png",
    ):
        assert (ROOT / "src/frontend/assets" / asset).is_file()
    assert "gold_eyes_orange_cat" in phaser_script
    assert "Phaser.Scale.FIT" in phaser_script
    assert "gandang-carrot-forest-pwa-v40" in worker


def test_face_editor_outfit_expansion_and_polish_contract() -> None:
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    game_script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    phaser_script = (ROOT / "src/frontend/forest-phaser.js").read_text(encoding="utf-8")
    engine = (ROOT / "src/frontend/lpc-avatar-engine.js").read_text(encoding="utf-8")
    css = (ROOT / "src/frontend/forest-game.css").read_text(encoding="utf-8")
    worker = (ROOT / "src/frontend/forest-sw.js").read_text(encoding="utf-8")

    assert 'id="face-section-tabs"' in html
    for label in ("얼굴형", "표정", "눈", "특수 눈", "눈썹", "코", "입", "주름"):
        assert f'label: "{label}"' in game_script
    assert 'lpcHair: ["hair", 24]' in game_script
    assert 'lpcOutfit: ["outfit", 20]' in game_script
    assert 'lpcBottom: ["bottom", 15]' in game_script
    assert 'lpcShoes: ["shoes", 12]' in game_script
    assert "drawFaceDetails" in engine
    assert "KeyCodes.SPACE" in phaser_script
    assert "time - this.lastPetAttackAt > 1600" in phaser_script
    assert "window.setInterval(playStep, 1080)" in game_script
    assert "storage-reward-cow" in game_script
    assert ".face-section-tabs" in css
    assert ".reward-rays,.reward-particles{display:none}" in css
    assert "/static/assets/lpc-pack/manifest.json" in worker
    assert "/static/lpc-avatar-engine.js" in html
    assert "/static/avatar-compositor.js" in html
    assert "CarrotAvatarCompositor" in phaser_script
    assert "const NAMEPLATE_Y = -126" in phaser_script
    assert "const AVATAR_RENDER_SCALE = 0.43" in phaser_script
    assert (ROOT / "src/frontend/vendor/phaser-3.90.0.min.js").stat().st_size > 1_000_000
    assert (ROOT / "src/frontend/vendor/PHASER_LICENSE.txt").exists()


def test_lpc_actions_and_pet_companion_motion_are_connected() -> None:
    import json

    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    game_script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    phaser_script = (ROOT / "src/frontend/forest-phaser.js").read_text(encoding="utf-8")
    engine_script = (ROOT / "src/frontend/lpc-avatar-engine.js").read_text(encoding="utf-8")
    manifest_path = ROOT / "src/frontend/assets/lpc-pack/manifest.json"
    credits_path = ROOT / "src/frontend/assets/lpc-pack/credits.json"

    assert manifest_path.exists()
    assert credits_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["items"]) >= 24
    for action in ("harvest", "fishing", "door", "attack", "dance"):
        assert action in engine_script
    for key_label in ("공격", "댄스"):
        assert key_label in html
    assert "playTogether" in phaser_script
    assert "this.petTrail" in phaser_script
    assert "time - 330" in phaser_script
    assert "this.petFacing" in phaser_script
    assert 'this.petAction = nextAvatar.sitting ? "sit" : "idle"' in phaser_script
    assert 'event.key === "0"' in game_script


def test_wild_rat_is_a_separate_attack_reward_event() -> None:
    game_script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    phaser_script = (ROOT / "src/frontend/forest-phaser.js").read_text(encoding="utf-8")
    worker = (ROOT / "src/frontend/forest-sw.js").read_text(encoding="utf-8")
    pet_builder = (ROOT / "scripts/build_lpc_pet_pack.py").read_text(encoding="utf-8")

    assert 'this.load.spritesheet("lpc-rat"' in phaser_script
    assert "spawnRat(time)" in phaser_script
    assert "tryAttackRat(time)" in phaser_script
    assert 'pose === "attack"' in phaser_script
    assert 'new CustomEvent("forest-rat-caught"' in phaser_script
    assert 'window.addEventListener("forest-rat-caught"' in game_script
    assert "state.carrots += amount" in game_script
    assert "야생 쥐를 잡고 당근" in game_script
    assert "RAT_OUTPUT" in pet_builder
    assert "carrot-forest-lpc-rat-v1.png" in worker
    assert (ROOT / "src/frontend/assets/carrot-forest-lpc-rat-v1.png").is_file()
    assert 'id: "rat"' not in game_script


def test_completed_challenges_grow_harvestable_carrots_in_the_garden() -> None:
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    game_script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")

    for control_id in ("garden-harvest-panel", "pending-harvest-carrots", "harvest-challenge-carrots"):
        assert f'id="{control_id}"' in html
    for contract in (
        "challengeCarrotClaims",
        "pendingChallengeCarrots",
        "accrueChallengeCarrots",
        "harvestChallengeCarrots",
        'data-world-action="harvest_challenge"',
    ):
        assert contract in game_script
    assert "if (state.challengeCarrotClaims?.[questId]) return 0" in game_script
    assert "if (!claim.harvested) claim.harvested = true" in game_script


def test_arcade_controls_pet_feeding_and_pet_auto_attack_are_connected() -> None:
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    game_script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    phaser_script = (ROOT / "src/frontend/forest-phaser.js").read_text(encoding="utf-8")

    assert "arcade-deck" in html
    assert 'data-action="feed"' in html
    assert "async function feedPet" in game_script
    assert 'new CustomEvent("forest-pet-fed"' in game_script
    assert "showPetHeart" in phaser_script
    assert "autoHunting" in phaser_script
    assert 'source: "pet"' in phaser_script
    assert 'this.premiumAvatar = this.add.image(0, 0, "avatar-composite").setOrigin(0.5, 0.87)' in phaser_script


def test_lpc_defaults_include_visible_face_and_gender_specific_starters() -> None:
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    game_script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    engine_script = (ROOT / "src/frontend/lpc-avatar-engine.js").read_text(encoding="utf-8")

    assert 'value="lpc_male_default"' in html
    assert 'value="lpc_female_default"' in html
    assert 'lpcExpression: "neutral"' in game_script
    assert "cosmeticSchemaVersion: 3" in game_script
    assert 'lpcNose: "button"' in game_script
    assert '["body", "body", "body", cosmetics.skin || "peach"]' in engine_script
    assert "skinPalettes" in engine_script
    assert "faceAnchors" in engine_script
    assert "drawEye" in engine_script
    assert "drawMouth" in engine_script
    assert 'if (direction === "up") return' in engine_script
    assert 'const palette = skinPalettes[cosmetics.skin] || skinPalettes.peach' in engine_script


def test_avatar_sitting_is_a_stable_toggle_and_clothing_catalog_is_expanded() -> None:
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")
    game_script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    engine_script = (ROOT / "src/frontend/lpc-avatar-engine.js").read_text(encoding="utf-8")

    assert 'data-action="sit"' in html
    assert "state.avatar.sitting = !state.avatar.sitting" in game_script
    assert "avatar.sitting && !options.pose" in engine_script
    assert "cycles[cycles.length - 1]" in engine_script
    assert 'lpcOutfit: ["outfit", 20]' in game_script
    assert 'lpcBottom: ["bottom", 15]' in game_script


def test_attack_effects_use_matching_lpc_motion() -> None:
    engine_script = (ROOT / "src/frontend/lpc-avatar-engine.js").read_text(encoding="utf-8")

    assert 'if (effect === "magic_burst") return "spellcast"' in engine_script
    assert 'if (effect === "arrow_volley") return "shoot"' in engine_script
    assert 'if (effect === "leaf_blade") return "thrust"' in engine_script
    assert 'return "slash"' in engine_script


def test_local_daily_reset_preserves_profile_but_reopens_daily_reward() -> None:
    game_script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")

    assert "function resetTodayProgress(current)" in game_script
    assert 'next.quests = { walk: false, meal: false, check: false }' in game_script
    assert "next.rewardClaimed = false" in game_script
    assert "completed: member.me ? 0 : 3" in game_script
    assert 'localDemoOrigin && params.get("resetToday") === "1"' in game_script


def test_modular_avatar_separates_the_base_body_from_hair_layers() -> None:
    compositor = (ROOT / "src/frontend/avatar-compositor.js").read_text(encoding="utf-8")
    html = (ROOT / "src/frontend/forest.html").read_text(encoding="utf-8")

    assert "const BASE_BODY_START = 146" in compositor
    assert 'const backHairPresets = new Set(["red_bow"])' in compositor
    assert "bodyTarget.y + target.height * BASE_BODY_START / CELL_HEIGHT" in compositor
    assert "if (usesBackHair) drawSource(context, source.image, hair, hairTarget)" in compositor
    assert "drawSource(context, source.image, outfit, bodyTarget)" in compositor
    assert "기본 몸 높이" in html


def test_each_preset_uses_directional_walk_and_vehicle_motion_in_world() -> None:
    compositor = (ROOT / "src/frontend/avatar-compositor.js").read_text(encoding="utf-8")
    phaser = (ROOT / "src/frontend/forest-phaser.js").read_text(encoding="utf-8")

    assert "drawPresetMotionFrame" in compositor
    assert "options.moving || options.mounted || options.motionPreview" in compositor
    assert "options.hairPreset === options.preset" in compositor
    assert "options.outfitPreset === options.preset" in compositor
    assert "const mountedBounce" in compositor
    assert "const horizontalLean" in compositor
    assert "playMountTransition" in phaser
    assert "this.mountTransitioning" in phaser
    assert "drawMotionEffects" in phaser
    assert "this.avatar.mounted" in phaser


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


def test_looping_animated_objects_are_buildable_placeable_and_cached() -> None:
    import struct

    atlas = ROOT / "src/frontend/assets/carrot-forest-animated-objects-v1.png"
    raw = atlas.read_bytes()
    width, height = struct.unpack(">II", raw[16:24])
    game_script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    phaser_script = (ROOT / "src/frontend/forest-phaser.js").read_text(encoding="utf-8")
    css = (ROOT / "src/frontend/forest-game.css").read_text(encoding="utf-8")
    worker = (ROOT / "src/frontend/forest-sw.js").read_text(encoding="utf-8")

    assert (width, height) == (512, 512)
    assert (ROOT / "scripts/build_animated_object_atlas.py").is_file()
    for code in ("duck_float", "animated_fountain", "firefly_lantern", "garden_pinwheel"):
        assert code in game_script
        assert code in phaser_script
    assert 'new CustomEvent("forest-world-pointer"' in phaser_script
    assert 'window.addEventListener("forest-world-pointer"' in game_script
    assert 'this.load.spritesheet("animated-objects"' in phaser_script
    assert "repeat: -1" in phaser_script
    assert "syncPlacedObjects" in phaser_script
    assert "animated-object-thumb" in css
    assert "carrot-forest-animated-objects-v1.png" in worker


def test_storage_objects_use_isolated_cells_and_recent_outfit_wardrobe() -> None:
    import struct

    atlas = ROOT / "src/frontend/assets/carrot-forest-storage-atlas-v3.png"
    raw = atlas.read_bytes()
    width, height = struct.unpack(">II", raw[16:24])
    game_script = (ROOT / "src/frontend/forest-game.js").read_text(encoding="utf-8")
    phaser_script = (ROOT / "src/frontend/forest-phaser.js").read_text(encoding="utf-8")
    css = (ROOT / "src/frontend/forest-game.css").read_text(encoding="utf-8")

    assert (width, height) == (256 * 5, 256 * 4)
    assert (ROOT / "scripts/build_storage_object_atlas.py").is_file()
    assert 'this.load.spritesheet("storage-objects"' in phaser_script
    assert "storageObjectIndex" in phaser_script
    assert 'item.code === "reward_cow"' in phaser_script
    assert "outfitHistory" in game_script
    assert "rememberCurrentOutfit" in game_script
    assert "applyOutfitLook" in game_script
    assert "data-outfit-look" in game_script
    assert "inventory: [...storageObjectCodes]" in game_script
    assert "carrot-forest-storage-atlas-v3.png" in css
