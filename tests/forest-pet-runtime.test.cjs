const assert = require('node:assert/strict');
const { readFileSync, existsSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const source = readFileSync(path.join(__dirname, '../src/frontend/forest-phaser.js'), 'utf8');
const ids = ['last_tick_white', 'last_tick_gray', 'last_tick_ginger', 'last_tick_ribbon'];
const aliases = {};
const fixturePets = {
  assets: [...ids.slice(0, 3), 'bow'].map(key => ({ key, url: `/fixture/${key}.png`, frameWidth: 32, frameHeight: 32 })),
  catalog: ids.map(id => ({ id })),
  actionDurations: { feed: 1600, attack: 760 },
  definition(id) {
    if (id === 'white_pup') return { id, legacy: true };
    id = aliases[id] || id;
    return ids.includes(id) ? { id } : null;
  },
  pose(id, { action = 'idle', direction = 'down', elapsed = 0, reducedMotion = false } = {}) {
    id = aliases[id] || id;
    const pose = { key: id === 'last_tick_ribbon' ? 'last_tick_white' : id,
      frame: ['idle', 'walk', 'sit', 'feed', 'attack'].indexOf(action) * 8 + (reducedMotion ? 0 : Math.floor(elapsed / 100) % 4),
      originX: .5, originY: 27 / 32, scale: 1.6, flipX: direction === 'left' };
    if (id === 'last_tick_ribbon') pose.overlay = { ...pose, key: 'bow' };
    return pose;
  },
};

function actor(x = 0, y = 0, key = 'lpc-pets', frame = 1) {
  return {
    x, y, visible: true, texture: key, frame, handlers: {},
    setPosition(x, y) { Object.assign(this, { x, y }); return this; },
    setTexture(key, frame) { this.texture = key; this.frame = frame; return this; },
    setFrame(frame) { this.frame = frame; return this; },
    setOrigin(x, y = x) { this.originX = x; this.originY = y; return this; },
    setScale(x, y = x) { this.scaleX = x; this.scaleY = y; return this; },
    setDepth(depth) { this.depth = depth; return this; },
    setAngle(angle) { this.angle = angle; return this; },
    setFlipX(flipX) { this.flipX = flipX; return this; },
    setVisible(visible) { this.visible = visible; return this; },
    setAlpha(alpha) { this.alpha = alpha; return this; },
    on(type, handler) { this.handlers[type] = handler; return this; },
  };
}

function setup({ id = 'last_tick_white', pets = fixturePets, loaded = (pets?.assets || []).map(asset => asset.key) } = {}) {
  let reducedMotion = false, modal = false;
  const events = [], listeners = new Map(), loads = [], overlays = [];
  const document = { hidden: false, activeElement: { tagName: 'DIV' },
    getElementById: () => ({ focus() {} }), querySelector: () => modal ? {} : null };
  const Phaser = {
    Scene: class {}, AUTO: 0, Scale: { NONE: 0 }, Game: class { constructor(config) { this.config = config; } },
    Math: { Distance: { Between: (x, y, x2, y2) => Math.hypot(x - x2, y - y2) } },
  };
  const window = {
    Phaser, ForestPets: pets, ForestObjects: { INDIVIDUAL_ASSETS: [] },
    ForestGarden: require('../src/frontend/forest-garden.js'),
    ForestAnimals: { assets: [] }, ForestRiverDuckArt: { assets: [] },
    matchMedia: () => ({ matches: reducedMotion }),
    dispatchEvent: event => events.push(event),
    addEventListener: (type, handler) => listeners.set(type, handler), removeEventListener() {},
  };
  vm.runInNewContext(source, {
    window, document, Phaser, localStorage: { getItem: () => null }, performance: { now: () => 5000 },
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options?.detail; } },
  });
  const scene = new window.carrotForestPhaserGame.config.scene();
  scene.avatar = { x: 400, y: 350, direction: 'right', cosmetics: { pet: id }, tuning: { worldScale: .43 } };
  scene.pet = actor(); scene.pet.input = { hitArea: { width: 32, height: 32 }, customHitArea: false };
  scene.petEmoji = actor().setVisible(false); scene.petHeart = actor().setVisible(false);
  scene.petFollowX = 368; scene.petFollowY = 358;
  scene.player = actor(400, 350); scene.ratActor = actor(420, 350);
  scene.textures = { exists: key => key === 'lpc-pets' || loaded.includes(key) };
  scene.add = { sprite(x, y, key, frame) { const result = actor(x, y, key, frame); overlays.push(result); return result; } };
  scene.load = { image: (...args) => loads.push(args), spritesheet: (...args) => loads.push(args) };
  scene.tweens = { killTweensOf() {}, add() {} };
  scene.rebuildAvatar(); scene.attachWindowEvents();
  scene.dismissRat = (time, caught) => { assert.equal(caught, true); scene.ratActive = false; };
  return { scene, window, document, events, listeners, loads, overlays,
    reduced: value => { reducedMotion = value; }, modal: value => { modal = value; } };
}

