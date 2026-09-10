const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const ForestRiverDuck = require('../src/frontend/forest-riverduck.js');

const source = readFileSync(path.join(__dirname, '../src/frontend/forest-game.js'), 'utf8');
const helperCode = source.slice(source.indexOf('  function fallbackRiverDuckEntry('), source.indexOf('  function drawPlacementGrid('));
const animationCode = source.slice(source.indexOf('  let lastAnimationAt ='), source.indexOf('  function distanceTo('));
const pointerCode = source.slice(source.indexOf('  async function handleWorldPointer('), source.indexOf('  canvas.addEventListener("click"'));
const directPointerCode = source.slice(source.indexOf('  window.addEventListener("forest-placed-object-pointer"'), source.indexOf('  $("#reward-button").addEventListener'));

function setup() {
  let now = 0, reduced = false, modal = false;
  const draws = [], renders = [], interactions = [], events = [], statuses = [], frames = [], handlers = new Map();
  const first = Object.freeze({ code: 'duck_float', x: 112, y: 398, rotation: 75, active: true });
  const second = Object.freeze({ code: 'duck_float', x: 128, y: 432, rotation: 0, active: true });
  const context2d = { save() {}, restore() {}, translate() {}, rotate() {} };
  const window = {
    ForestRiverDuck, carrotForestPhaserActive: false,
    ForestRiverDuckArt: { draw: (...args) => draws.push(args) },
    matchMedia: () => ({ matches: reduced }),
    requestAnimationFrame: callback => frames.push(callback),
    dispatchEvent: event => events.push(event),
    addEventListener: (type, callback) => handlers.set(type, callback),
  };
  const document = { hidden: false, querySelector: () => modal ? {} : null };
  const env = vm.createContext({
    window, document, state: { placed: [first, second], avatar: { mounted: false } },
    riverDuckStates: new WeakMap(), riverDuckImage: { complete: true, naturalWidth: 96 }, context: context2d,
    currentScene: 'world', placementCode: null, placementDraft: null, interactiveObjectTypes: {},
    performance: { now: () => now },
    setStatus: text => statuses.push(text), renderCanvas: () => renders.push(now),
    canvas: { focus() {} }, nearbyPlacedObject: () => null,
    interact: async action => interactions.push(action), reactToCow() { throw new Error('not a cow'); },
    placementCellValid: () => true, renderPlacementUI() {}, emitPlacementUpdate() {}, itemCatalog: { duck_float: { name: '리버덕' } },
    cowReactionUntil: 0, animationFrame: 0, walkingUntil: 0, running: false, walkAnimationFrame: 0,
    lastAvatarPreviewAt: 0, avatarPreviewFrame: 0, $: () => ({ open: false }),
    renderCatalogThumbnailCanvases() {}, renderAvatarPreview() {},
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options?.detail; } },
  });
  vm.runInContext(helperCode + animationCode + pointerCode + directPointerCode, env);
  return { env, window, document, first, second, draws, renders, interactions, events, statuses, frames, handlers,
    setNow: value => { now = value; }, setReduced: value => { reduced = value; }, setModal: value => { modal = value; } };
}

test('placement preview stays at its selected cell, even when a legacy anchor clamps elsewhere', () => {
  const { env, draws } = setup();
  const invalid = Object.freeze({ code: 'duck_float', x: 256, y: 448, rotation: 90 });
  env.drawPlacedObject(invalid, true);
  assert.equal(draws[0][3], 0); assert.equal(draws[0][4], 0);
  assert.equal(env.riverDuckStates.has(invalid), false, 'a draft must not create autonomous live state');
  env.state.placed.push(invalid);
  env.drawPlacedObject(invalid);
  const pose = env.riverDuckStates.get(invalid).state;
  assert.equal(draws[1][3], pose.x - invalid.x);
  assert.equal(draws[1][4], pose.y - invalid.y);
  assert.ok(ForestRiverDuck.isWater(pose.x, pose.y));
  assert.deepEqual(invalid, { code: 'duck_float', x: 256, y: 448, rotation: 90 });
});

test('fallback ducks advance smoothly through the RAF path without any placed-item writes', () => {
  const test = setup(), { env, first } = test;
  const before = JSON.stringify(env.state.placed);
  const initial = env.fallbackRiverDuckEntry(first).state;
  for (let frame = 0; frame < 650; frame++) {
    test.setNow(frame * 16); env.animateWorld(frame * 16);
  }
  const entry = env.riverDuckStates.get(first);
  assert.notDeepEqual([entry.state.x, entry.state.y], [initial.x, initial.y]);
  assert.ok(entry.animationMs > 10000);
  assert.ok(test.renders.length > 180, 'swimming must paint much faster than the old 420 ms cadence');
  assert.equal(test.frames.length, 650, 'one next RAF per call');
  assert.equal(JSON.stringify(env.state.placed), before);
  env.drawPlacedObject(first);
  assert.equal(test.draws.at(-1)[5], entry.animationMs, 'source frames use the paused per-duck animation clock');
  assert.equal(test.events.length, 0); assert.equal(test.interactions.length, 0);
});

