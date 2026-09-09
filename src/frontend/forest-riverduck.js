/* Riverduck movement in authored 768×512 world coordinates; no DOM, clocks,
 * randomness, persistence or mutation of a placed item's saved anchor.
 * Call createState({ x, y, seed }), then replace the transient state with the
 * result of update(state, deltaMs, { hidden, reducedMotion }) or
 * flee(state, { x: pointerWorldX, y: pointerWorldY }, { reducedMotion }). */
((root) => {
  "use strict";

  // Traced conservatively from world-v6.png (1536×1024, drawn at half size).
  // This convex LEFT basin follows its stone banks, not the old placement
  // rectangle. The dock already reaches world x≈180 at y≈410: its entire
  // platform, posts and the narrow lower-right shoreline stay outside.
  const WATER_POLYGON = Object.freeze([
    [38, 378], [76, 348], [115, 339], [153, 347], [177, 365],
    [181, 390], [168, 433], [135, 456], [96, 450], [58, 430], [39, 405],
  ].map(point => Object.freeze(point)));
  // Elliptical water-contact footprint, not the tall decorative silhouette.
  const FOOTPRINT = Object.freeze({ x: 16, y: 8 });
  const WATER_BOUNDS = Object.freeze({ left: 38, top: 339, right: 181, bottom: 456 });
  const MAX_DELTA_MS = 50;
  const CALM_SPEED = 6;
  const FLEE_SPEED = 36;
  const FLEE_DURATION_MS = 1100;
  const EPSILON = 1e-7;
  const finite = value => typeof value === "number" && Number.isFinite(value);
  const edges = WATER_POLYGON.map((point, index) => {
    const next = WATER_POLYGON[(index + 1) % WATER_POLYGON.length];
    const dx = next[0] - point[0], dy = next[1] - point[1];
    const length = Math.hypot(dx, dy);
    return Object.freeze({ x: point[0], y: point[1], nx: -dy / length, ny: dx / length });
  });

  function footprint(margin) {
    if (finite(margin)) return { x: Math.max(0, margin), y: Math.max(0, margin) };
    return { x: finite(margin?.x) ? Math.max(0, margin.x) : FOOTPRINT.x,
      y: finite(margin?.y) ? Math.max(0, margin.y) : FOOTPRINT.y };
  }

  function isWater(x, y, margin = FOOTPRINT) {
    if (!finite(x) || !finite(y)) return false;
    const radius = footprint(margin);
    return edges.every(edge => (x - edge.x) * edge.nx + (y - edge.y) * edge.ny
      >= Math.hypot(radius.x * edge.nx, radius.y * edge.ny) - EPSILON);
  }

  function clampToWater(x, y) {
    let px = finite(x) ? Math.max(WATER_BOUNDS.left, Math.min(WATER_BOUNDS.right, x)) : 112;
    let py = finite(y) ? Math.max(WATER_BOUNDS.top, Math.min(WATER_BOUNDS.bottom, y)) : 398;
    // Projection onto the convex footprint-inset half-planes. Invalid legacy
    // placements are corrected ONLY in this transient position, never saved.
    for (let pass = 0; pass < 24; pass += 1) {
      if (isWater(px, py)) return { x: px, y: py };
      edges.forEach(edge => {
        const missing = Math.hypot(FOOTPRINT.x * edge.nx, FOOTPRINT.y * edge.ny)
          - ((px - edge.x) * edge.nx + (py - edge.y) * edge.ny);
        if (missing > 0) { px += edge.nx * (missing + EPSILON); py += edge.ny * (missing + EPSILON); }
      });
    }
    return isWater(px, py) ? { x: px, y: py } : { x: 112, y: 398 };
  }

  function random(state) {
    let value = state.rng >>> 0 || 0x9e3779b9;
    value ^= value << 13; value ^= value >>> 17; value ^= value << 5;
    state.rng = value >>> 0;
    return state.rng / 4294967296;
  }

  function unit(x, y, fallbackX = -1, fallbackY = 0) {
    const length = finite(x) && finite(y) ? Math.hypot(x, y) : 0;
    return length > EPSILON ? { x: x / length, y: y / length } : { x: fallbackX, y: fallbackY };
  }

  function direction(x, y, fallback = "left") {
    if (Math.hypot(x, y) <= EPSILON) return fallback;
    return Math.abs(x) >= Math.abs(y) ? (x < 0 ? "left" : "right") : (y < 0 ? "up" : "down");
  }

  function idle(state) {
    state.mode = "idle"; state.remainingMs = 1400 + random(state) * 1800;
    state.moving = false; state.fleeing = false; state.speed = 0;
    state.threatX = null; state.threatY = null;
    return state;
  }

  function createState(anchor = {}) {
    const anchorX = finite(anchor.x) ? anchor.x : 112, anchorY = finite(anchor.y) ? anchor.y : 398;
    const position = clampToWater(anchorX, anchorY);
    const seed = finite(anchor.seed) ? anchor.seed >>> 0
      : (Math.imul(Math.round(anchorX * 100), 73856093) ^ Math.imul(Math.round(anchorY * 100), 19349663)) >>> 0;
    const state = { anchorX, anchorY, homeX: position.x, homeY: position.y, ...position,
      seed, rng: seed || 0x9e3779b9, headingX: -1, headingY: 0, direction: "left",
      mode: "idle", remainingMs: 0, moving: false, fleeing: false, speed: 0, threatX: null, threatY: null };
    state.turnSign = random(state) < .5 ? -1 : 1;
    return idle(state);
  }

  function copyState(state) {
    if (!state || !finite(state.x) || !finite(state.y) || !finite(state.rng)
      || !finite(state.homeX) || !finite(state.homeY) || !isWater(state.x, state.y)) {
      return createState({ x: state?.anchorX ?? state?.x, y: state?.anchorY ?? state?.y, seed: state?.seed });
    }
    return { ...state };
  }

  function flee(previous, pointer = {}, options = {}) {
    const state = copyState(previous);
    if (options.hidden) return { ...state, moving: false, speed: 0 };
    if (options.reducedMotion) return idle(state);
    if (!finite(pointer.x) || !finite(pointer.y)) return state;
    const away = unit(state.x - pointer.x, state.y - pointer.y, -state.headingX || 1, -state.headingY || 0);
    state.headingX = away.x; state.headingY = away.y;
    state.direction = direction(away.x, away.y, state.direction);
    state.mode = "flee"; state.remainingMs = FLEE_DURATION_MS;
    state.threatX = pointer.x; state.threatY = pointer.y;
    state.fleeing = true; state.moving = false; state.speed = 0;
    return state;
  }

  function startSwim(state) {
    const angle = random(state) * Math.PI * 2;
    const home = unit(state.homeX - state.x, state.homeY - state.y);
    const heading = Math.hypot(state.homeX - state.x, state.homeY - state.y) > 26
      ? home : { x: Math.cos(angle), y: Math.sin(angle) };
    state.headingX = heading.x; state.headingY = heading.y;
    state.mode = "swim"; state.remainingMs = 850 + random(state) * 850;
  }

  function advance(state, distance) {
    const heading = unit(state.headingX, state.headingY);
    const fleeing = state.mode === "flee";
    const threat = fleeing ? unit(state.x - state.threatX, state.y - state.threatY, heading.x, heading.y) : null;
    const turns = [0];
    for (let step = 1; step <= (fleeing ? 4 : 8); step += 1) turns.push(step * Math.PI / 8 * state.turnSign, -step * Math.PI / 8 * state.turnSign);
    for (const angle of turns) {
      const dx = heading.x * Math.cos(angle) - heading.y * Math.sin(angle);
      const dy = heading.x * Math.sin(angle) + heading.y * Math.cos(angle);
      // A bank may redirect the burst tangentially, but never towards the
      // click. If every safe escape is blocked, settle instead of oscillating.
      if (fleeing && dx * threat.x + dy * threat.y < -EPSILON) continue;
      const x = state.x + dx * distance, y = state.y + dy * distance;
      if (!isWater(x, y)) continue;
      state.x = x; state.y = y; state.headingX = dx; state.headingY = dy;
      state.direction = direction(dx, dy, state.direction);
      return true;
    }
    return false;
  }

  function update(previous, deltaMs, options = {}) {
    const state = copyState(previous);
    state.moving = false; state.speed = 0;
    if (options.hidden) return state; // Pause phase time as well as distance.
    if (options.reducedMotion) {
      if (state.mode !== "idle") idle(state);
      return state; // No deferred burst when the preference is later disabled.
    }
    const delta = finite(deltaMs) ? Math.max(0, Math.min(MAX_DELTA_MS, deltaMs)) : 0;
    if (!delta) return state;
    state.remainingMs = Math.max(0, (finite(state.remainingMs) ? state.remainingMs : 0) - delta);
    if (state.remainingMs <= 0) {
      if (state.mode === "idle") startSwim(state);
      else return idle(state);
    }
    state.fleeing = state.mode === "flee";
    if (state.mode === "idle") return state;
    const speed = state.fleeing ? FLEE_SPEED : CALM_SPEED;
    if (!advance(state, speed * delta / 1000)) return idle(state);
    state.moving = true; state.speed = speed;
    return state;
  }

  const api = Object.freeze({ createState, update, flee, isWater, clampToWater,
    WATER_POLYGON, WATER_BOUNDS, FOOTPRINT, MAX_DELTA_MS, CALM_SPEED, FLEE_SPEED, FLEE_DURATION_MS });
  root.ForestRiverDuck = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof window === "object" ? window : globalThis);