function atRest(scene) { scene.petFollowX = 368; scene.petFollowY = 358; }
function step(scene, frames = 1, start = 5000, moving = false) {
  for (let index = 0; index < frames; index += 1) scene.updatePet(start + index * 50, 50, moving);
}
function poseState(scene) {
  return JSON.stringify({ x: scene.petFollowX, y: scene.petFollowY, action: scene.petPoseAction,
    elapsed: scene.petPoseElapsedMs, feed: scene.petFeedRemainingMs, attack: scene.petAttackRemainingMs, idle: scene.petIdleMs, frame: scene.pet.frame });
}

test('optional kitten sheets preload through the manifest without removing the bundled dog/photo atlas', () => {
  for (const pets of [fixturePets, null]) {
    const { scene, loads } = setup({ pets }); scene.preload();
    assert.ok(loads.some(([key, url]) => key === 'lpc-pets' && url.includes('carrot-forest-lpc-pets-v1.png')));
    for (const asset of pets?.assets || []) {
      const record = loads.find(([key]) => key === asset.key);
      assert.equal(record[1], asset.url);
      assert.equal(record[2].frameWidth, 32); assert.equal(record[2].frameHeight, 32);
    }
  }
});

test('left-click and touch feeding keep the existing event path, while right-clicks and blocked states cannot feed', () => {
  const { scene, window, document, events, modal } = setup();
  const start = source.indexOf('const feedPetFromPointer = '), end = source.indexOf('this.pet.setInteractive', start);
  const handler = vm.runInNewContext(`(function () { ${source.slice(start, end)} return feedPetFromPointer; }).call(scene)`, {
    scene, window, document, performance: { now: () => 5000 },
    CustomEvent: class { constructor(type) { this.type = type; } },
  });
  let stopped = 0; const event = { stopPropagation() { stopped += 1; } };
  for (const pointer of [{ wasTouch: false, button: 0 }, { wasTouch: true, button: 0 }]) {
    scene.movePath = [{ x: 600, y: 400 }]; handler(pointer, 0, 0, event);
    assert.equal(scene.movePath.length, 0); assert.equal(scene.lastPetPointerAt, 5000);
  }
  assert.equal(stopped, 2); assert.equal(events.filter(event => event.type === 'forest-pet-clicked').length, 2);
  handler({ wasTouch: false, button: 2 }, 0, 0, event);
  for (const mode of ['hidden', 'placement', 'modal', 'photo']) {
    document.hidden = mode === 'hidden'; scene.placementActive = mode === 'placement';
    modal(mode === 'modal'); scene.memoryCapturing = mode === 'photo';
    handler({ wasTouch: false, button: 0 }, 0, 0, event);
  }
  assert.equal(stopped, 2); assert.equal(events.filter(event => event.type === 'forest-pet-clicked').length, 2);
});

test('all four kittens use real poses, stable feet, and an exactly synchronized ribbon', () => {
  for (const id of [...ids, ...Object.keys(aliases)]) {
    const { scene, overlays } = setup({ id });
    const saved = JSON.stringify(scene.avatar);
    for (const action of ['walk', 'idle', 'sit', 'feed', 'attack']) for (const direction of ['up', 'down', 'left', 'right']) {
      scene.petFacing = direction;
      scene.renderPetPose(action, 350);
      const expected = fixturePets.pose(id, { action, direction, elapsed: 350 });
      assert.equal(scene.pet.texture, expected.key); assert.equal(scene.pet.frame, expected.frame);
      assert.equal(scene.pet.originY, expected.originY); assert.equal(scene.pet.angle, 0);
      assert.deepEqual([scene.pet.scaleX, scene.pet.scaleY], [expected.scale, expected.scale]);
      assert.deepEqual([scene.pet.x, scene.pet.y], [scene.petFollowX, scene.petFollowY]);
      if (expected.overlay) {
        assert.equal(overlays.length, 1, 'frame changes reuse one overlay');
        for (const field of ['frame', 'x', 'y', 'originX', 'originY', 'scaleX', 'scaleY', 'flipX', 'angle']) {
          assert.equal(scene.petOverlay[field], scene.pet[field], `matching ribbon ${field}`);
        }
        assert.ok(scene.petOverlay.depth > scene.pet.depth);
      } else assert.equal(overlays.length, 0);
    }
    assert.equal(JSON.stringify(scene.avatar), saved, 'poses never modify saved avatar data');
  }
});