test('Phaser ownership, indoor scenes, and hidden tabs do not advance fallback ducks', () => {
  const test = setup(), { env, first, window, document } = test;
  env.updateFallbackRiverDucks(0);
  const entry = env.riverDuckStates.get(first);
  window.carrotForestPhaserActive = true;
  const original = JSON.stringify(entry);
  env.updateFallbackRiverDucks(4000);
  assert.equal(JSON.stringify(entry), original);
  window.carrotForestPhaserActive = false;
  for (const pause of ['indoor', 'hidden']) {
    env.currentScene = pause === 'indoor' ? 'home' : 'world'; document.hidden = pause === 'hidden';
    const before = [entry.state.x, entry.state.y, entry.state.remainingMs, entry.animationMs];
    for (let time = 5000; time <= 9000; time += 1000) assert.equal(env.updateFallbackRiverDucks(time), false);
    assert.deepEqual([entry.state.x, entry.state.y, entry.state.remainingMs, entry.animationMs], before);
  }
  document.hidden = false; env.currentScene = 'world';
  env.updateFallbackRiverDucks(9000016);
  assert.ok(entry.animationMs <= 50, 'a long suspension resumes with only one capped frame');
});

test('actual displaced duck clicks flee without opening pond UI or generic object actions', async () => {
  const test = setup(), { env, first } = test;
  const entry = env.fallbackRiverDuckEntry(first);
  entry.state = { ...entry.state, x: 153, y: 384 };
  assert.ok(ForestRiverDuck.isWater(entry.state.x, entry.state.y));
  assert.equal(env.fallbackRiverDuckAt(first.x, first.y - 28), null, 'old anchor is not a ghost hit target');
  assert.equal(env.fallbackRiverDuckAt(153, 370).item, first);
  const secondBefore = JSON.stringify(env.fallbackRiverDuckEntry(test.second));
  await env.handleWorldPointer(153, 370);
  assert.equal(entry.state.fleeing, true);
  assert.equal(JSON.stringify(env.riverDuckStates.get(test.second)), secondBefore, 'other ducks remain independent');
  assert.equal(test.interactions.length, 0); assert.equal(test.events.length, 0);
  assert.equal(first.x, 112); assert.equal(first.y, 398); assert.equal(first.active, true);
  await env.handleWorldPointer(260, 450);
  assert.deepEqual(test.interactions, ['pond'], 'open water still preserves the existing pond interaction');
});

test('a defensive placed-object event consumes duck clicks in either renderer without persistence', async () => {
  const test = setup(), callback = test.handlers.get('forest-placed-object-pointer');
  await callback({ detail: { index: 0, x: 90, y: 390 } });
  assert.equal(test.env.riverDuckStates.get(test.first).state.fleeing, true);
  test.window.carrotForestPhaserActive = true;
  const unchanged = JSON.stringify(test.env.riverDuckStates.get(test.first));
  await callback({ detail: { index: 0, x: 150, y: 390 } });
  assert.equal(JSON.stringify(test.env.riverDuckStates.get(test.first)), unchanged);
  assert.equal(test.interactions.length, 0); assert.equal(test.events.length, 0);
});

test('reduced motion and open dialogs suppress escape without queuing a delayed burst', async () => {
  const test = setup(), { env, first } = test;
  const entry = env.fallbackRiverDuckEntry(first), before = [entry.state.x, entry.state.y];
  test.setReduced(true);
  await env.handleWorldPointer(first.x, first.y - 10);
  for (let time = 0; time <= 5000; time += 50) env.animateWorld(time);
  assert.equal(entry.state.fleeing, false); assert.equal(entry.state.moving, false);
  assert.deepEqual([entry.state.x, entry.state.y], before); assert.equal(entry.animationMs, 0);
  test.setReduced(false); test.setModal(true);
  await env.handleWorldPointer(first.x, first.y - 10);
  assert.equal(entry.state.fleeing, false);
  assert.equal(test.interactions.length, 0);
  test.setModal(false); test.setNow(5020); env.animateWorld(5020);
  assert.equal(entry.state.mode, 'idle');
});

test('shared art hit testing takes precedence and moved anchors reset only their transient state', () => {
  const test = setup(), { env } = test;
  test.window.ForestRiverDuckArt.hitTest = (pose, x, y) => x === pose.x && y === pose.y;
  assert.equal(env.fallbackRiverDuckAt(test.first.x, test.first.y - 10), null);
  assert.equal(env.fallbackRiverDuckAt(test.first.x, test.first.y).item, test.first);
  const placed = { code: 'duck_float', x: 112, y: 398 };
  env.state.placed = [placed];
  const original = env.fallbackRiverDuckEntry(placed);
  placed.x = 128; placed.y = 416;
  const next = env.fallbackRiverDuckEntry(placed);
  assert.notEqual(next, original);
  assert.equal(next.state.anchorX, 128); assert.equal(next.state.anchorY, 416);
});
