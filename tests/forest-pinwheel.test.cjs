const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

function displayObject(x = 0, y = 0, texture, frame) {
  const data = new Map();
  return {
    x, y, texture, frame, angle: 0, visible: true,
    setData(key, value) { data.set(key, value); return this; },
    getData(key) { return data.get(key); },
    setOrigin(x, y) { this.originX = x; this.originY = y; return this; },
    setDisplaySize(w, h) { this.scaleX = w / 128; this.scaleY = h / 128; return this; },
    setTexture(value, frame) { this.texture = value; this.frame = frame; return this; },
    setAngle(value) { this.angle = value; return this; },
    setAlpha(value) { this.alpha = value; return this; },
    setDepth(value) { this.depth = value; return this; },
    setVisible(value) { this.visible = value; return this; },
    add(value) { this.list.push(value); return this; },
    clear() { return this; },
    stop() { return this; },
  };
}

function setup(individualReady = true) {
  let reducedMotion = false;
  const Phaser = {
    Scene: class {}, AUTO: 0, Scale: { FIT: 1, CENTER_BOTH: 1 },
    Game: class { constructor(config) { this.config = config; } },
  };
  const window = { Phaser, ForestObjects: { individualReady }, matchMedia: () => ({ matches: reducedMotion }) };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../src/frontend/forest-phaser.js'), 'utf8'), {
    window, Phaser, document: { getElementById: () => ({}) }, localStorage: { getItem: () => null },
  });
  const scene = new window.carrotForestPhaserGame.config.scene();
  scene.add = {
    sprite: displayObject, image: displayObject, graphics: () => displayObject(),
    container: (x, y, list) => Object.assign(displayObject(x, y), { list }),
  };
  scene.createPinwheelTextures = () => {};
  scene.placedObjectActors = [];
  const place = (active) => {
    const actor = scene.createPlacedObjectActor({ code: 'garden_pinwheel', x: 300, y: 400, rotation: 11, active });
    scene.placedObjectActors.push(actor);
    return actor;
  };
  return { scene, place, setReducedMotion: value => { reducedMotion = value; } };
}

test('pinwheel geometry rotates around the measured hub while its fixture and footprint remain fixed', () => {
  const { scene, place } = setup();
  const actor = place(), rotor = actor.getData('rotorTarget'), fixture = actor.getData('fixtureTarget');
  const pose = [rotor.x, rotor.y, rotor.scaleX, rotor.scaleY];
  assert.deepEqual([rotor.originX, rotor.originY], [63 / 128, 44 / 128]);
  assert.deepEqual([rotor.x, rotor.y], [(63 - 64) * 76 / 128, (44 - 128 * .84) * 76 / 128]);
  scene.updatePlacedObjectMotion(0);
  const angles = new Set();
  for (let time = 100; time <= 8000; time += 100) {
    scene.updatePlacedObjectMotion(time);
    angles.add(rotor.angle);
    assert.equal(rotor.angle, time * .04);
    assert.equal(rotor.texture, 'pinwheel-blades', 'spin geometry without changing the source palette');
    assert.deepEqual([rotor.x, rotor.y, rotor.scaleX, rotor.scaleY], pose);
    assert.deepEqual([actor.x, actor.y, actor.angle, fixture.x, fixture.y, fixture.angle], [300, 400, 11, 0, 0, 0]);
    assert.equal(fixture.texture, 'pinwheel-base');
  }
  assert.ok(angles.size > 60);
  const legacy = setup(false).place().getData('rotorTarget');
  assert.deepEqual([legacy.originX, legacy.originY], [62 / 128, 48 / 128]);
});

test('off, reduced motion, hidden actors and interior scenes pause the rotor without moving its support', () => {
  const { scene, place, setReducedMotion } = setup();
  const actor = place(), rotor = actor.getData('rotorTarget');
  scene.updatePlacedObjectMotion(0);
  scene.updatePlacedObjectMotion(500);
  assert.equal(rotor.angle, 20);
  setReducedMotion(true);
  scene.updatePlacedObjectMotion(2000);
  scene.updatePlacedObjectMotion(3000);
  assert.equal(rotor.angle, 20);
  setReducedMotion(false);
  scene.updatePlacedObjectMotion(3100);
  assert.equal(rotor.angle, 24, 'paused elapsed time is not included on resume');
  scene.applyPlacedObjectState(actor, { ...actor.getData('item'), active: false });
  scene.updatePlacedObjectMotion(3500);
  scene.updatePlacedObjectMotion(4500);
  assert.equal(rotor.angle, 24);
  scene.applyPlacedObjectState(actor, { ...actor.getData('item'), active: true });
  scene.updatePlacedObjectMotion(5000);
  scene.updatePlacedObjectMotion(5100);
  assert.equal(rotor.angle, 28);
  scene.sceneName = 'home';
  scene.updatePlacedObjectMotion(6000);
  assert.equal(rotor.angle, 28);
  scene.sceneName = 'world';
  actor.setVisible(false);
  scene.updatePlacedObjectMotion(7000);
  assert.equal(rotor.angle, 28);
  actor.setVisible(true);
  scene.updatePlacedObjectMotion(7100);
  assert.equal(rotor.angle, 32);
});

test('complete blade split preserves source alpha and colors; only runtime composition fills the occluded pole', () => {
  const { scene } = setup();
  const pixels = new Uint8ClampedArray(128 * 128 * 4), offset = (x, y) => (y * 128 + x) * 4;
  const color = (x, y, rgba) => pixels.set(rgba, offset(x, y));
  color(40, 20, [15, 12, 8, 255]); // Dark rotor outline must rotate, too.
  color(42, 22, [252, 248, 230, 211]); // Cream print and its source alpha.
  color(43, 23, [238, 100, 20, 79]);
  color(63, 44, [255, 190, 50, 255]);
  for (let y = 68; y < 105; y++) for (let x = 61; x <= 66; x++) {
    color(x, y, [140 + x, 80, 20, 255]);
  }
  color(62, 99, [215, 77, 20, 177]);
  const original = new Uint8ClampedArray(pixels);
  const { base, blades } = scene.splitStaticPinwheelPixels(pixels);
  for (let i = 0; i < pixels.length; i++) assert.equal(base[i] + blades[i], pixels[i]);
  for (const [x, y] of [[40, 20], [42, 22], [43, 23]]) {
    assert.equal(base[offset(x, y) + 3], 0, 'no stationary blade ghost');
    assert.deepEqual([...blades.slice(offset(x, y), offset(x, y) + 4)], [...pixels.slice(offset(x, y), offset(x, y) + 4)]);
  }
  assert.equal(base[offset(63, 44) + 3], 255, 'central cap stays fixed');
  const untouchedBase = new Uint8ClampedArray(base), support = scene.composePinwheelSupportPixels(base, pixels);
  for (let y = 44; y < 73; y++) for (let x = 61; x <= 66; x++) {
    assert.equal(support[offset(x, y) + 3], 255, 'turning blades cannot expose holes in the stem');
  }
  for (let y = 0; y < 128; y++) for (let x = 0; x < 128; x++) {
    if (y >= 44 && y < 73 && x >= 61 && x <= 66) continue;
    const i = offset(x, y);
    assert.deepEqual([...support.slice(i, i + 4)], [...base.slice(i, i + 4)], 'composition is confined to hidden wood');
  }
  assert.deepEqual(pixels, original);
  assert.deepEqual([...base], [...untouchedBase]);
});
