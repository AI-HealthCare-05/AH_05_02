const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const source = readFileSync(path.join(__dirname, '../src/frontend/forest-phaser.js'), 'utf8');
const ForestAnimals = require('../src/frontend/forest-animals.js');
const ForestRiverDuck = require('../src/frontend/forest-riverduck.js');
const ForestRiverDuckArt = require('../src/frontend/forest-riverduck-art.js');

function displayObject(x = 0, y = 0, texture, frame) {
  const data = new Map();
  return {
    x, y, texture, frame, scaleX: 1, scaleY: 1, angle: 0, visible: true, handlers: {}, operations: [],
    setData(key, value) { data.set(key, value); return this; },
    getData(key) { return data.get(key); },
    setPosition(x, y) { this.x = x; this.y = y; return this; },
    setOrigin(x, y = x) { this.originX = x; this.originY = y; return this; },
    setDisplaySize(w, h) { this.scaleX = w / 256; this.scaleY = h / 256; return this; },
    setScale(x, y = x) { this.scaleX = x; this.scaleY = y; return this; },
    setFlipX(value) { this.flipX = value; return this; },
    setCrop(x, y, width, height) { this.crop = [x, y, width, height]; return this; },
    setAngle(value) { this.angle = value; return this; },
    setAlpha(value) { this.alpha = value; return this; },
    setDepth(value) { this.depth = value; return this; },
    setVisible(value) { this.visible = value; return this; },
    setInteractive() { this.interactive = true; return this; },
    on(name, callback) { this.handlers[name] = callback; return this; },
    play() { this.playing = true; return this; },
    stop() { this.playing = false; return this; },
    setFrame(value) { this.frame = value; return this; },
    setTexture(value, frame) { this.texture = value; this.frame = frame; return this; },
    setY(value) { this.y = value; return this; },
    add(value) { this.list.push(value); return this; },
    destroy() { this.destroyed = true; return this; },
    clear() { this.operations = []; return this; },
    lineStyle(...args) { this.operations.push(['lineStyle', ...args]); return this; },
    fillStyle(...args) { this.operations.push(['fillStyle', ...args]); return this; },
    strokeEllipse(...args) { this.operations.push(['ellipse', ...args]); return this; },
    fillCircle(...args) { this.operations.push(['circle', ...args]); return this; },
  };
}

function setup() {
  let reduced = false;
  const tweens = [], events = [];
  const Phaser = {
    Scene: class {}, AUTO: 0, Scale: { FIT: 1, CENTER_BOTH: 1 },
    Game: class { constructor(config) { this.config = config; } },
    Math: { Between: minimum => minimum }, Utils: { Array: { GetRandom: values => values[0] } },
  };
  const window = {
    Phaser, ForestAnimals, ForestRiverDuck, ForestRiverDuckArt, matchMedia: () => ({ matches: reduced }),
    dispatchEvent: event => events.push(event),
  };
  const document = { getElementById: () => ({}), hidden: false };
  vm.runInNewContext(source, {
    window, Phaser, document,
    localStorage: { getItem: () => null }, performance: { now: () => 0 },
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options?.detail; } },
  });
  const scene = new window.carrotForestPhaserGame.config.scene();
  scene.add = {
    sprite: displayObject, image: displayObject, graphics: () => displayObject(),
    container: (x, y, list) => Object.assign(displayObject(x, y), { list }),
  };
  scene.tweens = { killTweensOf() {}, add: config => tweens.push(config) };
  scene.cameras = { main: { getWorldPoint: (x, y) => ({ x, y }) } };
  scene.cancelPointerMovement = () => { scene.cancelled = true; };
  scene.createPinwheelTextures = () => {};
  scene.createFountainTextures = () => {};
  scene.placedObjectActors = [];
  scene.sceneName = 'world';
  scene.time = { now: 0 };
  const place = (code, active = true, overrides = {}) => {
    const item = { code, x: 300, y: 400, rotation: 11, active, ...overrides };
    const actor = scene.createPlacedObjectActor(item, false, scene.placedObjectActors.length);
    scene.placedObjectActors.push(actor);
    return actor;
  };
  return { scene, place, tweens, events, setReduced: value => { reduced = value; }, setHidden: value => { document.hidden = value; } };
}