test('missing pet art or ribbon falls back to loaded LPC frames without fabricating a sit pose', () => {
  for (const id of [...ids, ...Object.keys(aliases), 'white_pup']) {
    const { scene } = setup({ id, loaded: [] });
    for (const action of ['idle', 'sit', 'feed']) {
      scene.renderPetPose(action, 900);
      assert.equal(scene.pet.visible, true); assert.equal(scene.pet.texture, 'lpc-pets');
      assert.equal(scene.petSourceAction, 'idle'); assert.equal(scene.pet.originY, 1);
      assert.deepEqual([scene.pet.scaleX, scene.pet.scaleY, scene.pet.angle], [1.2, 1.2, 0]);
      assert.equal(scene.petOverlay?.visible || false, false);
    }
  }
  const { scene } = setup({ id: 'last_tick_ribbon', loaded: ['last_tick_white'] });
  assert.equal(scene.pet.texture, 'lpc-pets', 'a missing overlay must not produce a mismatched or missing-texture costume');
});

test('actual movement chooses walk while resting preserves a continuous source idle clock without bobbing or scaling', () => {
  const { scene } = setup(); atRest(scene);
  step(scene, 89); assert.equal(scene.petPoseAction, 'idle');
  step(scene); assert.equal(scene.petPoseAction, 'idle');
  const restingPosition = [scene.pet.x, scene.pet.y];
  step(scene, 5); assert.deepEqual([scene.pet.x, scene.pet.y], restingPosition);
  step(scene, 85); assert.equal(scene.petPoseAction, 'idle');
  assert.equal(scene.petPoseElapsedMs, 9000, 'longer authored waiting clips are not reset every few seconds');
  scene.avatar.sitting = true; step(scene);
  assert.equal(scene.petPoseAction, 'sit'); assert.equal(scene.petPoseElapsedMs, 9050);
  scene.avatar.sitting = false;
  scene.petFollowX = 330;
  step(scene); assert.equal(scene.petPoseAction, 'walk', 'catching up after the player stops is still movement');
  assert.equal(scene.petFacing, 'right');
  atRest(scene); scene.petTrail = [{ x: 368, y: 350, time: 0 }];
  scene.petLastSampleAt = 5000;
  scene.updatePet(5000, 50, true);
  assert.equal(scene.petPoseAction, 'idle', 'a blocked player input does not animate a stationary pet as walking');
});

test('sitting and feeding keep paws planted, override hunting, and feed survives ordinary avatar synchronization', () => {
  const { scene, listeners, events } = setup({ id: 'last_tick_ribbon' });
  Object.assign(scene, { ratActive: true, ratEventId: 9, ratSpecies: 'rabbit', petFollowX: 420, petFollowY: 350 });
  scene.avatar.sitting = true;
  step(scene, 5); assert.equal(scene.petPoseAction, 'sit');
  assert.deepEqual([scene.pet.x, scene.pet.y], [420, 350]); assert.equal(events.length, 0);
  scene.avatar.sitting = false;
  listeners.get('forest-pet-fed')({ detail: { pet: 'last_tick_ribbon', amount: 1 } });
  assert.equal(scene.petPoseAction, 'feed'); assert.equal(scene.petHeart.visible, true);
  step(scene, 4);
  const before = poseState(scene), trail = scene.petTrail;
  scene.applyAvatarUpdate(JSON.parse(JSON.stringify(scene.avatar)));
  assert.equal(poseState(scene), before); assert.equal(scene.petTrail, trail);
  step(scene, 27); assert.equal(events.length, 0);
  step(scene, 2, 7000);
  assert.equal(events.filter(event => event.type === 'forest-rat-caught').length, 1);
});

test('changing pets clears only transient pet state and hides a previous ribbon, while selecting none hides both layers', () => {
  const { scene, listeners } = setup({ id: 'last_tick_ribbon' });
  listeners.get('forest-pet-fed')({ detail: { pet: 'last_tick_ribbon' } }); step(scene, 4);
  const avatar = JSON.parse(JSON.stringify(scene.avatar)); avatar.cosmetics.pet = 'last_tick_gray';
  scene.applyAvatarUpdate(avatar);
  assert.equal(scene.petFeedRemainingMs, 0); assert.equal(scene.petPoseElapsedMs, 0);
  assert.equal(scene.pet.texture, 'last_tick_gray'); assert.equal(scene.petOverlay.visible, false);
  listeners.get('forest-pet-fed')({ detail: { pet: 'last_tick_ribbon' } });
  assert.equal(scene.petFeedRemainingMs, 0, 'a late previous-pet feed cannot animate the newly selected pet');
  avatar.cosmetics.pet = 'none'; scene.rebuildAvatar();
  assert.equal(scene.pet.visible, false); assert.equal(scene.petOverlay.visible, false);
});

