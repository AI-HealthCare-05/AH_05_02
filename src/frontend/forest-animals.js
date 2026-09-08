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
  const rabbitVariants = Object.freeze([
    Object.freeze({ id: "bunbun", key: rabbitAssets[0].key, label: "Bunbun", scale: 1.4, actions: Object.freeze(bunbunActions.map(item => item.name)) }),
    Object.freeze({ id: "last-tick", key: rabbitAssets[1].key, label: "Last tick", scale: 1.4, actions: Object.freeze(lastTickActions.map(item => item.name)) }),
  ]);

  function rabbitAction(id, name) {
    return rabbitActionSets[id]?.find(item => item.name === name) || null;
  }

  function rabbitPose(id, { action: name, direction = "right", elapsedMs = 0, reducedMotion = false } = {}) {
    const variant = rabbitVariants.find(item => item.id === id);
    if (!variant) return null;
    const selected = rabbitAction(id, name) || rabbitActionSets[id][0];
    const time = Number.isFinite(elapsedMs) ? Math.max(0, elapsedMs) : 0;
    const done = time >= selected.durationMs;
    const index = reducedMotion ? 0 : done ? selected.frames.length - 1 : Math.floor(time / selected.frameMs) % selected.frames.length;
    // Bunbun side poses face right. Front/back and digging have their own art.
    const sidePose = id === "bunbun" && !["jump_front", "jump_back", "dig"].includes(selected.name);
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
    const asset = assets.find(item => item.key === key) || rabbitAssets.find(item => item.key === key);
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

  const api = Object.freeze({ assets, rabbitAssets, rabbitVariants, rabbitAction, rabbitPose, cowFrame, rabbitFrame, frameRect, mooUrl, playMoo, cowReactionDurationMs });
  root.ForestAnimals = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof window === "object" ? window : globalThis);
