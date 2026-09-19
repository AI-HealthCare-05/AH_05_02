/* Last tick's official FREE kitten sheets + FREE winter/Valentine equipment.
 * Import locally with scripts/import_forest_kittens.ps1; do not redistribute
 * the source sheets separately. No source bitmap is recolored or deformed.
 * Source: https://last-tick.itch.io/animated-pixel-kittens-cats-32x32
 * Audit: the ASEPRITE is ONE 352x1696 canvas without animation tags. Rows below
 * are verified against the included "cat 16x16 with text.png", "Frame indexes.png",
 * and the nonempty original 32px cells (11 columns x 53 rows), not guessed tags.
 */
((root) => {
  "use strict";
  const COLUMNS = 11, ROWS = 53, FRAME_SIZE = 32, SCALE = 1.2;
  // One authored floor line for all actions/overlays; animation pixels already
  // contain natural gait movement. Never fit or rescale each individual pose.
  const ORIGIN = Object.freeze({ x: .5, y: 26 / 32 });
  const sourceSheets = Object.freeze([
    "white", "gray", "ginger",
    "winter-antlers-green", "winter-antlers-red", "winter-santa-hat-1", "winter-santa-hat-2",
    "valentine-cupid", "valentine-nimbus", "valentine-wings", "valentine-bow-blue",
    "valentine-bow-gold", "valentine-glasses-gold", "valentine-bow-green",
    "valentine-bow-pink-2", "valentine-bow-pink", "valentine-bow-red", "valentine-glasses-red",
  ]);
  const assets = Object.freeze(sourceSheets.map(name => Object.freeze({
    key: `forest-kitten-${name}`,
    url: `/static/assets/animals/licensed-kittens/${name}.png?v=20260908-2`,
    frameWidth: FRAME_SIZE, frameHeight: FRAME_SIZE, width: 352, height: 1696,
    columns: COLUMNS, rows: ROWS, frameCount: COLUMNS * ROWS,
  })));
  const catalog = Object.freeze([
    { id: "last_tick_white", name: "눈꽃 고양이", color: "white", fallbackColumn: 0 },
    { id: "last_tick_gray", name: "구름 고양이", color: "gray", fallbackColumn: 0 },
    { id: "last_tick_ginger", name: "살구 고양이", color: "ginger", fallbackColumn: 3 },
  ].map(item => Object.freeze({ ...item, key: `forest-kitten-${item.color}`, scale: SCALE, legacy: false, group: "고양이" })));
  const equipment = Object.freeze([
    { id: "none", name: "장비 없음", sheet: null },
    { id: "winter_antlers_green", name: "초록 사슴뿔 머리띠", sheet: "winter-antlers-green" },
    { id: "winter_antlers_red", name: "빨강 사슴뿔 머리띠", sheet: "winter-antlers-red" },
    { id: "winter_santa_hat_1", name: "산타 모자", sheet: "winter-santa-hat-1" },
    { id: "winter_santa_hat_2", name: "포근한 산타 모자", sheet: "winter-santa-hat-2" },
    { id: "valentine_cupid", name: "큐피드 의상", sheet: "valentine-cupid" },
    { id: "valentine_nimbus", name: "큐피드 후광", sheet: "valentine-nimbus" },
    { id: "valentine_wings", name: "큐피드 날개", sheet: "valentine-wings" },
    { id: "valentine_bow_blue", name: "파란 리본", sheet: "valentine-bow-blue" },
    { id: "valentine_bow_gold", name: "금빛 리본", sheet: "valentine-bow-gold" },
    { id: "valentine_glasses_gold", name: "금빛 하트 안경", sheet: "valentine-glasses-gold" },
    { id: "valentine_bow_green", name: "초록 리본", sheet: "valentine-bow-green" },
    { id: "valentine_bow_pink_2", name: "큰 분홍 리본", sheet: "valentine-bow-pink-2" },
    { id: "valentine_bow_pink", name: "분홍 리본", sheet: "valentine-bow-pink" },
    { id: "valentine_bow_red", name: "빨간 리본", sheet: "valentine-bow-red" },
    { id: "valentine_glasses_red", name: "빨간 하트 안경", sheet: "valentine-glasses-red" },
  ].map(item => Object.freeze({ ...item, key: item.sheet ? `forest-kitten-${item.sheet}` : null,
    slot: "petAccessory", itemId: item.id, group: "펫 장비" })));
  // Only authored animated pets are selectable. Old saved IDs remain readable
  // through a rendering alias; opening the menu never rewrites saved outfits.
  const aliases = Object.freeze({ white_pup: "lpc_brown_dog", brown_pup: "lpc_brown_dog",
    cat: "lpc_white_cat", fox: "lpc_orange_cat",
    blue_eyes_white_cat: "last_tick_white", gold_eyes_orange_cat: "last_tick_ginger",
    last_tick_ribbon: "last_tick_white" });
  const classicCatalog = Object.freeze([
    { id: "lpc_white_cat", name: "흰 고양이 · 보행", fallbackColumn: 0 },
    { id: "lpc_orange_cat", name: "주황 고양이 · 보행", fallbackColumn: 3 },
    { id: "lpc_brown_dog", name: "갈색 강아지 · 보행", fallbackColumn: 6 },
  ].map(item => Object.freeze({ ...item, key: "lpc-pets", scale: 1.2, legacy: true,
    supportsSit: false, group: "강아지", description: "기존 LPC · 네 방향 걷기" })));

  function canonicalId(id) {
    return Object.hasOwn(aliases, id) ? aliases[id] : id;
  }

  // Exact nonempty cell counts from the official original body PNGs. Preserve
  // this audited topology: trailing transparent cells are NOT animation frames.
  const rowFrameCounts = Object.freeze([6,8,6,10,4,4,8,8,6,6,6,6,2,2,2,2,2,2,2,2,
    8,8,8,8,8,8,8,8,3,3,3,3,8,8,8,8,9,9,7,11,11,2,2,1,9,5,7,7,9,9,5,5,4]);
  const walkRows = Object.freeze({ down: 4, up: 5, right: 6, left: 7, down_left: 8, down_right: 9, up_right: 10, up_left: 11 });
  const eatRows = Object.freeze({ down: 20, up: 21, left: 22, right: 23, down_right: 24, down_left: 25, up_right: 26, up_left: 27 });
  const pawRows = Object.freeze({ down: 44, up: 45, left: 46, right: 47, down_right: 48, down_left: 49, up_right: 50, up_left: 51 });
  const sitColumns = Object.freeze({ down: 0, up: 1, left: 2, right: 3, down_left: 4, down_right: 5, up_left: 1, up_right: 1 });
  const actionDurations = Object.freeze({ idle: Infinity, sit: Infinity, walk: Infinity, feed: 1280, attack: 760 });
  // Official labels: row28 "meow sit" (3 cells), row32 "yawn sit" (8),
  // row36 "wash sit" (9). All are genuinely seated original body frames.
  // Quiet rests dominate a 12s cycle; the first short movement starts at 1.6s
  // so a brief pause is not indistinguishable from a frozen decorative sprite.
  const idleClips = Object.freeze([
    Object.freeze({ name: "meow_sit", row: 28, startMs: 1600, frameMs: 160 }),
    Object.freeze({ name: "yawn_sit", row: 32, startMs: 3800, frameMs: 150 }),
    Object.freeze({ name: "wash_sit", row: 36, startMs: 7200, frameMs: 140 }),
  ]);
  const IDLE_CYCLE_MS = 10000;
  const idleStages = Object.freeze([
    Object.freeze({ name: "sit", thresholdMs: 10000, static: true }),
    Object.freeze({ name: "paws_tucked", thresholdMs: 30000, rowDown: 12, rowRight: 13, frameMs: 850 }),
    Object.freeze({ name: "sleep_sitting", thresholdMs: 60000, rowDown: 14, rowRight: 15, frameMs: 900 }),
    Object.freeze({ name: "sleep_head_down", thresholdMs: 90000, rowDown: 16, rowRight: 17, frameMs: 950 }),
    Object.freeze({ name: "sleep_stretched", thresholdMs: 120000, rowDown: 18, rowRight: 19, frameMs: 1000 }),
  ]);
  const actions = Object.freeze({
    idle: Object.freeze({ label: "시간에 따라 쉬기", description: "10초 앉기부터 2분 쭉 뻗어 자기까지 원본 휴식 프레임을 단계별 사용", sourceRows: Object.freeze([0, 12, 13, 14, 15, 16, 17, 18, 19, 28, 32, 36]) }),
    sit: Object.freeze({ label: "앉아 쉬기", description: "실제 앉은 자세와 짧은 앉은 대기 동작", sourceRows: Object.freeze([0, 28, 32, 36]) }),
    walk: Object.freeze({ label: "따라 걷기", description: "이동 방향에 맞는 여덟 방향 원본 보행", sourceRows: Object.freeze([4, 5, 6, 7, 8, 9, 10, 11]) }),
    feed: Object.freeze({ label: "간식 먹기", description: "1280ms 동안 원본 먹기 동작 후 다시 앉기", sourceRows: Object.freeze([20, 21, 22, 23, 24, 25, 26, 27]), durationMs: 1280 }),
    attack: Object.freeze({ label: "앞발 내밀기", description: "760ms 동안 방향별 원본 앞발 동작 후 다시 앉기", sourceRows: Object.freeze([44, 45, 46, 47, 48, 49, 50, 51]), durationMs: 760 }),
  });

  function definition(id) {
    return [...classicCatalog, ...catalog].find(item => item.id === canonicalId(id)) || null;
  }

  function equipmentDefinition(id) {
    return equipment.find(item => item.id === id) || equipment[0];
  }

  function pose(id, options = {}) {
    const pet = definition(id);
    if (!pet) return null;
    const direction = Object.hasOwn(walkRows, options.direction) ? options.direction : "down";
    const rawTime = options.elapsedMs ?? options.elapsed ?? 0;
    const elapsed = Number.isFinite(rawTime) ? Math.max(0, rawTime) : 0;
    const rawIdle = options.idleMs ?? elapsed;
    const idleElapsed = Number.isFinite(rawIdle) ? Math.max(0, rawIdle) : 0;
    const requested = options.action === "eat" ? "feed" : options.action || "idle";
    const action = options.reducedMotion ? "sit" : Object.hasOwn(actionDurations, requested) ? requested : "idle";
    const done = ["feed", "attack"].includes(action) && elapsed >= actionDurations[action];
    let frame, clip = action, flipX = false;
    if (pet.legacy) {
      // The existing dog atlas has only four directions x three gait cells.
      // A stopped gait cell is an honest idle, not an invented sitting pose.
      const row = { down: 0, left: 1, right: 2, up: 3 }[direction.split("_")[0]] ?? 0;
      frame = row * 9 + pet.fallbackColumn + (action === "walk" ? Math.floor(elapsed / 150) % 3 : 1);
      return { key: pet.key, frame, flipX: false, originX: .5, originY: 1, scale: pet.scale,
        action: action === "walk" ? "walk" : "idle", done, supportsSit: false, durationMs: actionDurations[action] };
    }
    if (action === "walk") {
      const row = walkRows[direction];
      frame = row * COLUMNS + Math.floor(elapsed / 110) % rowFrameCounts[row];
    } else if (action === "feed" && !done) {
      frame = eatRows[direction] * COLUMNS + Math.floor(elapsed / 160);
    } else if (action === "attack" && !done) {
      const row = pawRows[direction];
      frame = row * COLUMNS + Math.floor(elapsed / actionDurations.attack * rowFrameCounts[row]);
    } else {
      // Official REST first row has six seated directions. The front-facing
      // source clips briefly look toward the viewer, without flipping artwork
      // into directions the creator did not draw. No ambient sound is emitted.
      frame = sitColumns[direction];
      clip = "rest";
      const stage = !options.reducedMotion && !done
        ? [...idleStages].reverse().find(item => idleElapsed >= item.thresholdMs)
        : null;
      if (stage) {
        const side = ["left", "right"].includes(direction);
        if (!stage.static) {
          const row = side ? stage.rowRight : stage.rowDown;
          frame = row * COLUMNS + Math.floor((idleElapsed - stage.thresholdMs) / stage.frameMs) % rowFrameCounts[row];
          flipX = direction === "left";
        }
        clip = stage.name;
      } else if (!options.reducedMotion && !done) {
        const cycleTime = elapsed % IDLE_CYCLE_MS;
        const idle = idleClips.find(item => cycleTime >= item.startMs && cycleTime < item.startMs + rowFrameCounts[item.row] * item.frameMs);
        if (idle) { frame = idle.row * COLUMNS + Math.floor((cycleTime - idle.startMs) / idle.frameMs); clip = idle.name; }
      }
    }
    const result = { key: pet.key, frame, flipX, originX: ORIGIN.x, originY: ORIGIN.y,
      scale: pet.scale, action: done ? "sit" : action, clip, done, supportsSit: true, durationMs: actionDurations[action] };
    const requestedEquipment = options.equipment || "none";
    const chosenEquipment = id === "last_tick_ribbon" && requestedEquipment === "none"
      ? "valentine_bow_red"
      : requestedEquipment;
    const accessory = equipmentDefinition(chosenEquipment);
    if (accessory.key) result.overlay = { key: accessory.key, frame, flipX,
      originX: ORIGIN.x, originY: ORIGIN.y, scale: pet.scale };
    return result;
  }

  const api = Object.freeze({ assets, catalog, equipment, classicCatalog, aliases, canonicalId, definition, equipmentDefinition, pose, rowFrameCounts,
    walkRows, eatRows, pawRows, sitColumns, actions, actionDurations, idleClips, idleStages, IDLE_CYCLE_MS, COLUMNS, ROWS, FRAME_SIZE, SCALE, ORIGIN });
  root.ForestPets = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof window === "object" ? window : globalThis);
