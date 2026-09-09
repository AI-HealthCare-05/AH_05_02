const assert = require('node:assert/strict');
const { test } = require('node:test');
const duck = require('../src/frontend/forest-riverduck.js');

function assertSafe(state) {
  for (const key of ['x', 'y', 'headingX', 'headingY', 'speed', 'remainingMs']) assert.ok(Number.isFinite(state[key]), key);
  assert.ok(duck.isWater(state.x, state.y), `${state.x},${state.y} must retain the whole water footprint`);
  assert.ok(['left', 'right', 'up', 'down'].includes(state.direction));
}

test('traced water domain excludes banks and the full dock, including its left posts', () => {
  for (const point of [[112, 398], [100, 380], [128, 400], [128, 432], [96, 416]]) assert.equal(duck.isWater(...point), true, String(point));
  for (const point of [[64, 336], [288, 400], [180, 410], [190, 425], [220, 440], [256, 448], [128, 464], [32, 400], [NaN, 400], [128, Infinity]]) {
    assert.equal(duck.isWater(...point), false, String(point));
  }
  assert.equal(duck.isWater(115, 341, 0), true, 'raw bank outline can contain a point');
  assert.equal(duck.isWater(115, 341), false, 'the duck footprint, not only its center, must fit');
  for (let i = 0; i < duck.WATER_POLYGON.length; i++) {
    const a = duck.WATER_POLYGON[i], b = duck.WATER_POLYGON[(i + 1) % duck.WATER_POLYGON.length];
    const c = duck.WATER_POLYGON[(i + 2) % duck.WATER_POLYGON.length];
    assert.ok((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) > 0, 'convex polygon guarantees no segment crosses a bank');
  }
});

test('invalid old placements become safe transient positions without changing their saved anchors', () => {
  for (const point of [[256, 448], [64, 336], [288, 464], [-1e9, 1e9], [Infinity, NaN]]) {
    const item = Object.freeze({ x: point[0], y: point[1], seed: 8 });
    const state = duck.createState(item);
    assertSafe(state);
    if (Number.isFinite(item.x)) assert.equal(state.anchorX, item.x);
    if (Number.isFinite(item.y)) assert.equal(state.anchorY, item.y);
    assert.deepEqual(item, { x: point[0], y: point[1], seed: 8 });
  }
});

test('equal seeds and input sequences are deterministic and each duck owns independent state', () => {
  const anchor = Object.freeze({ x: 112, y: 398, seed: 123 });
  let a = duck.createState(anchor), b = duck.createState(anchor), other = duck.createState({ ...anchor, seed: 124 });
  const frozenOther = JSON.stringify(other);
  for (let i = 0; i < 700; i++) {
    Object.freeze(a);
    a = duck.update(a, 16); b = duck.update(b, 16);
    assert.deepEqual(a, b); assertSafe(a);
  }
  assert.equal(JSON.stringify(other), frozenOther);
  for (let i = 0; i < 700; i++) other = duck.update(other, 16);
  assert.notDeepEqual([a.x, a.y], [other.x, other.y]);
  assert.equal(a.anchorX, anchor.x); assert.equal(a.anchorY, anchor.y);
});

test('calm behavior alternates genuinely still waits and short, slow swims', () => {
  let state = duck.createState({ x: 112, y: 398, seed: 7 });
  const modes = new Set(), moving = new Set();
  for (let i = 0; i < 1000; i++) {
    const old = state; state = duck.update(state, 20);
    modes.add(state.mode); moving.add(state.moving);
    assertSafe(state);
    if (state.moving) assert.equal(state.speed, duck.CALM_SPEED);
    else assert.deepEqual([state.x, state.y], [old.x, old.y]);
    assert.ok(Math.hypot(state.x - old.x, state.y - old.y) <= duck.CALM_SPEED * .02 + 1e-8);
  }
  assert.deepEqual([...modes].sort(), ['idle', 'swim']);
  assert.deepEqual([...moving].sort(), [false, true]);
});