test('hidden pages, placement, modals and photos pause both hunting and transient animation clocks', () => {
  for (const mode of ['hidden', 'placement', 'modal', 'photo']) {
    const runtime = setup(); const { scene, events, document, modal } = runtime;
    Object.assign(scene, { ratActive: true, ratEventId: 11, ratSpecies: 'mouse', petFollowX: 420, petFollowY: 350 });
    if (mode === 'hidden') document.hidden = true;
    if (mode === 'placement') scene.placementActive = true;
    if (mode === 'modal') modal(true);
    if (mode === 'photo') scene.memoryCapturing = true;
    const before = poseState(scene);
    scene.updatePet(90000, 90000, true);
    assert.equal(poseState(scene), before, mode); assert.equal(events.length, 0, mode);
  }
});

test('reduced motion freezes source frames, discards new feed animations, and never stretches a pet', () => {
  const { scene, reduced, listeners } = setup(); atRest(scene); reduced(true);
  step(scene); const first = scene.pet.frame, elapsed = scene.petPoseElapsedMs;
  listeners.get('forest-pet-fed')({ detail: { pet: 'last_tick_white' } });
  step(scene, 200);
  assert.equal(scene.pet.frame, first); assert.equal(scene.petPoseElapsedMs, elapsed);
  assert.equal(scene.petFeedRemainingMs, 0); assert.equal(scene.petPoseAction, 'idle');
  assert.equal(scene.pet.scaleX, scene.pet.scaleY); assert.equal(scene.pet.angle, 0);
});

test('long or invalid deltas cannot fast-forward a feed or teleport the follower', () => {
  const one = setup(), resumed = setup();
  one.scene.updatePet(5000, 50, true); resumed.scene.updatePet(90000, 90000, true);
  assert.deepEqual([one.scene.pet.x, one.scene.pet.y, one.scene.petPoseElapsedMs],
    [resumed.scene.pet.x, resumed.scene.pet.y, resumed.scene.petPoseElapsedMs]);
  const before = [one.scene.pet.x, one.scene.pet.y, one.scene.petPoseElapsedMs];
  for (const delta of [0, -1, NaN, Infinity]) one.scene.updatePet(91000, delta, false);
  assert.deepEqual([one.scene.pet.x, one.scene.pet.y, one.scene.petPoseElapsedMs], before);
});

test('every original and new pet retains one rabbit carrot and zero mouse rewards, never hunting indoors', () => {
  for (const id of [...ids, ...Object.keys(aliases), 'white_pup']) for (const species of ['rabbit', 'mouse']) {
    const { scene, events } = setup({ id });
    Object.assign(scene, { ratActive: true, ratEventId: 27, ratSpecies: species, petFollowX: 420, petFollowY: 350 });
    scene.sceneName = 'home'; step(scene); assert.equal(events.length, 0);
    scene.sceneName = 'world'; Object.assign(scene, { petFollowX: 420, petFollowY: 350 });
    step(scene, 2);
    const catches = events.filter(event => event.type === 'forest-rat-caught');
    assert.equal(catches.length, 1, `${id}/${species}`);
    assert.deepEqual(JSON.parse(JSON.stringify(catches[0].detail)), { eventId: 27, amount: species === 'rabbit' ? 1 : 0, source: 'pet', species });
  }
});

test('a successful catch plays one finite planted-foot paw reaction and feeding can interrupt it', () => {
  const { scene, listeners, events } = setup();
  Object.assign(scene, { ratActive: true, ratEventId: 32, ratSpecies: 'mouse', petFollowX: 420, petFollowY: 350 });
  step(scene); assert.equal(scene.petPoseAction, 'attack');
  const position = [scene.pet.x, scene.pet.y], first = scene.pet.frame;
  step(scene, 4);
  assert.notEqual(scene.pet.frame, first); assert.deepEqual([scene.pet.x, scene.pet.y], position);
  listeners.get('forest-pet-fed')({ detail: { pet: 'last_tick_white' } });
  assert.equal(scene.petPoseAction, 'feed'); assert.equal(scene.petAttackRemainingMs, 0);
  step(scene, 33);
  assert.notEqual(scene.petPoseAction, 'attack');
  assert.equal(events.filter(event => event.type === 'forest-rat-caught').length, 1);
});

