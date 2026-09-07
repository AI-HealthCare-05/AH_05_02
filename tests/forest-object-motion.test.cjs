const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const source = readFileSync(path.join(__dirname, '../src/frontend/forest-phaser.js'), 'utf8');

function displayObject(x = 0, y = 0, texture, frame) {
  const data = new Map();
  return {
    x, y, texture, frame, scaleX: 1, scaleY: 1, angle: 0, visible: true, handlers: {}, operations: [],
    setData(key, value) { data.set(key, value); return this; },
    getData(key) { return data.get(key); },
    setPosition(x, y) { this.x = x; this.y = y; return this; },
    setOrigin() { return this; },
    setDisplaySize(w, h) { this.scaleX = w / 256; this.scaleY = h / 256; return this; },
    setScale(x, y = x) { this.scaleX = x; this.scaleY = y; return this; },
    setAngle(value) { this.angle = value; return this; },
    setAlpha(value) { this.alpha = value; return this; },
    setDepth(value) { this.depth = value; return this; },
    setVisible(value) { this.visible = value; return this; },
    setInteractive() { this.interactive = true; return this; },
    on(name, callback) { this.handlers[name] = callback; return this; },
    play() { this.playing = true; return this; },
    stop() { this.playing = false; return this; },
    setFrame(value) { this.frame = value; return this; },
    setTexture(value) { this.texture = value; this.frame = undefined; return this; },
    add(value) { this.list.push(value); return this; },
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
  };
  const window = {
    Phaser, matchMedia: () => ({ matches: reduced }),
    dispatchEvent: event => events.push(event),
  };
  vm.runInNewContext(source, {
    window, Phaser, document: { getElementById: () => ({}) },
    localStorage: { getItem: () => null },
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
  scene.placedObjectActors = [];
  const place = (code, active = true) => {
    const item = { code, x: 300, y: 400, rotation: 11, active };
    const actor = scene.createPlacedObjectActor(item, false, scene.placedObjectActors.length);
    scene.placedObjectActors.push(actor);
    return actor;
  };
  return { scene, place, tweens, events, setReduced: value => { reduced = value; } };
}

test('fountain, firefly and pinwheel fixtures keep identical frames and fixed bases', () => {
  const { scene, place } = setup();
  for (const [code, frame] of [['animated_fountain', 4], ['firefly_lantern', 8], ['garden_pinwheel', undefined]]) {
    const actor = place(code), fixture = actor.getData('fixtureTarget');
    const scale = [fixture.scaleX, fixture.scaleY];
    for (let time = 0; time < 30000; time += 137) {
      scene.updatePlacedObjectMotion(time);
      assert.deepEqual([actor.x, actor.y, actor.angle], [300, 400, 11]);
      assert.deepEqual([fixture.x, fixture.y, fixture.angle, fixture.frame], [0, 0, 0, frame]);
      assert.deepEqual([fixture.scaleX, fixture.scaleY], scale);
      assert.equal(fixture.playing, false);
    }
  }
});

test('pinwheel only rotates isolated blades around one fixed pivot at one turn per 36 seconds', () => {
  const { scene, place, setReduced } = setup();
  const actor = place('garden_pinwheel'), rotor = actor.getData('rotorTarget');
  const base = actor.getData('fixtureTarget');
  const pose = [rotor.x, rotor.y, rotor.scaleX, rotor.scaleY];
  assert.equal(base.texture, 'pinwheel-base');
  assert.equal(rotor.texture, 'pinwheel-blades');
  for (const [time, expected] of [[0, 0], [9000, 90], [18000, 180], [27000, 270], [36000, 0]]) {
    scene.updatePlacedObjectMotion(time);
    assert.equal(rotor.angle, expected);
    assert.deepEqual([rotor.x, rotor.y, rotor.scaleX, rotor.scaleY], pose);
    assert.deepEqual([actor.x, actor.y, base.x, base.y, base.angle], [300, 400, 0, 0, 0]);
  }
  setReduced(true);
  scene.updatePlacedObjectMotion(9000);
  assert.equal(rotor.angle, 0);
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

test('duck only bobs less than half a world pixel without horizontal travel or resize', () => {
  const { scene, place, setReduced } = setup();
  const actor = place('duck_float'), duck = actor.getData('motionTarget');
  const scale = [duck.scaleX, duck.scaleY];
  assert.equal(duck.texture, 'duck-cutout');
  for (let time = 0; time < 30000; time += 113) {
    scene.updatePlacedObjectMotion(time);
    assert.deepEqual([actor.x, actor.y, duck.x, duck.angle], [300, 400, 0, 0]);
    assert.ok(Math.abs(duck.y) <= .45);
    assert.deepEqual([duck.scaleX, duck.scaleY], scale);
    assert.equal(duck.playing, false);
  }
  setReduced(true);
  scene.updatePlacedObjectMotion(99999);
  assert.equal(duck.y, 0);
});

test('water and firefly accent movement stays subpixel and firefly OFF clears it', () => {
  const { scene, place } = setup();
  const fountain = place('animated_fountain'), lantern = place('firefly_lantern');
  for (let time = 0; time < 12000; time += 91) {
    scene.updatePlacedObjectMotion(time);
    const drops = fountain.getData('ambientFx').operations.filter(op => op[0] === 'circle');
    assert.equal(drops.length, 2);
    drops.forEach(([, x, y]) => {
      assert.ok([-15, 17].includes(x));
      assert.ok(Math.abs(y + 37) <= .35 + 1e-9);
    });
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

test('cow toggles and touch reactions retain display-size scale and fixed grass base', () => {
  const { scene, place, tweens, setReduced } = setup();
  const actor = place('reward_cow'), body = actor.getData('motionTarget'), base = actor.list[0];
  const origin = actor.getData('motionOrigin');
  assert.deepEqual([body.scaleX, body.scaleY], [84 / 256, 84 / 256]);
  assert.deepEqual([base.x, base.y], [0, 3]);
  assert.equal(tweens[0].targets, body);
  assert.ok(Math.abs(tweens[0].x) < 1 && Math.abs(tweens[0].y - origin.y) < 1);
  assert.equal(tweens[0].scaleX, undefined);
  for (const reaction of ['head', 'body']) {
    scene.reactCow(0, reaction);
    const tween = tweens.at(-1);
    assert.equal(tween.targets, body);
    assert.ok(Math.abs(tween.x) <= 1.2 && Math.abs(tween.y - origin.y) <= 1.8 + 1e-9);
    assert.equal(tween.scaleX, undefined);
    assert.deepEqual([body.scaleX, body.scaleY], [origin.scaleX, origin.scaleY]);
    assert.deepEqual([base.x, base.y], [0, 3]);
  }
  scene.applyPlacedObjectState(actor, { ...actor.getData('item'), active: false });
  assert.deepEqual([body.x, body.y, body.scaleX], [0, -7, 84 / 256]);
  setReduced(true);
  const count = tweens.length;
  scene.applyPlacedObjectState(actor, { ...actor.getData('item'), active: true });
  scene.reactCow(0, 'head');
  assert.equal(tweens.length, count);
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