test('click bursts head away, never get closer during edge steering, then settle', () => {
  for (const pointer of [{ x: 70, y: 398 }, { x: 150, y: 398 }, { x: 112, y: 360 }, { x: 112, y: 440 }]) {
    let state = duck.flee(duck.createState({ x: 112, y: 398, seed: 12 }), pointer);
    assert.equal(state.fleeing, true);
    const start = state;
    let previousDistance = Math.hypot(state.x - pointer.x, state.y - pointer.y), moved = false;
    for (let elapsed = 0; elapsed < 1500; elapsed += 20) {
      state = duck.update(state, 20); assertSafe(state);
      const distance = Math.hypot(state.x - pointer.x, state.y - pointer.y);
      assert.ok(distance >= previousDistance - 1e-7, 'a fleeing duck must not run towards its click');
      previousDistance = distance;
      if (state.moving) { moved = true; assert.equal(state.speed, duck.FLEE_SPEED); }
    }
    assert.equal(moved, true); assert.equal(state.mode, 'idle'); assert.equal(state.fleeing, false);
    assert.equal(state.anchorX, start.anchorX); assert.equal(state.anchorY, start.anchorY);
  }
});

test('every edge and corner stays finite through repeated clicks and long-running swims', () => {
  const origins = [...duck.WATER_POLYGON, [112, 398], [256, 448]];
  for (let index = 0; index < origins.length; index++) {
    let state = duck.createState({ x: origins[index][0], y: origins[index][1], seed: index + 1 });
    for (let frame = 0; frame < 2200; frame++) {
      if (frame % 71 === 0) state = duck.flee(state, { x: 112 + Math.sin(frame) * 150, y: 398 + Math.cos(frame) * 150 });
      const before = state; state = duck.update(state, 50); assertSafe(state);
      assert.ok(Math.hypot(state.x - before.x, state.y - before.y) <= duck.FLEE_SPEED * .05 + 1e-7);
      // Convex inset keeps every point along each movement segment in water.
      assert.ok(duck.isWater((state.x + before.x) / 2, (state.y + before.y) / 2));
    }
  }
});

test('tab suspension and invalid delta cannot teleport or consume phase time', () => {
  const active = duck.flee(duck.createState({ x: 112, y: 398, seed: 3 }), { x: 75, y: 398 });
  assert.deepEqual(duck.update(active, 600000), duck.update(active, duck.MAX_DELTA_MS));
  for (const delta of [-50, NaN, Infinity, undefined, '100']) {
    const state = duck.update(active, delta);
    assert.deepEqual([state.x, state.y, state.remainingMs], [active.x, active.y, active.remainingMs]);
  }
  const hidden = duck.update(active, 600000, { hidden: true });
  assert.deepEqual([hidden.x, hidden.y, hidden.remainingMs], [active.x, active.y, active.remainingMs]);
  assert.equal(hidden.moving, false); assert.equal(hidden.speed, 0);
});

test('reduced motion keeps position still and cancels rather than defers a fast escape', () => {
  const initial = duck.createState({ x: 112, y: 398, seed: 18 });
  let state = duck.flee(initial, { x: 70, y: 398 }, { reducedMotion: true });
  for (let i = 0; i < 200; i++) state = duck.update(state, 50, { reducedMotion: true });
  assert.deepEqual([state.x, state.y], [initial.x, initial.y]);
  assert.equal(state.fleeing, false); assert.equal(state.moving, false); assert.equal(state.speed, 0);
  const active = duck.flee(initial, { x: 70, y: 398 });
  state = duck.update(active, 50, { reducedMotion: true });
  assert.equal(state.mode, 'idle'); assert.equal(state.fleeing, false);
  state = duck.update(state, 50);
  assert.equal(state.mode, 'idle'); assert.equal(state.moving, false);
});

test('a click exactly at the duck and malformed inputs never introduce NaN', () => {
  let state = duck.createState();
  state = duck.flee(state, { x: state.x, y: state.y });
  for (let i = 0; i < 100; i++) { state = duck.update(state, 25); assertSafe(state); }
  assertSafe(duck.update({ x: NaN, y: Infinity }, 16));
  assertSafe(duck.flee(null, { x: NaN, y: Infinity }));
});