test('fountain, firefly and pinwheel fixtures keep identical frames and fixed bases', () => {
  const { scene, place } = setup();
  for (const [code, frame] of [['animated_fountain', 0], ['firefly_lantern', 8], ['garden_pinwheel', undefined]]) {
    const actor = place(code), fixture = actor.getData('fixtureTarget');
    const scale = [fixture.scaleX, fixture.scaleY];
    for (let time = 0; time < 30000; time += 137) {
      scene.updatePlacedObjectMotion(time);
      assert.deepEqual([actor.x, actor.y, actor.angle], [300, 400, 11]);
      assert.deepEqual([fixture.x, fixture.y, fixture.angle, fixture.frame], [0, 0, 0, code === 'animated_fountain' ? Math.floor(time / 110) % 8 : frame]);
      assert.deepEqual([fixture.scaleX, fixture.scaleY], scale);
      assert.equal(fixture.playing, false);
    }
  }
});

test('pinwheel rotates only its blades while the full support and footprint stay fixed', () => {
  const { scene, place, setReduced } = setup();
  const actor = place('garden_pinwheel'), rotor = actor.getData('rotorTarget');
  const base = actor.getData('fixtureTarget');
  const pose = [rotor.x, rotor.y, rotor.scaleX, rotor.scaleY];
  assert.equal(base.texture, 'pinwheel-base');
  assert.equal(rotor.texture, 'pinwheel-blades');
  for (const [time, expected] of [[0, 0], [650, 26], [1300, 52], [1950, 78], [2600, 104], [3250, 130]]) {
    scene.updatePlacedObjectMotion(time);
    assert.equal(rotor.angle, expected);
    assert.equal(rotor.texture, 'pinwheel-blades', 'rotation never changes the authored palette');
    assert.deepEqual([rotor.x, rotor.y, rotor.scaleX, rotor.scaleY], pose);
    assert.deepEqual([actor.x, actor.y, base.x, base.y, base.angle], [300, 400, 0, 0, 0]);
  }
  setReduced(true);
  scene.updatePlacedObjectMotion(9000);
  assert.equal(rotor.angle, 130, 'reduced motion pauses at the current angle');
  assert.equal(rotor.texture, 'pinwheel-blades');
  assert.equal(rotor.interactive, true);
});

test('pinwheel layer split preserves the complete lower base and fixed stem without mutating source', () => {
  const { scene } = setup();
  const pixels = new Uint8ClampedArray(128 * 128 * 4);
  const offset = (x, y) => (y * 128 + x) * 4;
  pixels.set([220, 20, 70, 255], offset(40, 25));
  for (let y = 75; y < 100; y++) for (let x = 60; x < 68; x++) pixels.set([160, 95, 30, 255], offset(x, y));
  for (let y = 100; y < 128; y++) for (let x = 20; x < 110; x++) pixels.set([60, 110, 40, 255], offset(x, y));
  const original = new Uint8ClampedArray(pixels);
  const { base, blades } = scene.splitPinwheelPixels(pixels);
  assert.deepEqual([...base.slice(offset(0, 76))], [...original.slice(offset(0, 76))]);
  assert.ok(blades.slice(offset(0, 76)).every(value => value === 0));
  assert.deepEqual([...blades.slice(offset(40, 25), offset(40, 25) + 4)], [220, 20, 70, 255]);
  assert.equal(base[offset(40, 25) + 3], 0);
  for (let y = 48; y < 100; y++) {
    assert.deepEqual([...base.slice(offset(62, y), offset(62, y) + 4)], [160, 95, 30, 255]);
    assert.equal(blades[offset(62, y) + 3], 0);
  }
  assert.deepEqual(pixels, original);
});

