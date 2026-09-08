const assert = require('node:assert/strict');
const { test } = require('node:test');
const animals = require('../src/frontend/forest-animals.js');
const { cowBehavior } = animals;

function advance(state, duration, options) {
  for (let elapsed = 0; elapsed < duration; elapsed += 50) state = animals.updateCowState(state, Math.min(50, duration - elapsed), options);
  return state;
}

function at(state, action, elapsedMs) {
  return Object.freeze({ ...state, action, elapsedMs });
}

test('each cow has a deterministic independent 12–22 second quiet timer and an immutable saved anchor', () => {
  const item = Object.freeze({ x: 442, y: 337, seed: 161, active: true });
  const before = JSON.stringify(item), state = animals.createCowState(item);
  assert.ok(Object.isFrozen(state));
  assert.equal(state.action, 'idle'); assert.equal(state.elapsedMs, 0);
  assert.equal(state.anchorX, item.x); assert.equal(state.anchorY, item.y);
  const waits = new Set();
  for (let seed = 1; seed < 100; seed++) {
    const sample = animals.createCowState({ x: item.x, y: item.y, seed });
    assert.ok(sample.waitMs >= 12000 && sample.waitMs <= 22000);
    waits.add(sample.waitMs);
  }
  assert.ok(waits.size > 20);
  let a = state, b = animals.createCowState(item);
  for (let i = 0; i < 1500; i++) {
    a = animals.updateCowState(a, 30); b = animals.updateCowState(b, 30);
    assert.deepEqual(a, b); assert.ok(Object.isFrozen(a));
    assert.equal(a.anchorX, item.x); assert.equal(a.anchorY, item.y);
  }
  assert.equal(state.elapsedMs, 0, 'updating a second clock cannot mutate its previous state');
  assert.equal(JSON.stringify(item), before);
});

test('an untouched cow periodically lowers, chews and lifts its head, then returns to a fresh quiet wait', () => {
  const initial = animals.createCowState({ x: 360, y: 375, seed: 15 });
  let state = advance(initial, initial.waitMs - 1);
  assert.equal(state.action, 'idle'); assert.equal(animals.cowPose(state).frame, 4);
  state = animals.updateCowState(state, 1);
  assert.equal(state.action, 'graze'); assert.equal(state.elapsedMs, 0);
  const seen = [];
  for (const time of [0, 250, 650, 1100, 1450, 1800, 2150, 2550, 2900]) {
    const pose = animals.cowPose(at(state, 'graze', time));
    seen.push(pose.frame); assert.equal(pose.key, 'forest-cow-eat'); assert.equal(pose.originY, 88 / 128);
  }
  assert.deepEqual(seen, [4, 5, 6, 7, 6, 7, 6, 5, 4]);
  state = advance(state, cowBehavior.grazeMs);
  assert.equal(state.action, 'idle'); assert.equal(state.elapsedMs, 0);
  assert.notEqual(state.rng, initial.rng, 'each completed action draws a new per-cow waiting period');
  assert.ok(state.waitMs >= 12000 && state.waitMs <= 22000);
  state = advance(state, state.waitMs);
  assert.equal(state.action, 'graze', 'automatic grazing repeats without a click');
});

test('head touch interrupts chewing with a lift, front look, and left return using matching foot origins', () => {
  const initial = animals.createCowState({ x: 384, y: 400, seed: 4 });
  const grazing = at(initial, 'graze', 1200);
  assert.equal(animals.cowPose(grazing).frame, 7);
  const touched = animals.touchCowState(grazing, 'head');
  assert.equal(touched.action, 'head'); assert.equal(touched.elapsedMs, 0);
  assert.equal(touched.liftFromColumn, 3); assert.equal(grazing.action, 'graze');
  const poses = [0, 150, 300, 749, 750, 1049].map(time => animals.cowPose(at(touched, 'head', time)));
  assert.deepEqual(poses.map(pose => [pose.key, pose.frame]), [
    ['forest-cow-eat', 6], ['forest-cow-eat', 5], ['forest-cow-walk', 8],
    ['forest-cow-walk', 8], ['forest-cow-walk', 4], ['forest-cow-walk', 4],
  ]);
  assert.equal(animals.cowPose(at(touched, 'head', 250)).frame, 4, 'fully lift before turning to look at the player');
  assert.equal(poses[2].originY, 102 / 128);
  for (const index of [0, 1, 4, 5]) assert.equal(poses[index].originY, 88 / 128);
  const settled = advance(touched, cowBehavior.headMs);
  assert.equal(settled.action, 'idle'); assert.equal(animals.cowPose(settled).frame, 4);
});

