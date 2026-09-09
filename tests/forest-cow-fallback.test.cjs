const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const ForestAnimals = require('../src/frontend/forest-animals.js');

const source = readFileSync(path.join(__dirname, '../src/frontend/forest-game.js'), 'utf8');
const helpers = source.slice(source.indexOf('  function fallbackCowEntry('), source.indexOf('  function drawPlacementGrid('));
const reaction = source.slice(source.indexOf('  function reactToCow('), source.indexOf('  let lastAnimationAt ='));
const animation = source.slice(source.indexOf('  let lastAnimationAt ='), source.indexOf('  function distanceTo('));
const pointer = source.slice(source.indexOf('  window.addEventListener("forest-placed-object-pointer"'), source.indexOf('  $("#reward-button").addEventListener'));

function setup() {
  let now = 0, reduced = false;
  const draws = [], transforms = [], events = [], moos = [], renders = [], frames = [], handlers = new Map();
  const first = Object.freeze({ code: 'reward_cow', x: 300, y: 400, rotation: 11, active: true, seed: 7 });
  const second = Object.freeze({ code: 'reward_cow', x: 350, y: 420, rotation: 0, active: true, seed: 8 });
  const cowEat = { key: 'forest-cow-eat', complete: true, naturalWidth: 512 };
  const cowWalk = { key: 'forest-cow-walk', complete: true, naturalWidth: 512 };
  const window = {
    ForestAnimals: { ...ForestAnimals, playMoo: options => moos.push(options) }, carrotForestPhaserActive: false,
    matchMedia: () => ({ matches: reduced }), requestAnimationFrame: callback => frames.push(callback),
    dispatchEvent: event => events.push(event), addEventListener: (name, callback) => handlers.set(name, callback),
  };
  const document = { hidden: false };
  const env = vm.createContext({
    window, document, state: { placed: [first, second], avatar: { mounted: false } }, cowStates: new WeakMap(),
    rewardCowImage: cowEat, rewardCowWalkImage: cowWalk,
    context: { save() {}, restore() {}, translate: (...args) => transforms.push(['translate', ...args]),
      rotate: value => transforms.push(['rotate', value]), drawImage: (...args) => draws.push(args) },
    currentScene: 'world', placementCode: null, interactiveObjectTypes: { reward_cow: 'cow' }, animatedObjectRows: {},
    performance: { now: () => now }, setStatus() {}, renderCanvas: () => renders.push(now),
    sfxEngine: { muted: false, effectiveVolume: value => value * .5 },
    ForestSfx: class { constructor() { this.muted = false; } effectiveVolume(value) { return value * .5; } },
    updateFallbackRiverDucks: () => false, animationFrame: 0, walkingUntil: 0, running: false, walkAnimationFrame: 0,
    lastAvatarPreviewAt: 0, avatarPreviewFrame: 0, $: () => ({ open: false }),
    renderCatalogThumbnailCanvases() {}, renderAvatarPreview() {}, canvas: { focus() {} },
    interact() { throw new Error('cow clicks must never toggle or persist a generic fixture'); },
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options?.detail; } },
  });
  vm.runInContext(helpers + reaction + animation + pointer, env);
  return { env, window, document, first, second, cowEat, cowWalk, draws, transforms, events, moos, renders, frames, handlers,
    setNow: value => { now = value; }, setReduced: value => { reduced = value; } };
}

test('fallback cows autonomously graze through RAF with independent transient clocks and no ambient moo or saved-item writes', () => {
  const fixture = setup(), { env, first, second } = fixture;
  const saved = JSON.stringify(env.state.placed), actions = new Set(), grazingFrames = new Set();
  let independent = false;
  for (let step = 0; step <= 1000; step++) {
    fixture.setNow(step * 50); env.animateWorld(step * 50);
    const state = env.cowStates.get(first).state, other = env.cowStates.get(second).state;
    actions.add(state.action);
    independent ||= state.action !== other.action || state.waitMs !== other.waitMs;
    if (state.action === 'graze') {
      env.drawPlacedObject(first);
      const sample = ForestAnimals.cowPose(state), draw = fixture.draws.at(-1);
      grazingFrames.add(sample.frame);
      assert.equal(draw[0], fixture.cowEat, 'autonomous grazing uses the existing eat sheet');
      assert.deepEqual(draw.slice(5), [-160 * sample.originX, -160 * sample.originY, 160, 160]);
      assert.equal(draw[7] / draw[3], 1.25); assert.equal(draw[8] / draw[4], 1.25);
    }
  }
  assert.deepEqual([...actions].sort(), ['graze', 'idle']);
  assert.ok(grazingFrames.size >= 4, 'grazing uses actual changing head/chewing frames');
  assert.equal(independent, true);
  assert.equal(JSON.stringify(env.state.placed), saved);
  assert.equal(fixture.frames.length, 1001, 'cow animation participates in the existing RAF owner');
  assert.ok(fixture.renders.length > 20);
  assert.deepEqual(fixture.moos, [], 'the ambient state machine never generates animal sounds');
  assert.deepEqual(fixture.events, []);
  for (const transform of fixture.transforms) {
    if (transform[0] === 'translate') assert.deepEqual(transform, ['translate', first.x, first.y]);
    else assert.deepEqual(transform, ['rotate', first.rotation * Math.PI / 180], 'only the saved placement angle is applied; no animated warping');
  }
});

