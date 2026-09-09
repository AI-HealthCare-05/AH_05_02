const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const zlib = require('node:zlib');
const window = {};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../src/frontend/forest-fire.js'), 'utf8'), { window });
const { flameMask, rippleFrame, alphaBounds, fitBase, SIZE, FRAMES } = window.ForestFire;
const pixel = (x, y) => (y * SIZE + x) * 4;
function fixture() {
  const pixels = new Uint8ClampedArray(SIZE * SIZE * 4);
  for (let y = 35; y < 170; y++) for (let x = 120; x < 144; x++) pixels.set([255, 145, 20, 255], pixel(x, y));
  for (let y = 170; y < SIZE; y++) for (let x = 20; x < 235; x++) pixels.set([180, 90, 30, 255], pixel(x, y));
  pixels.set([125, 120, 110, 255], pixel(85, 110));
  return pixels;
}

// The shipped atlas is an 8-bit RGBA PNG. Decode it without a browser or optional
// graphics packages so silhouette/base regressions are checked against real art.
function readPng(assetName) {
  const png = fs.readFileSync(path.join(__dirname, '../src/frontend/assets', assetName));
  assert.equal(png[24], 8);
  assert.equal(png[25], 6);
  const width = png.readUInt32BE(16), height = png.readUInt32BE(20), chunks = [];
  for (let offset = 8; offset < png.length;) {
    const length = png.readUInt32BE(offset);
    if (png.toString('ascii', offset + 4, offset + 8) === 'IDAT') chunks.push(png.subarray(offset + 8, offset + 8 + length));
    offset += 12 + length;
  }
  const packed = zlib.inflateSync(Buffer.concat(chunks)), stride = width * 4;
  const decoded = new Uint8ClampedArray(stride * height);
  const paeth = (a, b, c) => {
    const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
    return pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
  };
  for (let y = 0; y < height; y++) for (let x = 0; x < stride; x++) {
    const left = x >= 4 ? decoded[y * stride + x - 4] : 0;
    const up = y ? decoded[(y - 1) * stride + x] : 0;
    const upperLeft = x >= 4 && y ? decoded[(y - 1) * stride + x - 4] : 0;
    const filter = packed[y * (stride + 1)];
    const prediction = [0, left, up, Math.floor((left + up) / 2), paeth(left, up, upperLeft)][filter];
    decoded[y * stride + x] = (packed[y * (stride + 1) + x + 1] + prediction) & 255;
  }
  return { pixels: decoded, width, height };
}

function originalCampfire() {
  const { pixels: decoded, width } = readPng('carrot-forest-storage-atlas-v4.png');
  const tile = new Uint8ClampedArray(SIZE * SIZE * 4);
  for (let y = 0; y < SIZE; y++) {
    const start = ((2 * SIZE + y) * width + 4 * SIZE) * 4;
    tile.set(decoded.subarray(start, start + SIZE * 4), y * SIZE * 4);
  }
  return tile;
}

test('flame selection excludes grey stone, lower warm logs and other tiles', () => {
  const pixels = fixture(), mask = flameMask(pixels);
  assert.equal(mask[100 * SIZE + 130], 1);
  assert.equal(mask[110 * SIZE + 85], 0);
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
    assert.deepEqual([...frame.slice(pixel(85, 110), pixel(85, 110) + 4)], [125, 120, 110, 255]);
  }
  assert.deepEqual(pixels, original);
});

test('empty flame mask leaves the whole object unchanged', () => {
  const pixels = new Uint8ClampedArray(SIZE * SIZE * 4).fill(80);
  assert.deepEqual([...rippleFrame(pixels, new Uint8Array(SIZE * SIZE), 8)], [...pixels]);
});

