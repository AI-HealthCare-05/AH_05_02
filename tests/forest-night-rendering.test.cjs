const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../src/frontend/forest-phaser.js'), 'utf8');

function setup() {
  const operations = [], gradients = [];
  let refreshes = 0;
  const context = {
    clearRect: (...args) => operations.push(['clear', ...args]),
    fillRect: (...args) => operations.push(['fillRect', ...args]),
    beginPath() {}, arc: (...args) => operations.push(['arc', ...args]), fill() {},
    createRadialGradient(...args) {
      const gradient = { args, stops: [], addColorStop(...stop) { this.stops.push(stop); } };
      gradients.push(gradient); return gradient;
    },
  };
  function drawable() {
    return { visible: true, alpha: 1, operations: [],
      setDisplaySize(width, height) { this.width = width; this.height = height; return this; },
      setDepth(depth) { this.depth = depth; return this; },
      setAlpha(alpha) { this.alpha = alpha; return this; },
      setVisible(visible) { this.visible = visible; return this; },
      clear() { this.operations = []; return this; },
      lineStyle(...args) { this.operations.push(['line', ...args]); return this; },
      strokeEllipse(...args) { this.operations.push(['ellipse', ...args]); return this; },
      fillStyle(...args) { this.operations.push(['fill', ...args]); return this; },
      fillCircle(...args) { this.operations.push(['circle', ...args]); return this; },
    };
  }
  const Phaser = { Scene: class {}, AUTO: 0, Scale: { FIT: 1, CENTER_BOTH: 1 }, Game: class { constructor(config) { this.config = config; } } };
  const window = { Phaser, matchMedia: () => ({ matches: true }), location: { search: '' }, ForestAtmosphere: { seoulTime: () => ({ hour: 19 }) } };
  vm.runInNewContext(source, { window, Phaser, document: { getElementById: () => ({}) }, localStorage: { getItem: () => null }, URLSearchParams });
  const scene = new window.carrotForestPhaserGame.config.scene();
  scene.add = { image: () => drawable() };
  scene.textures = {
    exists: () => false,
    createCanvas: (_key, width, height) => ({ width, height, getContext: () => context, refresh: () => { refreshes++; } }),
  };
  scene.createNightMask();
  scene.lightFx = drawable(); scene.waterRippleFx = drawable(); scene.placedObjectActors = [];
  scene.nightStrength = 0;
  const addItem = item => { const actor = { depth: item.y - 2, getData: () => item }; scene.placedObjectActors.push(actor); return actor; };
  return { scene, window, context, operations, gradients, addItem, refreshes: () => refreshes };
}

test('one above-actor nighttime pass strongly darkens the world from 19:00 Seoul time', () => {
  const { scene, addItem, refreshes } = setup();
  const furniture = addItem({ code: 'bench', x: 350, y: 400 });
  assert.equal(scene.nightOverlay.depth, 900);
  assert.ok(scene.nightOverlay.depth > furniture.depth, 'placed furniture must receive the same darkness as the map');
  assert.equal(scene.nightMaskTexture.width, 768); assert.equal(scene.nightMaskTexture.height, 512);
  for (const hour of [19, 19.5, 20, 23.99, 0, 4.99]) assert.equal(scene.ambientStrengthForHour(hour), .78);
  assert.equal(scene.ambientStrengthForHour(18), .22);
  assert.equal(scene.ambientStrengthForHour(5), .44);
  assert.equal(scene.ambientStrengthForHour(6), .22);
  assert.equal(scene.ambientStrengthForHour(12), 0);
  scene.updateWorldAtmosphere(0);
  assert.equal(scene.nightOverlay.alpha, .78); assert.equal(scene.nightOverlay.visible, true);
  assert.equal(refreshes(), 1);
  assert.equal((source.match(/this\.nightOverlay\s*=/g) || []).length, 1, 'no second map or furniture darkening pass');
});

test('active lights cut local soft holes in that same mask, and idle updates reuse the texture', () => {
  const { scene, addItem, context, operations, gradients, refreshes } = setup();
  addItem({ code: 'lantern', x: 350, y: 400, active: true });
  addItem({ code: 'campfire', x: 480, y: 420, active: true });
  const offLamp = { code: 'firefly_lantern', x: 610, y: 340, active: false }; addItem(offLamp);
  addItem({ code: 'bench', x: 360, y: 420, active: true });
  scene.updateWorldAtmosphere(0);
  assert.equal(gradients.length, 2);
  assert.deepEqual(gradients[0].args, [350, 370, 0, 350, 370, 124]);
  assert.deepEqual(gradients[1].args, [480, 396, 0, 480, 396, 102]);
  assert.deepEqual(gradients[0].stops, [[0, 'rgba(0,0,0,.96)'], [.3, 'rgba(0,0,0,.78)'], [1, 'rgba(0,0,0,0)']]);
  assert.equal(context.globalCompositeOperation, 'source-over', 'mask drawing must restore compositing state');
  assert.equal(scene.lightFx.operations.filter(op => op[0] === 'circle').length, 4);
  assert.equal(operations.filter(op => op[0] === 'fillRect').length, 1, 'uniform darkness is drawn only once');
  scene.updateWorldAtmosphere(5000); assert.equal(refreshes(), 1);
  offLamp.active = true; scene.updateWorldAtmosphere(6000); assert.equal(refreshes(), 2);
  assert.equal(scene.localLightSources().length, 3);
});

test('atmosphere toggle and indoor scenes remove darkness without changing furniture alpha', () => {
  const { scene, addItem } = setup();
  const actor = addItem({ code: 'chair_green', x: 380, y: 440 });
  scene.updateWorldAtmosphere(0); scene.atmosphereEnabled = false; scene.updateWorldAtmosphere(1000);
  assert.equal(scene.nightOverlay.alpha, 0); assert.equal(scene.nightOverlay.visible, false);
  assert.equal(actor.alpha, undefined, 'no cumulative per-object alpha or tint mutation');
  scene.atmosphereEnabled = true; scene.sceneName = 'home'; scene.updateWorldAtmosphere(2000);
  assert.equal(scene.nightOverlay.visible, false); assert.equal(scene.lightFx.visible, false);
});

test('pinwheel hue frames preserve alpha, silhouette, hub, stem, base, and source pixels', () => {
  const { scene } = setup(), pixels = new Uint8ClampedArray(128 * 128 * 4);
  const index = (x, y) => (y * 128 + x) * 4;
  for (const [x, y, color] of [[35, 30, [230, 50, 70, 255]], [62, 48, [210, 150, 30, 255]],
    [62, 70, [165, 105, 30, 255]], [32, 106, [50, 155, 45, 220]], [45, 40, [230, 230, 230, 120]]]) pixels.set(color, index(x, y));
  const before = new Uint8ClampedArray(pixels);
  for (let phase = 1; phase < 5; phase++) {
    const output = scene.colorCyclePinwheelPixels(pixels, phase);
    assert.notDeepEqual([...output.slice(index(35, 30), index(35, 30) + 3)], [...pixels.slice(index(35, 30), index(35, 30) + 3)]);
    for (let i = 3; i < pixels.length; i += 4) assert.equal(output[i], pixels[i]);
    for (const [x, y] of [[62, 48], [62, 70], [32, 106], [45, 40]]) {
      assert.deepEqual([...output.slice(index(x, y), index(x, y) + 4)], [...pixels.slice(index(x, y), index(x, y) + 4)]);
    }
  }
  assert.deepEqual(pixels, before);
  assert.deepEqual([...scene.colorCyclePinwheelPixels(pixels, 0)], [...pixels]);
});