test('head and body touches select distinct original walk-sheet poses, then return to a stable grazing-sheet idle', () => {
  const sequences = {};
  for (const touch of ['head', 'body']) {
    const fixture = setup(), { env, first } = fixture;
    env.reactToCow(0, touch);
    assert.equal(env.cowStates.get(first).state.action, touch);
    assert.equal(fixture.events[0].type, 'forest-cow-react');
    assert.deepEqual({ ...fixture.events[0].detail }, { index: 0, reaction: touch });
    const keys = new Set(), poses = [];
    for (let elapsed = 0; elapsed <= 1600; elapsed += 50) {
      fixture.setNow(elapsed); env.updateFallbackCows(elapsed); env.drawPlacedObject(first);
      const state = env.cowStates.get(first).state, pose = ForestAnimals.cowPose(state), draw = fixture.draws.at(-1);
      keys.add(draw[0].key); poses.push(`${pose.key}:${pose.frame}`);
      assert.equal(draw[0].key, pose.key, 'frame coordinates always read their matching source image');
      assert.deepEqual(draw.slice(5), [-160 * pose.originX, -160 * pose.originY, 160, 160], 'shared feet origins prevent the body jumping between sheets');
    }
    sequences[touch] = poses;
    assert.ok(keys.has('forest-cow-walk'));
    assert.equal(env.cowStates.get(first).state.action, 'idle');
    assert.equal(fixture.draws.at(-1)[0], fixture.cowEat);
    assert.equal(fixture.moos.length, 1, 'only the explicit click triggers moo');
    assert.deepEqual({ ...fixture.moos[0] }, { enabled: true, volume: .2 });
    assert.deepEqual([first.x, first.y, first.rotation], [300, 400, 11]);
  }
  assert.notDeepEqual(sequences.head, sequences.body, 'looking up and adjusting a hoof are different from each other and ambient grazing');
});

test('hidden tabs, home and placement pause phase clocks; reduced motion cancels touches without a deferred burst', () => {
  const fixture = setup(), { env, first, document } = fixture;
  env.reactToCow(0, 'head'); env.updateFallbackCows(200);
  const entry = env.cowStates.get(first), before = JSON.stringify(entry.state);
  document.hidden = true; assert.equal(env.updateFallbackCows(100000), false); document.hidden = false;
  env.currentScene = 'home'; assert.equal(env.updateFallbackCows(200000), false); env.currentScene = 'world';
  env.placementCode = 'bench'; assert.equal(env.updateFallbackCows(300000), false); env.placementCode = null;
  assert.equal(JSON.stringify(entry.state), before);
  fixture.setReduced(true); env.updateFallbackCows(400000);
  assert.equal(entry.state.action, 'idle');
  const stopped = JSON.stringify(entry.state);
  for (const time of [500000, 600000]) env.updateFallbackCows(time);
  assert.equal(JSON.stringify(entry.state), stopped);
  env.reactToCow(0, 'body');
  assert.equal(entry.state.action, 'idle');
  fixture.setReduced(false); env.updateFallbackCows(900000);
  assert.equal(entry.state.action, 'idle');
  assert.ok(entry.state.waitMs >= 11900, 'resume cannot consume minutes of suspended wait time');
});

test('Phaser alone owns cow state when active while the existing click event and mute-aware audio still dispatch', () => {
  const fixture = setup(), { env, window, first } = fixture;
  window.carrotForestPhaserActive = true;
  env.animateWorld(5000); env.drawPlacedObject(first);
  assert.equal(env.cowStates.has(first), false, 'hidden fallback rendering must not create a second autonomous actor');
  env.sfxEngine.muted = true;
  env.reactToCow(0, 'body');
  assert.equal(env.cowStates.has(first), false, 'Phaser click reactions cannot start a fallback clock');
  assert.equal(fixture.events[0].type, 'forest-cow-react');
  assert.equal(fixture.moos[0].enabled, false);
  window.carrotForestPhaserActive = false; env.updateFallbackCows(6000);
  const unchanged = JSON.stringify(env.cowStates.get(first));
  window.carrotForestPhaserActive = true; env.updateFallbackCows(900000);
  assert.equal(JSON.stringify(env.cowStates.get(first)), unchanged);
});

test('preview remains idle without transient state and missing walk art uses a matching idle source until loaded', () => {
  const fixture = setup(), { env, first, cowWalk, draws } = fixture;
  env.drawPlacedObject(first, true);
  assert.equal(env.cowStates.has(first), false);
  assert.equal(draws[0][0], fixture.cowEat);
  cowWalk.complete = false;
  env.reactToCow(0, 'body'); env.drawPlacedObject(first);
  assert.equal(draws.at(-1)[0], fixture.cowEat, 'an unfinished walk image cannot make the cow disappear');
  assert.deepEqual(draws.at(-1).slice(1, 5), [0, 128, 128, 128]);
  cowWalk.complete = true; env.drawPlacedObject(first);
  assert.equal(draws.at(-1)[0], cowWalk);
});

test('precise head/body metadata from Phaser overrides the old world-y heuristic; legacy pointer events remain compatible', async () => {
  for (const [detail, expected] of [
    [{ index: 0, y: 400, reaction: 'head' }, 'head'],
    [{ index: 0, y: 100, reaction: 'body' }, 'body'],
    [{ index: 0, y: 350 }, 'head'],
    [{ index: 0, y: 390, reaction: 'unsupported' }, 'body'],
  ]) {
    const fixture = setup();
    await fixture.handlers.get('forest-placed-object-pointer')({ detail });
    assert.equal(fixture.events[0].detail.reaction, expected);
    assert.equal(fixture.env.cowStates.get(fixture.first).state.action, expected);
  }
});