test('all ON frames reuse the exact OFF base outside their isolated flame layer', () => {
  const original = originalCampfire(), before = new Uint8ClampedArray(original);
  const mask = flameMask(original), blank = new Uint8ClampedArray(original.length);
  const base = new Uint8ClampedArray(original.length);
  for (let y = 103; y < SIZE; y++) for (let x = 10; x < 246; x++) base.set([85, 80, 72, 255], pixel(x, y));
  for (let frame = 0; frame < FRAMES; frame++) {
    const flame = rippleFrame(original, mask, frame, blank);
    const on = rippleFrame(original, mask, frame, base);
    let lit = 0;
    for (let offset = 0; offset < original.length; offset += 4) {
      if (!flame[offset + 3]) {
        assert.deepEqual([...on.subarray(offset, offset + 4)], [...base.subarray(offset, offset + 4)], `base changed in frame ${frame} at pixel ${offset / 4}`);
      } else {
        lit++;
      }
    }
    assert.ok(lit > 2000, 'each ON frame must contain the original flame');
    assert.deepEqual([...on.subarray(pixel(0, 184))], [...base.subarray(pixel(0, 184))]);
  }
  assert.deepEqual(original, before, 'compositing must not mutate the original atlas');
});

test('real flame mask includes neutral top outlines but excludes source ring and log ends', () => {
  const original = originalCampfire(), mask = flameMask(original);
  let outlined = 0;
  for (let y = 24; y < 103; y++) for (let x = 80; x < 180; x++) {
    const offset = pixel(x, y);
    if (!original[offset + 3]) continue;
    assert.equal(mask[y * SIZE + x], 1);
    if (original[offset] - original[offset + 2] < 55) outlined++;
  }
  assert.ok(outlined > 50, 'neutral antialiased outlines must move with the flame');
  for (const [x, y] of [[80, 110], [178, 119], [72, 168], [178, 168], [110, 194], [149, 196]]) assert.equal(mask[y * SIZE + x], 0);
});

test('2D OFF tile aspect-fits intact base art and caches it without carving the atlas', () => {
  const localWindow = {}, draws = [], canvases = [], atlas = {}, source = { naturalWidth: 8, naturalHeight: 4 };
  const sourcePixels = new Uint8ClampedArray(8 * 4 * 4);
  for (let y = 1; y < 3; y++) for (let x = 2; x < 6; x++) sourcePixels.set([80, 72, 68, 255], (y * 8 + x) * 4);
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../src/frontend/forest-fire.js'), 'utf8'), {
    window: localWindow,
    document: { createElement: type => {
      assert.equal(type, 'canvas');
      const canvas = { getContext: () => ({ drawImage: (...args) => draws.push(args), getImageData: () => ({ data: sourcePixels }) }) };
      canvases.push(canvas);
      return canvas;
    } },
  });
  const tile = localWindow.ForestFire.offTile(atlas, source);
  assert.equal(tile, canvases[1]);
  assert.equal(localWindow.ForestFire.offTile(atlas, source), tile);
  assert.deepEqual(draws, [[source, 0, 0], [canvases[0], 0, 0, 8, 4, -108, 69, 472, 236]]);
  assert.equal(tile.width, 256);
  assert.equal(tile.height, 256);
  assert.equal(canvases.length, 2);
  assert.throws(() => localWindow.ForestFire.offTile(atlas), /base artwork is required/);
  assert.deepEqual({ ...alphaBounds(sourcePixels, 8, 4) }, { x: 2, y: 1, width: 4, height: 2 });
  assert.deepEqual({ ...fitBase({ width: 400, height: 200 }) }, { x: 10, y: 128, width: 236, height: 118 });
});

test('real imagegen base uses solid alpha bounds instead of its faint outer halo', () => {
  const { pixels, width, height } = readPng('carrot-forest-campfire-base-v5.png');
  assert.equal(width, 1536);
  assert.equal(height, 1024);
  assert.equal(pixels[3], 0);
  const solid = alphaBounds(pixels, width, height), halo = alphaBounds(pixels, width, height, 8);
  assert.ok(solid.width > 900 && solid.height > 550);
  assert.ok(solid.width < halo.width && solid.height < halo.height);
  const target = fitBase(solid);
  assert.ok(target.width >= 230 && target.height >= 135, 'stone body fills the original ring footprint');
  assert.equal(target.y + target.height, 246, 'bottom anchor stays identical to the original tile');
  assert.ok(Math.abs(target.width / target.height - solid.width / solid.height) < 0.015, 'aspect ratio must not stretch');
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
