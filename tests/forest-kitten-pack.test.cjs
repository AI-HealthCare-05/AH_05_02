const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');
const pets = require('../src/frontend/forest-pets.js');
const root = path.join(__dirname, '..');
const directions = ['down', 'up', 'left', 'right', 'down_left', 'down_right', 'up_left', 'up_right'];

test('free kittens expose all three original coats and every free holiday equipment sheet, never paid source paths', () => {
  assert.deepEqual(pets.catalog.map(item => item.id), ['last_tick_white', 'last_tick_gray', 'last_tick_ginger']);
  assert.equal(pets.equipment.length, 16);
  assert.deepEqual(pets.equipment.slice(0, 5).map(item => item.id),
    ['none', 'winter_antlers_green', 'winter_antlers_red', 'winter_santa_hat_1', 'winter_santa_hat_2']);
  assert.equal(pets.equipment.filter(item => item.id.startsWith('valentine_')).length, 11);
  assert.equal(pets.definition('blue_eyes_white_cat').key, pets.definition('last_tick_white').key);
  assert.equal(pets.definition('gold_eyes_orange_cat').key, pets.definition('last_tick_ginger').key);
  assert.equal(pets.definition('lpc_brown_dog').supportsSit, false);
  assert.equal(pets.pose('none'), null);
  for (const asset of pets.assets) {
    assert.deepEqual([asset.frameWidth, asset.frameHeight, asset.columns, asset.rows], [32, 32, 11, 53]);
    assert.match(asset.url, /licensed-kittens\/(white|gray|ginger|winter-|valentine-)/);
  }
  assert.equal(pets.assets.length, 18);
  const installer = fs.readFileSync(path.join(root, 'scripts/import_forest_kittens.ps1'), 'utf8');
  assert.match(installer, /'Free pack.zip'='15289409'/);
  assert.match(installer, /'Winter accessories.zip'='16035254'/);
  assert.match(installer, /'14 feb.zip'='16045897'/);
  assert.match(installer, /\$matching.Count -ne 1/);
  assert.match(installer, /\$archive.GetEntry\(\$EntryName\)/);
  assert.match(fs.readFileSync(path.join(root, '.gitignore'), 'utf8'), /animals\/licensed-kittens\//);
});

test('every kitten action stays in an occupied authored cell with a synchronized bow and fixed feet', () => {
  for (const pet of pets.catalog) for (const direction of directions) for (const action of ['idle', 'sit', 'walk', 'feed', 'attack']) {
    for (let elapsed = 0; elapsed < 24000; elapsed += 55) {
      const pose = pets.pose(pet.id, { action, direction, elapsed });
      assert.ok(Number.isInteger(pose.frame) && pose.frame >= 0 && pose.frame < 583);
      assert.ok(pose.frame % 11 < pets.rowFrameCounts[Math.floor(pose.frame / 11)], `${pet.id}/${action}/${direction}/${elapsed}`);
      assert.equal(pose.originY, 26 / 32);
      assert.equal(pose.scale, 1.2);
      if (pose.overlay) {
        assert.equal(pose.overlay.frame, pose.frame);
        assert.equal(pose.overlay.originY, pose.originY);
      }
    }
  }
});

test('idle advances through the requested 10s, 30s, 60s, 90s and 120s authored rest stages', () => {
  const frames = new Set(Array.from({ length: 240 }, (_, index) => pets.pose('last_tick_white', { action: 'idle', elapsed: index * 50 }).frame));
  for (const row of [28, 32, 36]) assert.ok([...frames].some(frame => Math.floor(frame / 11) === row));
  for (const [idleMs, clip, row] of [[10000, 'sit', 0], [30000, 'paws_tucked', 12], [60000, 'sleep_sitting', 14],
    [90000, 'sleep_head_down', 16], [120000, 'sleep_stretched', 18]]) {
    const pose = pets.pose('last_tick_white', { action: 'idle', direction: 'down', elapsed: idleMs, idleMs });
    assert.equal(pose.clip, clip);
    assert.equal(Math.floor(pose.frame / 11), row);
  }
  const still = Array.from({ length: 50 }, (_, i) => pets.pose('last_tick_ribbon', { action: 'walk', elapsed: i * 150, reducedMotion: true }).frame);
  assert.equal(new Set(still).size, 1);
  assert.ok(still[0] < 6);
});

// Optional local-byte audit: CI needs no redistributable copy of creator art.
function rgba(filename) {
  const png = fs.readFileSync(filename), chunks = [];
  const width = png.readUInt32BE(16), height = png.readUInt32BE(20);
  assert.deepEqual([width, height, png[24], png[25]], [352, 1696, 8, 6]);
  for (let offset = 8; offset < png.length;) {
    const length = png.readUInt32BE(offset);
    if (png.toString('ascii', offset + 4, offset + 8) === 'IDAT') chunks.push(png.subarray(offset + 8, offset + 8 + length));
    offset += length + 12;
  }
  const packed = zlib.inflateSync(Buffer.concat(chunks)), stride = width * 4, pixels = new Uint8Array(stride * height);
  const paeth = (a, b, c) => { const p = a + b - c, x = Math.abs(p - a), y = Math.abs(p - b), z = Math.abs(p - c); return x <= y && x <= z ? a : y <= z ? b : c; };
  for (let y = 0; y < height; y++) for (let x = 0; x < stride; x++) {
    const left = x >= 4 ? pixels[y * stride + x - 4] : 0, up = y ? pixels[(y - 1) * stride + x] : 0;
    const diagonal = x >= 4 && y ? pixels[(y - 1) * stride + x - 4] : 0;
    const prediction = [0, left, up, Math.floor((left + up) / 2), paeth(left, up, diagonal)][packed[y * (stride + 1)]];
    pixels[y * stride + x] = (packed[y * (stride + 1) + x + 1] + prediction) & 255;
  }
  return { width, pixels };
}
const files = pets.assets.map(asset => path.join(root, 'src/frontend', asset.url.split('?')[0].replace('/static/', '')));
test('installed original PNGs contain every body frame and each official equipment layer has visible authored cells', { skip: files.some(file => !fs.existsSync(file)) ? 'Install creator free packs locally; source PNGs are not public Git fixtures.' : false }, () => {
  const usedFrames = new Set();
  for (const direction of directions) for (const action of ['idle', 'sit', 'walk', 'feed', 'attack']) for (let elapsed = 0; elapsed < 24000; elapsed += 55) {
    usedFrames.add(pets.pose('last_tick_ribbon', { action, direction, elapsed }).frame);
  }
  for (const [fileIndex, file] of files.entries()) {
    const { pixels, width } = rgba(file);
    let visibleRuntimeFrames = 0;
    for (const frame of usedFrames) {
      let visible = 0;
      for (let y = 0; y < 32; y++) for (let x = 0; x < 32; x++) visible += pixels[((Math.floor(frame / 11) * 32 + y) * width + frame % 11 * 32 + x) * 4 + 3] > 0;
      if (fileIndex < 3) assert.ok(visible > 0, `${path.basename(file)} frame ${frame}`);
      if (visible > 0) visibleRuntimeFrames++;
    }
    assert.ok(visibleRuntimeFrames > 0, `${path.basename(file)} has no visible runtime equipment cells`);
  }
});