test('riverduck alternates still rests and slow swims inside water without moving its saved anchor', () => {
  const { scene, place } = setup();
  const actor = place('duck_float', true, { x: 112, y: 398, seed: 7 }), duck = actor.getData('motionTarget');
  const anchor = Object.freeze(actor.getData('item'));
  const scale = [duck.scaleX, duck.scaleY];
  const modes = new Set(), moving = new Set(), positions = new Set(), swimFrames = new Set(), idleFrames = new Set();
  let leftMovingFrames = 0;
  assert.equal(duck.texture, ForestRiverDuckArt.asset.key);
  assert.deepEqual(scale, [ForestRiverDuckArt.SCALE, ForestRiverDuckArt.SCALE]);
  assert.deepEqual(duck.crop, [0, 0, 96, 87]);
  assert.equal(actor.list.length, 1, 'transparent riverduck has no moving water or ground fixture');
  assert.equal(actor.getData('ambientFx'), undefined);
  for (let time = 0; time < 30000; time += 50) {
    const before = [actor.x, actor.y];
    scene.updatePlacedObjectMotion(time);
    const state = actor.getData('riverDuckState');
    modes.add(state.mode); moving.add(state.moving); positions.add(`${actor.x}:${actor.y}`);
    assert.ok(ForestRiverDuck.isWater(actor.x, actor.y), 'the entire contact footprint stays off banks and dock');
    assert.deepEqual([actor.x, actor.y, actor.depth], [state.x, state.y, state.y - 2]);
    assert.ok(Math.hypot(actor.x - before[0], actor.y - before[1]) <= ForestRiverDuck.CALM_SPEED * .05 + 1e-8);
    assert.deepEqual([duck.x, duck.y, duck.angle, actor.angle], [0, 0, 0, 0], 'no whole-image bob, rocking, or saved rotation');
    assert.deepEqual([duck.scaleX, duck.scaleY], scale);
    assert.deepEqual(duck.crop, [0, 0, 96, 87], 'every real body frame retains the same submerged-foot crop');
    assert.deepEqual({ ...actor.getData('item') }, { code: 'duck_float', x: 112, y: 398, rotation: 11, active: true, seed: 7 });
    assert.equal(actor.getData('item'), anchor);
    assert.deepEqual([state.anchorX, state.anchorY], [112, 398]);
    const pose = ForestRiverDuckArt.pose(state, actor.getData('riverDuckClock'));
    assert.deepEqual([duck.texture, duck.frame, duck.originX, duck.originY, duck.flipX], [pose.key, pose.frame, pose.originX, pose.originY, pose.flipX]);
    (state.moving ? swimFrames : idleFrames).add(duck.texture);
    if (state.moving && state.direction === 'left') {
      leftMovingFrames++;
      assert.equal(duck.flipX, true, 'leftward travel mirrors the original right-facing body instead of rotating it');
    }
  }
  assert.deepEqual([...modes].sort(), ['idle', 'swim']);
  assert.deepEqual([...moving].sort(), [false, true]);
  assert.ok(positions.size > 50, 'the duck genuinely travels rather than only cycling a stationary image');
  assert.deepEqual([...swimFrames].sort(), ForestRiverDuckArt.assets.slice(2, 4).map(asset => asset.key).sort(), 'slow swims alternate both original body frames');
  assert.deepEqual([...idleFrames].sort(), ForestRiverDuckArt.assets.slice(0, 2).map(asset => asset.key).sort());
  assert.ok(leftMovingFrames > 0, 'the integration exercises a moving left-facing pose');
  const oldPlacement = place('duck_float');
  assert.ok(ForestRiverDuck.isWater(oldPlacement.x, oldPlacement.y));
  assert.deepEqual([oldPlacement.getData('item').x, oldPlacement.getData('item').y], [300, 400], 'invalid old placement is corrected only at runtime');
});

test('duck pointer interaction flees away without firing furniture selection or hunting events', () => {
  const { scene, place, events } = setup();
  const actor = place('duck_float', true, { x: 112, y: 398 }), duck = actor.getData('motionTarget');
  scene.updatePlacedObjectMotion(0);
  let stopped = 0;
  const pointer = { x: actor.x - 20, y: actor.y, button: 0 };
  duck.handlers.pointerdown(pointer, 0, 0, { stopPropagation: () => stopped++ });
  assert.equal(stopped, 1); assert.equal(scene.cancelled, true);
  assert.equal(actor.getData('riverDuckState').mode, 'flee');
  const before = [actor.x, actor.y];
  scene.updatePlacedObjectMotion(50);
  assert.ok(actor.x > before[0], 'a click left of the body sends it right');
  assert.ok(Math.hypot(actor.x - pointer.x, actor.y - pointer.y) > 20);
  assert.equal(actor.getData('riverDuckState').speed, ForestRiverDuck.FLEE_SPEED);
  assert.equal(duck.flipX, false, 'a rightward escape uses the unmirrored source pose');
  const fleeFrames = new Set([duck.texture]);
  assert.equal(events.length, 0, 'duck clicks do not emit generic furniture or hunting actions');
  for (let time = 100; time < 1800; time += 50) {
    scene.updatePlacedObjectMotion(time);
    if (actor.getData('riverDuckState').moving) fleeFrames.add(duck.texture);
    assert.deepEqual(duck.crop, [0, 0, 96, 87], 'flee frames cannot expose land-walking feet');
  }
  assert.deepEqual([...fleeFrames].sort(), ForestRiverDuckArt.assets.slice(4, 6).map(asset => asset.key).sort(), 'short escape alternates both faster original body frames');
  assert.equal(actor.getData('riverDuckState').mode, 'idle', 'the short escape ends in a still rest');
  for (const guard of ['placement', 'memory', 'home', 'rightButton']) {
    const guarded = setup(), actor = guarded.place('duck_float', true, { x: 112, y: 398 });
    guarded.scene.placementActive = guard === 'placement';
    guarded.scene.memoryCapturing = guard === 'memory';
    guarded.scene.sceneName = guard === 'home' ? 'home' : 'world';
    actor.getData('motionTarget').handlers.pointerdown({ x: 92, y: 398, button: guard === 'rightButton' ? 2 : 0 }, 0, 0, { stopPropagation() {} });
    assert.equal(actor.getData('riverDuckState').mode, 'idle', guard);
    assert.equal(guarded.events.length, 0, guard);
  }
});