test('body touch is a distinct short original walk-row gesture, never the eating cycle', () => {
  const initial = animals.createCowState({ x: 384, y: 400, seed: 14 });
  const touched = animals.touchCowState(at(initial, 'graze', 1800), 'body');
  assert.equal(touched.action, 'body');
  const frames = [];
  for (const time of [0, 170, 340, 510, 680]) {
    const pose = animals.cowPose(at(touched, 'body', time));
    frames.push(pose.frame); assert.equal(pose.key, 'forest-cow-walk'); assert.equal(pose.originY, 88 / 128);
    assert.equal(pose.moving, false);
    for (const key of ['x', 'y', 'scale', 'scaleX', 'scaleY', 'rotation', 'angle', 'offsetX', 'offsetY']) assert.equal(key in pose, false, key);
  }
  assert.deepEqual(frames, [4, 5, 6, 7, 4]);
  assert.equal(advance(touched, cowBehavior.bodyMs).action, 'idle');
});

test('repeated touches debounce without keeping the same gesture alive indefinitely', () => {
  const initial = animals.createCowState({ x: 384, y: 400, seed: 4 });
  let touched = animals.touchCowState(initial, 'body');
  touched = advance(touched, 200);
  assert.deepEqual(animals.touchCowState(touched, 'head'), touched);
  touched = advance(touched, 50);
  const changed = animals.touchCowState(touched, 'head');
  assert.equal(changed.action, 'head'); assert.equal(changed.elapsedMs, 0);
  touched = animals.touchCowState(initial, 'body');
  for (let elapsed = 0; elapsed < 850; elapsed += 50) {
    touched = animals.touchCowState(touched, 'body');
    touched = animals.updateCowState(touched, 50);
  }
  assert.equal(touched.action, 'idle');
});

test('hidden clocks pause and discard clicks, while oversized or invalid delta never causes catch-up', () => {
  const state = animals.touchCowState(animals.createCowState({ x: 380, y: 440, seed: 7 }), 'head');
  assert.deepEqual(animals.updateCowState(state, 600000, { hidden: true }), state);
  assert.deepEqual(animals.touchCowState(state, 'body', { hidden: true }), state);
  assert.deepEqual(animals.updateCowState(state, 600000), animals.updateCowState(state, 50));
  for (const delta of [-20, NaN, Infinity, undefined, '50']) assert.deepEqual(animals.updateCowState(state, delta), state);
  assert.equal(animals.updateCowState(state, 50).elapsedMs, 50);
});

test('reduced motion stays static, discards active or queued touches, and resumes with a quiet interval', () => {
  const initial = animals.createCowState({ x: 380, y: 440, seed: 7 });
  for (const action of ['graze', 'head', 'body']) {
    const active = at(initial, action, 450);
    assert.equal(animals.cowPose(active, { reducedMotion: true }).frame, 4);
    assert.equal(animals.cowPose(active, { reducedMotion: true }).key, 'forest-cow-eat');
    let stopped = animals.updateCowState(active, 50, { reducedMotion: true });
    assert.equal(stopped.action, 'idle'); assert.equal(stopped.elapsedMs, 0);
    const quiet = stopped;
    for (let i = 0; i < 500; i++) stopped = animals.updateCowState(stopped, 50, { reducedMotion: true });
    assert.deepEqual(stopped, quiet);
    stopped = animals.updateCowState(stopped, 50);
    assert.equal(stopped.action, 'idle'); assert.equal(stopped.elapsedMs, 50);
  }
  assert.equal(animals.touchCowState(initial, 'head', { reducedMotion: true }).action, 'idle');
});

test('all poses use valid original source frames and malformed state remains finite', () => {
  for (const state of [undefined, {}, { x: NaN, y: Infinity }, { action: 'broken', elapsedMs: NaN }]) {
    const next = animals.updateCowState(state, 16);
    for (const key of ['anchorX', 'anchorY', 'rng', 'waitMs', 'elapsedMs']) assert.ok(Number.isFinite(next[key]), key);
    assert.ok(animals.frameRect(animals.cowPose(next).key, animals.cowPose(next).frame));
  }
  const initial = animals.createCowState();
  for (const action of ['idle', 'graze', 'head', 'body']) {
    for (let elapsedMs = 0; elapsedMs < 5000; elapsedMs += 17) {
      const pose = animals.cowPose(at(initial, action, elapsedMs));
      assert.ok(animals.frameRect(pose.key, pose.frame));
      assert.equal(pose.originX, .5);
    }
  }
});

test('legacy photo and thumbnail cowFrame behavior remains exactly compatible', () => {
  const frames = [];
  for (let elapsed = 0; elapsed < animals.cowReactionDurationMs; elapsed += 170) frames.push(animals.cowFrame(elapsed).frame);
  assert.deepEqual(frames, [4, 5, 6, 7, 7, 6, 5, 4]);
  assert.equal(animals.cowFrame().frame, 4);
  assert.equal(animals.cowFrame(500, { reducedMotion: true }).frame, 4);
});
