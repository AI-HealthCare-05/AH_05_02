const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const animals = require('../src/frontend/forest-animals.js');
const base = path.join(__dirname, '../src/frontend');

test('downloaded sheets have the documented complete frame grid', () => {
  for (const asset of animals.assets) {
    const filename = path.join(base, asset.url.replace('/static/', ''));
    const data = fs.readFileSync(filename);
    assert.equal(data.subarray(1, 4).toString(), 'PNG');
    assert.equal(data.readUInt32BE(16), asset.frameWidth * 4);
    assert.equal(data.readUInt32BE(20), asset.frameHeight * (asset.key === 'forest-rabbit' ? 8 : 4));
    assert.equal(data[25], 6, 'RGBA transparent complete-body sprites');
  }
});

test('cow is stationary before touch and returns to the exact idle frame after one reaction', () => {
  const idle = animals.cowFrame();
  assert.equal(idle.frame, 4);
  assert.equal(idle.done, true);
  const frames = [];
  for (let elapsed = 0; elapsed < animals.cowReactionDurationMs; elapsed += 170) {
    const sample = animals.cowFrame(elapsed);
    assert.equal(sample.done, false);
    assert.equal(sample.originY, idle.originY);
    frames.push(sample.frame);
  }
  assert.deepEqual(frames, [4, 5, 6, 7, 7, 6, 5, 4]);
  assert.deepEqual(animals.cowFrame(animals.cowReactionDurationMs), idle);
  assert.deepEqual(animals.cowFrame(600000), idle);
  assert.equal('scale' in idle || 'x' in idle || 'y' in idle, false, 'no body bob or scale deformation');
});

test('cow reduced-motion mode keeps its original pose throughout interaction', () => {
  for (const elapsed of [0, 170, 700, 1359, 1360]) {
    assert.equal(animals.cowFrame(elapsed, { reducedMotion: true }).frame, 4);
  }
});

test('rabbit uses four directional hopping and separate grazing rows', () => {
  for (const [row, direction] of ['up', 'left', 'down', 'right'].entries()) {
    assert.deepEqual([0, 140, 280, 420].map(time => animals.rabbitFrame(direction, true, time).frame),
      [row * 4, row * 4 + 1, row * 4 + 2, row * 4 + 3]);
    assert.equal(animals.rabbitFrame(direction, false, 0).frame, (row + 4) * 4);
    assert.equal(animals.rabbitFrame(direction, true, 500, true).frame, row * 4);
  }
});

test('frame rectangles stay inside their original sheets and reject invalid input', () => {
  for (const asset of animals.assets) {
    const total = asset.key === 'forest-rabbit' ? 32 : 16;
    for (let frame = 0; frame < total; frame++) {
      const rect = animals.frameRect(asset.key, frame);
      assert.ok(rect.x >= 0 && rect.x + rect.width <= asset.frameWidth * 4);
      assert.ok(rect.y >= 0 && rect.y + rect.height <= asset.frameHeight * total / 4);
    }
    for (const invalid of [-1, total, 0.5, NaN]) assert.equal(animals.frameRect(asset.key, invalid), null);
  }
  assert.equal(animals.frameRect('missing', 0), null);
});

test('real cow sound is local, never autoplays, respects mute, and throttles repeated touches', () => {
  const sound = fs.readFileSync(path.join(base, animals.mooUrl.replace('/static/', '')));
  assert.ok(sound.length > 1000);
  const instances = [];
  const context = vm.createContext({ window: { Audio: class {
    constructor(url) { this.url = url; this.plays = 0; instances.push(this); }
    pause() {}
    play() { this.plays++; return Promise.resolve(); }
  } } });
  vm.runInContext(fs.readFileSync(path.join(base, 'forest-animals.js'), 'utf8'), context);
  const api = context.window.ForestAnimals;
  assert.equal(instances.length, 0);
  assert.equal(api.playMoo({ enabled: false, nowMs: 0 }), false);
  assert.equal(instances.length, 0);
  assert.equal(api.playMoo({ nowMs: 0 }), true);
  assert.equal(api.playMoo({ nowMs: 100 }), false);
  assert.equal(api.playMoo({ nowMs: 1600, volume: 4 }), true);
  assert.equal(instances.length, 1);
  assert.equal(instances[0].plays, 2);
  assert.equal(instances[0].volume, 1);
});

test('source, creators and selected licenses ship with the assets', () => {
  const credits = fs.readFileSync(path.join(base, 'assets/animals/ATTRIBUTION.md'), 'utf8');
  for (const expected of ['Daniel Eddeland', 'Stephen Challener', 'Tebruno99', 'Evert', 'Joseph SARDIN',
    'CC BY 3.0', 'CC0 1.0', 'opengameart.org', 'bigsoundbank.com/cow-moos-6-s2386.html']) {
    assert.ok(credits.includes(expected), expected);
  }
});