test('riverduck pauses movement and its animation clock for hidden, interior, placement, and reduced-motion states', () => {
  const { scene, place, setReduced, setHidden } = setup();
  const actor = place('duck_float', true, { x: 112, y: 398 }), duck = actor.getData('motionTarget');
  scene.updatePlacedObjectMotion(0);
  duck.handlers.pointerdown({ x: 92, y: 398, button: 0 }, 0, 0, { stopPropagation() {} });
  scene.updatePlacedObjectMotion(50);
  const pose = [actor.x, actor.y], clock = actor.getData('riverDuckClock');
  const remaining = actor.getData('riverDuckState').remainingMs;
  setHidden(true); scene.updatePlacedObjectMotion(100000); setHidden(false);
  scene.sceneName = 'home'; scene.updatePlacedObjectMotion(200000); scene.sceneName = 'world';
  scene.placementActive = true; scene.updatePlacedObjectMotion(300000); scene.placementActive = false;
  actor.setVisible(false); scene.updatePlacedObjectMotion(400000); actor.setVisible(true);
  assert.deepEqual([actor.x, actor.y], pose);
  assert.equal(actor.getData('riverDuckState').remainingMs, remaining, 'hidden wall time does not consume the behavior phase');
  assert.equal(actor.getData('riverDuckClock'), clock);
  setReduced(true);
  for (const time of [400050, 500000, 600000]) scene.updatePlacedObjectMotion(time);
  assert.deepEqual([actor.x, actor.y], pose);
  assert.equal(actor.getData('riverDuckClock'), clock);
  assert.equal(actor.getData('riverDuckState').mode, 'idle', 'reduced motion cancels a pending flee');
  duck.handlers.pointerdown({ x: 92, y: 398, button: 0 }, 0, 0, { stopPropagation() {} });
  assert.equal(actor.getData('riverDuckState').mode, 'idle');
  setReduced(false); scene.updatePlacedObjectMotion(900000);
  assert.deepEqual([actor.x, actor.y], pose, 'resume does not teleport or replay a deferred burst');
  assert.equal(actor.getData('riverDuckClock'), clock + 50, 'resumed elapsed time is capped to one safe update');
});

test('saving unrelated furniture preserves transient duck swimming and flee state while its anchor stays unchanged', () => {
  const { scene, place } = setup();
  const actor = place('duck_float', true, { x: 112, y: 398, seed: 10 }), lantern = place('firefly_lantern');
  const anchor = { ...actor.getData('item') };
  scene.updatePlacedObjectMotion(0);
  for (let time = 50; time <= 5000; time += 50) scene.updatePlacedObjectMotion(time);
  actor.getData('motionTarget').handlers.pointerdown({ x: actor.x - 20, y: actor.y, button: 0 }, 0, 0, { stopPropagation() {} });
  scene.updatePlacedObjectMotion(5050);
  const state = actor.getData('riverDuckState'), clock = actor.getData('riverDuckClock');
  scene.syncPlacedObjects([{ ...lantern.getData('item'), active: false }, { ...anchor }]);
  const replacement = scene.placedObjectActors[1];
  assert.equal(actor.destroyed, true); assert.equal(lantern.destroyed, true);
  assert.notEqual(replacement, actor);
  assert.equal(replacement.getData('riverDuckState'), state, 'same saved anchor restores the exact transient state even after list reorder');
  assert.equal(replacement.getData('riverDuckClock'), clock);
  assert.deepEqual([replacement.x, replacement.y], [state.x, state.y]);
  assert.deepEqual({ ...replacement.getData('item') }, anchor);
  scene.updatePlacedObjectMotion(8000);
  assert.deepEqual([replacement.x, replacement.y], [state.x, state.y], 'recreated actor begins with a fresh elapsed-time baseline');
  scene.updatePlacedObjectMotion(8050);
  assert.equal(replacement.getData('riverDuckClock'), clock + 50);
  assert.ok(ForestRiverDuck.isWater(replacement.x, replacement.y));
});

