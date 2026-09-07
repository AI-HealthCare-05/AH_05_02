const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const window = {};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../src/frontend/forest-fire.js'), 'utf8'), { window });
const { flameMask, rippleFrame, SIZE, FRAMES } = window.ForestFire;
const pixel = (x, y) => (y * SIZE + x) * 4;
function fixture() {
  const pixels = new Uint8ClampedArray(SIZE * SIZE * 4);
  for (let y = 35; y < 170; y++) for (let x = 120; x < 144; x++) pixels.set([255, 145, 20, 255], pixel(x, y));
  for (let y = 170; y < SIZE; y++) for (let x = 20; x < 235; x++) pixels.set([180, 90, 30, 255], pixel(x, y));
  pixels.set([125, 120, 110, 255], pixel(85, 100));
  return pixels;
}

test('flame selection excludes grey stone, lower warm logs and other tiles', () => {
  const pixels = fixture(), mask = flameMask(pixels);
  assert.equal(mask[100 * SIZE + 130], 1);
  assert.equal(mask[100 * SIZE + 85], 0);
  assert.equal(mask[190 * SIZE + 130], 0);
  pixels.set([255, 160, 20, 255], pixel(20, 100));
  assert.equal(flameMask(pixels)[100 * SIZE + 20], 0);
});

test('frames visibly change fire while preserving the base and source bytes', () => {
  const pixels = fixture(), original = new Uint8ClampedArray(pixels), mask = flameMask(pixels);
  assert.deepEqual([...rippleFrame(pixels, mask, 0)], [...pixels]);
  const moving = rippleFrame(pixels, mask, 4);
  assert.notDeepEqual([...moving.slice(0, pixel(0, 170))], [...pixels.slice(0, pixel(0, 170))]);
  for (let index = 0; index < FRAMES; index++) {
    const frame = rippleFrame(pixels, mask, index);
    assert.deepEqual([...frame.slice(pixel(0, 170))], [...pixels.slice(pixel(0, 170))]);
    assert.deepEqual([...frame.slice(pixel(85, 100), pixel(85, 100) + 4)], [125, 120, 110, 255]);
  }
  assert.deepEqual(pixels, original);
});

test('empty flame mask leaves the whole object unchanged', () => {
  const pixels = new Uint8ClampedArray(SIZE * SIZE * 4).fill(80);
  assert.deepEqual([...rippleFrame(pixels, flameMask(pixels), 8)], [...pixels]);
});

test('Phaser starts/stops flame animation for on/off and reduced motion', () => {
  const source = fs.readFileSync(path.join(__dirname, '../src/frontend/forest-phaser.js'), 'utf8');
  const body = source.slice(source.indexOf('    applyPlacedObjectState('), source.indexOf('    reactCow('));
  let reduced = false;
  const scene = { tweens: { killTweensOf() {} } };
  vm.runInNewContext(`scene.apply = function${body.slice(body.indexOf('('))}`, {
    scene, animatedObjectRows: {}, interactiveObjectTypes: { campfire: 'fire' },
    window: { matchMedia: () => ({ matches: reduced }), ForestFire: { FRAMES } },
  });
  const calls = [];
  const target = { setVisible() { return this; }, play() { calls.push('play'); return this; }, stop() { calls.push('stop'); return this; }, setFrame(n) { calls.push(n); return this; } };
  const actor = { setData() { return this; }, getData: key => key.startsWith('fire') ? target : null, setPosition() { return this; }, setAlpha() { return this; } };
  scene.apply(actor, { code: 'campfire', active: true, x: 100, y: 200 });
  assert.deepEqual(calls, ['play']);
  calls.length = 0;
  scene.apply(actor, { code: 'campfire', active: false, x: 100, y: 200 });
  assert.deepEqual(calls, ['stop', 0]);
  reduced = true; calls.length = 0;
  scene.apply(actor, { code: 'campfire', active: true, x: 100, y: 200 });
  assert.deepEqual(calls, ['stop', 0]);
});