test('installed production kitten manifest can drive all four runtime variants without synthetic frame assumptions', t => {
  const modulePath = path.join(__dirname, '../src/frontend/forest-pets.js');
  if (!existsSync(modulePath)) { t.skip('production manifest has not landed yet'); return; }
  const pets = require(modulePath);
  for (const id of ids) {
    const { scene, listeners } = setup({ id, pets });
    for (const action of ['walk', 'idle', 'sit', 'feed', 'attack']) {
      scene.renderPetPose(action, 450);
      const pose = pets.pose(id, { action, direction: scene.petFacing, elapsed: 450 });
      assert.equal(scene.pet.texture, pose.key); assert.equal(scene.pet.frame, pose.frame);
      assert.ok(Number.isFinite(scene.pet.originY) && Number.isFinite(scene.pet.scaleX));
      if (pose.overlay) assert.equal(scene.petOverlay.frame, pose.overlay.frame);
    }
    scene.renderPetPose('walk', 0); const first = scene.pet.frame;
    scene.renderPetPose('walk', 160);
    assert.notEqual(scene.pet.frame, first, 'the real manifest receives elapsed time, not a frozen default');
    listeners.get('forest-pet-fed')({ detail: { pet: id } });
    assert.equal(scene.petFeedRemainingMs, pets.actionDurations.feed, 'runtime feeding uses the audited source duration');
  }
  const { scene } = setup({ pets }); atRest(scene);
  const clips = new Set();
  for (let index = 0; index < 240; index += 1) {
    scene.updatePet(index * 50, 50, false);
    const pose = pets.pose(ids[0], { action: scene.petPoseAction, direction: scene.petFacing, elapsed: scene.petPoseElapsedMs });
    clips.add(pose.clip); assert.equal(scene.pet.frame, pose.frame);
  }
  assert.deepEqual([...clips].sort(), ['meow_sit', 'rest', 'wash_sit', 'yawn_sit'], 'the live resting clock reaches every audited waiting clip');
});

test('all three LPC walkers remain visible animated choices without modifying saved IDs', () => {
  const pets = require('../src/frontend/forest-pets.js');
  for (const pet of pets.classicCatalog) {
    const { scene, events } = setup({ id: pet.id, pets });
    scene.preload();
    const saved = JSON.stringify(scene.avatar);
    assert.equal(scene.pet.visible, true, pet.id);
    for (const action of ['walk', 'idle', 'sit', 'feed', 'attack']) {
      const expected = pets.pose(pet.id, { action, direction: scene.petFacing, elapsed: 300 });
      scene.renderPetPose(action, 300);
      assert.equal(scene.pet.texture, expected.key, pet.id);
      assert.equal(scene.pet.frame, expected.frame, pet.id);
      assert.equal(scene.petSourceAction, action === 'walk' ? 'walk' : 'idle');
      assert.equal(scene.pet.scaleX, expected.scale);
      assert.equal(scene.pet.scaleX, scene.pet.scaleY);
      assert.equal(scene.pet.angle, 0);
      assert.deepEqual(scene.pet.input.hitArea, { width: 32, height: 32 });
      assert.equal(scene.petOverlay?.visible || false, false);
    }
    assert.equal(JSON.stringify(scene.avatar), saved);
    Object.assign(scene, { ratActive: true, ratEventId: 27, ratSpecies: 'rabbit', petFollowX: 420, petFollowY: 350 });
    step(scene, 2);
    assert.equal(events.filter(event => event.type === 'forest-rat-caught').length, 1);
    scene.avatar.cosmetics.pet = 'none'; scene.rebuildAvatar();
    assert.equal(scene.pet.visible, false);
  }
});

test('older saved IDs stay visible and animate identically to canonical choices without rewriting the saved ID', () => {
  const pets = require('../src/frontend/forest-pets.js');
  for (const [oldId, id] of Object.entries(pets.aliases)) {
    const { scene } = setup({ id: oldId, pets });
    const saved = JSON.stringify(scene.avatar);
    assert.equal(scene.pet.visible, true);
    scene.renderPetPose('walk', 0); const first = scene.pet.frame;
    scene.renderPetPose('walk', 160);
    const expected = pets.pose(id, { action: 'walk', direction: scene.petFacing, elapsed: 160 });
    assert.equal(scene.pet.texture, expected.key);
    assert.equal(scene.pet.frame, expected.frame);
    assert.notEqual(scene.pet.frame, first);
    assert.equal(JSON.stringify(scene.avatar), saved);
    assert.deepEqual(scene.pet.input.hitArea, { width: 32, height: 32 });
  }
});