test('fountain uses only masked water frames and firefly accents remain subpixel until switched off', () => {
  const { scene, place } = setup();
  const fountain = place('animated_fountain'), lantern = place('firefly_lantern');
  for (let time = 0; time < 12000; time += 91) {
    scene.updatePlacedObjectMotion(time);
    assert.deepEqual(fountain.getData('ambientFx').operations, [], 'no old-coordinate droplets may drift over the new stone fixture');
    assert.equal(fountain.getData('fixtureTarget').texture, 'fountain-flow');
    assert.equal(fountain.getData('fixtureTarget').frame, Math.floor(time / 110) % 8);
    const points = lantern.getData('ambientFx').operations.filter(op => op[0] === 'circle');
    points.forEach(([, x, y], index) => {
      const [originX, originY] = [[-18, -31], [24, -42], [12, -20]][index];
      assert.ok(Math.abs(x - originX) <= .65 + 1e-9);
      assert.ok(Math.abs(y - originY) <= .4 + 1e-9);
    });
  }
  scene.applyPlacedObjectState(lantern, { ...lantern.getData('item'), active: false });
  scene.updatePlacedObjectMotion(13000);
  assert.deepEqual(lantern.getData('ambientFx').operations, []);
  assert.equal(lantern.getData('fixtureTarget').visible, true);
  assert.deepEqual([lantern.x, lantern.y], [300, 400]);
});

test('reduced-motion water and light accents do not change between updates', () => {
  const { scene, place, setReduced } = setup();
  const actors = [place('animated_fountain'), place('firefly_lantern')];
  setReduced(true);
  scene.updatePlacedObjectMotion(0);
  const before = actors.map(actor => structuredClone(actor.getData('ambientFx').operations));
  scene.updatePlacedObjectMotion(54321);
  assert.deepEqual(actors.map(actor => actor.getData('ambientFx').operations), before);
});

test('cow grazes occasionally and responds to touch with separate original look and hoof frames', () => {
  const { scene, place, tweens, setReduced } = setup();
  const actor = place('reward_cow'), body = actor.getData('motionTarget');
  const origin = actor.getData('motionOrigin');
  assert.equal(actor.list.length, 1, 'complete transparent animal needs no attached grass/base layer');
  assert.equal(body.texture, 'forest-cow-eat'); assert.equal(body.frame, 4);
  assert.deepEqual([body.scaleX, body.scaleY], [1.25, 1.25]);
  assert.equal(body.originY, 88 / 128);
  let time = 0;
  const actions = new Set(), grazingFrames = new Set();
  for (; time < 30000; time += 40) {
    scene.updatePlacedObjectMotion(time);
    actions.add(actor.getData('cowState').action);
    if (actor.getData('cowState').action === 'graze') grazingFrames.add(body.frame);
    assert.deepEqual([actor.x, actor.y, body.x, body.y, body.scaleX, body.scaleY], [300, 400, 0, 0, 1.25, 1.25]);
  }
  assert.deepEqual([...actions].sort(), ['graze', 'idle']);
  assert.ok(grazingFrames.size >= 3);
  for (const reaction of ['head', 'body']) {
    actor.setData('cowState', { ...actor.getData('cowState'), action: 'graze', elapsedMs: 1700 });
    scene.reactCow(0, reaction);
    assert.equal(actor.getData('cowState').action, reaction);
    const frames = new Set();
    const end = time + 1500;
    for (; time <= end; time += 40) {
      scene.updatePlacedObjectMotion(time); frames.add(`${body.texture}:${body.frame}`);
      assert.deepEqual([body.x, body.y, body.scaleX, body.scaleY, body.angle], [0, 0, origin.scaleX, origin.scaleY, 0]);
    }
    assert.ok(frames.has(reaction === 'head' ? 'forest-cow-walk:8' : 'forest-cow-walk:6'));
    assert.equal(actor.getData('cowState').action, 'idle');
  }
  scene.applyPlacedObjectState(actor, { ...actor.getData('item'), active: false });
  assert.deepEqual([body.x, body.y, body.scaleX], [0, 0, 1.25]);
  setReduced(true);
  scene.applyPlacedObjectState(actor, { ...actor.getData('item'), active: true });
  scene.reactCow(0, 'head'); scene.updatePlacedObjectMotion(time + 40);
  assert.equal(body.frame, 4); assert.equal(tweens.length, 0, 'cow never uses whole-image bob/scale/rotation tweens');
});

