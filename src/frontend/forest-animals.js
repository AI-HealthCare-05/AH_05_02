/* Downloaded LPC animal frames. See assets/animals/ATTRIBUTION.md for source licenses. */
((root) => {
  "use strict";
  const directory = "/static/assets/animals/";
  const assets = Object.freeze([
    Object.freeze({ key: "forest-cow-eat", url: `${directory}lpc-cow-eat.png`, frameWidth: 128, frameHeight: 128 }),
    Object.freeze({ key: "forest-cow-walk", url: `${directory}lpc-cow-walk.png`, frameWidth: 128, frameHeight: 128 }),
    Object.freeze({ key: "forest-rabbit", url: `${directory}lpc-rabbit.png`, frameWidth: 72, frameHeight: 72 }),
  ]);
  // Optional creator-licensed packs are installed locally, not redistributed in
  // Git. Original 32px source cells are used without repainting or deformation.
  const rabbitAssets = Object.freeze([
    Object.freeze({ key: "forest-rabbit-bunbun", url: `${directory}licensed-rabbits/bunbun.png?v=20260908-1`, frameWidth: 32, frameHeight: 32, columns: 4, frameCount: 32 }),
    Object.freeze({ key: "forest-rabbit-last-tick", url: `${directory}licensed-rabbits/last-tick.png?v=20260908-1`, frameWidth: 32, frameHeight: 32, columns: 11, frameCount: 374 }),
  ]);
  const action = (name, label, frames, frameMs, options = {}) => Object.freeze({
    name, label, frames: Object.freeze(frames), frameMs,
    durationMs: frames.length * frameMs * (options.repeats || 1),
    loop: (options.repeats || 1) > 1, moves: false, ...options,
  });
  const bunbunActions = [
    action("idle", "가만히 쉬기", [0, 2], 350, { repeats: 3 }),
    action("jump_up", "제자리 점프", [4, 6], 170, { repeats: 2 }),
    action("jump_forward", "앞으로 뛰기", [10, 11], 170, { repeats: 2, moves: true, direction: "right" }),
    action("jump_front", "정면으로 뛰기", [8, 9], 170, { repeats: 2, moves: true, direction: "down" }),
    action("jump_back", "뒤로 뛰기", [12, 13], 170, { repeats: 2, moves: true, direction: "up" }),
    action("kick", "뒷발 차기", [16, 18], 170, { repeats: 2 }),
    action("sleep", "잠자기", [20, 22], 450, { repeats: 4 }),
    action("dig", "땅 파고 나오기", [24, 25, 26, 27], 150, { repeats: 2 }),
  ];
  // The Last tick ASEPRITE is a single canvas without animation tags. These
  // names and timings are application-authored, verified against the artwork.
  const directions = ["down", "up", "left", "right", "down_left", "down_right", "up_right", "up_left"];
  const directionLabels = ["앞", "뒤", "왼쪽", "오른쪽", "왼쪽 앞", "오른쪽 앞", "오른쪽 뒤", "왼쪽 뒤"];
  const restNames = ["stretched_left", "stretched_right", "loaf_left", "loaf_right", "flat_left", "flat_right"];
  const restLabels = ["왼쪽으로 몸 펴기", "오른쪽으로 몸 펴기", "왼쪽으로 웅크리기", "오른쪽으로 웅크리기", "왼쪽으로 누워 쉬기", "오른쪽으로 누워 쉬기"];
  const rowFrames = (row, count) => Array.from({ length: count }, (_, column) => row * 11 + column);
  const lastTickActions = [
    ...directions.map((direction, i) => action(`pose_${direction}`, `${directionLabels[i]} 바라보기`, [i], 550, { direction })),
    ...restNames.map((name, i) => action(`pose_${name}`, restLabels[i], [11 + i], 550, { direction: i % 2 ? "right" : "left" })),
    ...["down", "up", "right", "left", "down_left", "down_right", "up_right", "up_left"].map((direction, i) =>
      action(`hop_${direction}`, `${directionLabels[directions.indexOf(direction)]} 방향으로 뛰기`, rowFrames(2 + i, 6), 140, { moves: true, direction })),
    ...restNames.map((name, i) => action(`rest_${name}`, `${restLabels[i]} · 숨쉬기`, rowFrames(10 + i, 2), 350, { direction: i % 2 ? "right" : "left" })),
    ...directions.map((direction, i) => action(`head_lower_${direction}`, `${directionLabels[i]} · 고개 숙이기`, rowFrames(16 + i, 9), 120, { direction })),
    action("look_around", "두리번거리기", rowFrames(24, 9), 120, { direction: "down" }),
    action("upright_bob", "몸 세우기", rowFrames(25, 4), 140, { direction: "down" }),
    ...[8, 5, 6, 8, 5, 6].map((count, i) => action(`ear_flick_${i + 1}`, `${i < 3 ? "앞" : "뒤"} · 귀 움직이기 ${i % 3 + 1}`, rowFrames(26 + i, count), 110, { direction: i < 3 ? "down" : "up" })),
    action("head_tilt_1", "고개 기울이고 몸단장 1", rowFrames(32, 11), 110, { direction: "down" }),
    action("head_tilt_2", "고개 기울이고 몸단장 2", rowFrames(33, 11), 110, { direction: "down" }),
  ];
  const rabbitActionSets = Object.freeze({ bunbun: Object.freeze(bunbunActions), "last-tick": Object.freeze(lastTickActions) });
  const rabbitOriginals = [
    { id: "bunbun", key: rabbitAssets[0].key, label: "Bunbun 얼룩토끼", actions: Object.freeze(bunbunActions.map(item => item.name)) },
    { id: "last-tick", key: rabbitAssets[1].key, label: "Last tick 회색토끼", actions: Object.freeze(lastTickActions.map(item => item.name)) },
  ];
  // Game-authored runtime palettes, NOT additional downloads from the creators.
  // Only verified fur colors change. Eyes/outlines, pink ears, carrots and alpha
  // keep their exact original bytes in every source animation cell.
  const rabbitFurColors = {
    bunbun: [0x6f6f6f, 0x8e8e8e, 0xa3a3a3, 0xb3b3b3, 0xdddddd],
    "last-tick": [0x414752, 0x626773, 0x868d9b, 0xb6b8c7],
  };
  const rabbitColors = [
    ["bunbun", "cream", "Bunbun 크림토끼", [0x887257, 0xb99d71, 0xd8bd8c, 0xe5cfa7, 0xf6e7ca]],
    ["bunbun", "brown", "Bunbun 갈색토끼", [0x5a3a2d, 0x73503b, 0xa7744e, 0xb98a61, 0xe4c4a0]],
    ["bunbun", "black", "Bunbun 검정토끼", [0x29313a, 0x364047, 0x485261, 0x657179, 0x9aa3aa]],
    ["last-tick", "white", "Last tick 흰토끼", [0x87909a, 0xced3d5, 0xe4e8e4, 0xfffff7]],
    ["last-tick", "cream", "Last tick 크림토끼", [0x8e7864, 0xd8b588, 0xedcfa5, 0xfff0cf]],
    ["last-tick", "brown", "Last tick 갈색토끼", [0x5f4034, 0xa67148, 0xc19465, 0xe5c394]],
  ];
  const rabbitVariants = Object.freeze([
    ...rabbitOriginals.map(item => Object.freeze({ ...item, family: item.id, sourceKey: item.key, scale: 1.4, generated: false })),
    ...rabbitColors.map(([family, color, label, palette]) => {
      const source = rabbitOriginals.find(item => item.id === family);
      return Object.freeze({ id: `${family}-${color}`, key: `forest-rabbit-${family}-${color}`, sourceKey: source.key,
        family, color, label, scale: 1.4, generated: true, actions: source.actions,
        palette: Object.freeze(Object.fromEntries(rabbitFurColors[family].map((rgb, index) => [rgb, palette[index]]))) });
    }),
  ]);

  function recolorRabbitPixels(pixels, variantId) {
    if (!pixels || pixels.length % 4) throw new Error("Rabbit pixels must be RGBA.");
    const copy = new Uint8ClampedArray(pixels);
    const palette = rabbitVariants.find(item => item.id === variantId)?.palette;
    if (!palette) return copy;
    for (let index = 0; index < copy.length; index += 4) {
      if (!copy[index + 3]) continue;
      const replacement = palette[(copy[index] << 16) | (copy[index + 1] << 8) | copy[index + 2]];
      if (replacement === undefined) continue;
      copy[index] = replacement >>> 16; copy[index + 1] = (replacement >>> 8) & 255; copy[index + 2] = replacement & 255;
    }
    return copy;
  }

  function createRabbitSkinCanvas(source, variantId) {
    const variant = rabbitVariants.find(item => item.id === variantId);
    const asset = rabbitAssets.find(item => item.key === variant?.sourceKey);
    const width = source?.naturalWidth || source?.width, height = source?.naturalHeight || source?.height;
    if (!asset || width !== asset.columns * asset.frameWidth || height !== asset.frameCount / asset.columns * asset.frameHeight) return null;
    const canvas = root.document.createElement("canvas"); canvas.width = width; canvas.height = height;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    context.drawImage(source, 0, 0);
    if (variant.generated) {
      const pixels = context.getImageData(0, 0, width, height);
      pixels.data.set(recolorRabbitPixels(pixels.data, variantId));
      context.putImageData(pixels, 0, 0);
    }
    return canvas;
  }

  function registerRabbitSkins(scene) {
    const installed = [];
    for (const variant of rabbitVariants.filter(item => item.generated)) {
      if (scene.textures.exists(variant.key)) { installed.push(variant.key); continue; }
      if (!scene.textures.exists(variant.sourceKey)) continue;
      try {
        const canvas = createRabbitSkinCanvas(scene.textures.get(variant.sourceKey).getSourceImage(), variant.id);
        if (!canvas) continue;
        scene.textures.addSpriteSheet(variant.key, canvas, { frameWidth: 32, frameHeight: 32 });
        installed.push(variant.key);
      } catch { /* Optional palette preparation must not block the original rabbits or game boot. */ }
    }
    return installed;
  }

  function rabbitAction(id, name) {
    const family = rabbitVariants.find(item => item.id === id)?.family;
    return rabbitActionSets[family]?.find(item => item.name === name) || null;
  }

  function rabbitPose(id, { action: name, direction = "right", elapsedMs = 0, reducedMotion = false } = {}) {
    const variant = rabbitVariants.find(item => item.id === id);
    if (!variant) return null;
    const selected = rabbitAction(id, name) || rabbitActionSets[variant.family][0];
    const time = Number.isFinite(elapsedMs) ? Math.max(0, elapsedMs) : 0;
    const done = time >= selected.durationMs;
    const index = reducedMotion ? 0 : done ? selected.frames.length - 1 : Math.floor(time / selected.frameMs) % selected.frames.length;
    // Bunbun side poses face right. Front/back and digging have their own art.
    const sidePose = variant.family === "bunbun" && !["jump_front", "jump_back", "dig"].includes(selected.name);
    return {
      key: variant.key, frame: selected.frames[index], originX: 0.5, originY: 1,
      scale: variant.scale, flipX: sidePose && direction.includes("left"), done,
    };
  }
  const rows = Object.freeze({ up: 0, left: 1, down: 2, right: 3 });
  const cowFootY = Object.freeze([110 / 128, 88 / 128, 102 / 128, 88 / 128]);
  const reactionColumns = Object.freeze([0, 1, 2, 3, 3, 2, 1, 0]);
  const cowReactionFrameMs = 170;
  const cowReactionDurationMs = reactionColumns.length * cowReactionFrameMs;
  const mooUrl = `${directory}cow-moo-joseph-sardin-cc0.mp3`;

  function directionRow(direction, fallback = "down") {
    return Object.hasOwn(rows, direction) ? rows[direction] : rows[fallback];
  }

  // A negative/missing elapsed time is a genuinely still animal. It never advances
  // frames on its own. A finite touch reaction returns to exactly the same pose.
  function cowFrame(elapsedMs = -1, { direction = "left", reducedMotion = false } = {}) {
    const row = directionRow(direction, "left");
    const reacting = Number.isFinite(elapsedMs) && elapsedMs >= 0 && elapsedMs < cowReactionDurationMs;
    const column = reacting && !reducedMotion ? reactionColumns[Math.floor(elapsedMs / cowReactionFrameMs)] : 0;
    return {
      key: "forest-cow-eat", frame: row * 4 + column, done: !reacting,
      originX: 0.5, originY: cowFootY[row],
    };
  }

  // Live cows own this immutable, scene-local clock. The saved furniture anchor
  // never moves, and the legacy cowFrame above remains the photo/thumbnail API.
  const cowBehavior = Object.freeze({
    idleMinMs: 12000, idleMaxMs: 22000, maxDeltaMs: 50, touchDebounceMs: 250,
    grazeMs: 3200, headMs: 1050, bodyMs: 840,
  });
  const cowGrazeFrames = Object.freeze([4, 5, 6, 7, 6, 7, 6, 5, 4]);
  const cowGrazeEnds = Object.freeze([250, 650, 1100, 1450, 1800, 2150, 2550, 2900, 3200]);
  const cowBodyFrames = Object.freeze([4, 5, 6, 7, 4]);
  const cowBodyEnds = Object.freeze([170, 340, 510, 680, 840]);
  const cowActions = new Set(["idle", "graze", "head", "body"]);

  function nextCowRandom(state) {
    let value = state.rng >>> 0 || 0x9e3779b9;
    value ^= value << 13; value ^= value >>> 17; value ^= value << 5;
    state.rng = value >>> 0;
    return state.rng / 4294967296;
  }

  function restCow(state) {
    state.action = "idle"; state.elapsedMs = 0; state.liftFromColumn = 0;
    state.waitMs = cowBehavior.idleMinMs
      + Math.floor(nextCowRandom(state) * (cowBehavior.idleMaxMs - cowBehavior.idleMinMs + 1));
    return state;
  }

  function createCowState(anchor = {}) {
    const anchorX = Number.isFinite(anchor.x) ? anchor.x : 0;
    const anchorY = Number.isFinite(anchor.y) ? anchor.y : 0;
    const seed = Number.isFinite(anchor.seed) ? anchor.seed >>> 0
      : (Math.imul(Math.round(anchorX * 100), 73856093) ^ Math.imul(Math.round(anchorY * 100), 19349663)) >>> 0;
    return Object.freeze(restCow({ anchorX, anchorY, seed, rng: seed || 0x9e3779b9,
      action: "idle", elapsedMs: 0, waitMs: 0, liftFromColumn: 0 }));
  }

  function copyCowState(state) {
    if (!state || !Number.isFinite(state.anchorX) || !Number.isFinite(state.anchorY)
      || !Number.isFinite(state.rng) || !Number.isFinite(state.elapsedMs) || state.elapsedMs < 0
      || !Number.isFinite(state.waitMs) || state.waitMs < cowBehavior.idleMinMs
      || state.waitMs > cowBehavior.idleMaxMs || !cowActions.has(state.action)) {
      return { ...createCowState({ x: state?.anchorX ?? state?.x, y: state?.anchorY ?? state?.y, seed: state?.seed }) };
    }
    return { ...state };
  }

  function cowActionDuration(actionName) {
    return { graze: cowBehavior.grazeMs, head: cowBehavior.headMs, body: cowBehavior.bodyMs }[actionName] || 0;
  }

  function updateCowState(previous, deltaMs, { hidden = false, reducedMotion = false } = {}) {
    const state = copyCowState(previous);
    if (hidden) return Object.freeze(state);
    if (reducedMotion) {
      // Discard interrupted actions instead of playing a delayed reaction when
      // the motion preference is changed back. Quiet idle clocks stay paused.
      if (state.action !== "idle") restCow(state);
      return Object.freeze(state);
    }
    const delta = Number.isFinite(deltaMs) ? Math.max(0, Math.min(cowBehavior.maxDeltaMs, deltaMs)) : 0;
    if (!delta) return Object.freeze(state);
    state.elapsedMs += delta;
    if (state.action === "idle" && state.elapsedMs >= state.waitMs) {
      state.action = "graze"; state.elapsedMs -= state.waitMs;
    } else if (state.action !== "idle" && state.elapsedMs >= cowActionDuration(state.action)) restCow(state);
    return Object.freeze(state);
  }

  function touchCowState(previous, reaction = "body", { hidden = false, reducedMotion = false } = {}) {
    const state = copyCowState(previous);
    if (hidden) return Object.freeze(state); // No queued indoor/hidden click.
    if (reducedMotion) return Object.freeze(restCow(state));
    const nextAction = reaction === "head" ? "head" : "body";
    const alreadyReacting = state.action === "head" || state.action === "body";
    // Same-reaction spam cannot keep the animal reacting indefinitely. A
    // different touch may replace it only after the initial debounce window.
    if (alreadyReacting && (state.elapsedMs < cowBehavior.touchDebounceMs || state.action === nextAction)) return Object.freeze(state);
    const previousPose = cowPose(state);
    state.liftFromColumn = previousPose.key === "forest-cow-eat" && previousPose.frame >= 4 && previousPose.frame <= 7
      ? previousPose.frame - 4 : 0;
    state.action = nextAction; state.elapsedMs = 0;
    return Object.freeze(state);
  }

  function cowPose(previous, { reducedMotion = false } = {}) {
    const state = copyCowState(previous);
    const actionName = reducedMotion || (state.action !== "idle" && state.elapsedMs >= cowActionDuration(state.action))
      ? "idle" : state.action;
    let key = "forest-cow-eat", frame = 4, row = rows.left;
    if (actionName === "graze") {
      const index = cowGrazeEnds.findIndex(end => state.elapsedMs < end);
      frame = cowGrazeFrames[index < 0 ? cowGrazeFrames.length - 1 : index];
    } else if (actionName === "head") {
      const from = Number.isFinite(state.liftFromColumn) ? Math.max(0, Math.min(3, Math.floor(state.liftFromColumn))) : 0;
      if (state.elapsedMs < 300) {
        // Lift from the interrupted grazing frame, never lower the head again.
        frame = 4 + Math.max(0, from - (Math.floor(state.elapsedMs / 100) + 1));
      } else if (state.elapsedMs < 750) {
        key = "forest-cow-walk"; frame = 8; row = rows.down;
      } else key = "forest-cow-walk";
    } else if (actionName === "body") {
      key = "forest-cow-walk";
      const index = cowBodyEnds.findIndex(end => state.elapsedMs < end);
      frame = cowBodyFrames[index < 0 ? cowBodyFrames.length - 1 : index];
    }
    return Object.freeze({ key, frame, originX: .5, originY: cowFootY[row],
      action: actionName, moving: false, done: actionName === "idle" });
  }

  // The sheet contains the natural hop displacement already. Do not add a sine
  // bounce or stretch the body. Lower rows are the source's grazing poses.
  function rabbitFrame(direction = "down", moving = false, elapsedMs = 0, reducedMotion = false) {
    const row = directionRow(direction);
    const time = Number.isFinite(elapsedMs) ? Math.max(0, elapsedMs) : 0;
    const column = reducedMotion ? 0 : Math.floor(time / (moving ? 140 : 330)) % 4;
    return {
      key: "forest-rabbit", frame: (moving ? row : row + 4) * 4 + column,
      originX: 0.5, originY: 51 / 72,
    };
  }

  function frameRect(key, frame) {
    const sourceKey = rabbitVariants.find(item => item.key === key)?.sourceKey || key;
    const asset = assets.find(item => item.key === sourceKey) || rabbitAssets.find(item => item.key === sourceKey);
    const frameCount = asset?.frameCount || (key === "forest-rabbit" ? 32 : 16);
    if (!asset || !Number.isInteger(frame) || frame < 0 || frame >= frameCount) return null;
    const columns = asset.columns || 4;
    return {
      x: (frame % columns) * asset.frameWidth, y: Math.floor(frame / columns) * asset.frameHeight,
      width: asset.frameWidth, height: asset.frameHeight,
    };
  }

  let moo = null;
  let lastMooAt = -Infinity;
  function playMoo({ enabled = true, volume = 0.32, nowMs = Date.now() } = {}) {
    if (!enabled || typeof root.Audio !== "function" || nowMs - lastMooAt < 1400) return false;
    lastMooAt = nowMs;
    if (!moo) {
      moo = new root.Audio(mooUrl);
      moo.preload = "none";
    }
    const safeVolume = Number.isFinite(volume) ? Math.max(0, Math.min(1, volume)) : 0.32;
    moo.pause();
    moo.currentTime = 0;
    moo.volume = safeVolume;
    try {
      const playing = moo.play();
      if (playing && typeof playing.catch === "function") playing.catch(() => {});
    } catch {
      return false;
    }
    return true;
  }

  const api = Object.freeze({ assets, rabbitAssets, rabbitVariants, rabbitAction, rabbitPose, cowFrame,
    recolorRabbitPixels, createRabbitSkinCanvas, registerRabbitSkins,
    createCowState, updateCowState, touchCowState, cowPose, cowBehavior,
    rabbitFrame, frameRect, mooUrl, playMoo, cowReactionDurationMs });
  root.ForestAnimals = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof window === "object" ? window : globalThis);