test('cow clocks pause and survive unrelated saves without changing the placed anchor', () => {
  const { scene, place, setHidden, setReduced } = setup();
  const actor = place('reward_cow');
  const item = { ...actor.getData('item') };
  scene.updatePlacedObjectMotion(0);
  scene.updatePlacedObjectMotion(40);
  const before = actor.getData('cowState');
  setHidden(true); scene.updatePlacedObjectMotion(90);
  assert.equal(actor.getData('cowState').elapsedMs, before.elapsedMs);
  setHidden(false); scene.sceneName = 'home'; scene.updatePlacedObjectMotion(140);
  assert.equal(actor.getData('cowState').elapsedMs, before.elapsedMs);
  scene.sceneName = 'world'; scene.placementActive = true; scene.updatePlacedObjectMotion(180);
  assert.equal(actor.getData('cowState').elapsedMs, before.elapsedMs);
  scene.placementActive = false;
  scene.reactCow(0, 'body'); scene.updatePlacedObjectMotion(220);
  const response = structuredClone(actor.getData('cowState'));
  scene.syncPlacedObjects([item]);
  assert.deepEqual(scene.placedObjectActors[0].getData('cowState'), response);
  assert.deepEqual({ ...scene.placedObjectActors[0].getData('item') }, item);
  setReduced(true); scene.updatePlacedObjectMotion(260);
  assert.equal(scene.placedObjectActors[0].getData('cowState').action, 'idle');
});

test('rabbit uses directional hop frames while its body scale and foot origin remain stable', () => {
  const { scene } = setup();
  Object.assign(scene, { ratActive: true, ratDespawnAt: Infinity, ratTurnAt: Infinity, ratDirection: 'left', ratSpecies: 'rabbit' });
  scene.ratActor = displayObject(420, 350);
  scene.ratSprite = displayObject(0, 0).setScale(1.35);
  scene.ratShadow = displayObject(0, 0);
  scene.isBlocked = () => false;
  const frames = [];
  for (let time = 0; time < 560; time += 140) {
    scene.updateRat(time, 40); frames.push(scene.ratSprite.frame);
    assert.equal(scene.ratSprite.texture, 'forest-rabbit');
    assert.deepEqual([scene.ratSprite.x, scene.ratSprite.y, scene.ratSprite.scaleX, scene.ratSprite.scaleY, scene.ratSprite.angle], [0, 0, 1.35, 1.35, 0]);
    assert.equal(scene.ratSprite.originY, 51 / 72);
  }
  assert.deepEqual(frames, [4, 5, 6, 7]);
  assert.ok(scene.ratActor.x < 420);
  scene.isBlocked = () => true; scene.updateRat(600, 40);
  assert.ok(scene.ratSprite.frame >= 16, 'blocked movement uses grazing rather than skating in place');
  scene.setRatSpecies('mouse');
  scene.isBlocked = () => false; scene.ratTurnAt = Infinity; scene.updateRat(700, 40);
  assert.equal(scene.ratSprite.texture, 'lpc-rat', 'rabbits supplement rather than replace the existing mouse');
  assert.equal(scene.ratSprite.scaleX, 1.4);
  assert.equal(scene.ratSprite.originY, 1);
});

test('fixed child fixtures retain direct pointer selection and placement guard', () => {
  const { scene, place, events } = setup();
  const actor = place('firefly_lantern'), fixture = actor.getData('fixtureTarget');
  let stopped = 0;
  const click = () => fixture.handlers.pointerdown({ x: 300, y: 370 }, 0, 0, { stopPropagation: () => stopped++ });
  assert.equal(fixture.interactive, true);
  click();
  assert.equal(stopped, 1);
  assert.equal(scene.cancelled, true);
  assert.equal(events[0].type, 'forest-placed-object-pointer');
  assert.deepEqual({ ...events[0].detail }, { index: 0, x: 300, y: 370 });
  scene.placementActive = true;
  click();
  assert.equal(events.length, 1);
});
