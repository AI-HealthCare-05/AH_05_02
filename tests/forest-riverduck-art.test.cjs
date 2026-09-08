const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const art = require('../src/frontend/forest-riverduck-art.js');
const frontend = path.join(__dirname, '../src/frontend');

test('six original transparent frames and CC0 provenance ship locally and in the offline pack', () => {
  assert.equal(art.assets.length, 6);
  const worker = fs.readFileSync(path.join(frontend, 'forest-sw.js'), 'utf8');
  for (const asset of art.assets) {
    const name = asset.url.split('?')[0].replace('/static/', '');
    const png = fs.readFileSync(path.join(frontend, name));
    assert.equal(png.toString('ascii', 1, 4), 'PNG');
    assert.deepEqual([png.readUInt32BE(16), png.readUInt32BE(20)], [96, 96]);
    assert.equal(asset.frameWidth, 96); assert.equal(asset.frameHeight, 96);
    assert.ok(worker.includes(path.basename(name, '.png')));
  }
  const source = fs.readFileSync(path.join(frontend, 'assets/animals/riverduck-v160/SOURCE.md'), 'utf8');
  for (const text of ['CC0', 'Ulti', 'https://opengameart.org/content/character-spritesheet-duck', 'SHA-256']) assert.ok(source.includes(text));
});

test('idle, swimming and fleeing use actual source frames with stable contact and scale', () => {
  const keys = new Set();
  for (const moving of [false, true]) for (const fleeing of [false, true]) for (const direction of ['left', 'right', 'up', 'down']) {
    for (let t = 0; t < 2000; t += 60) {
      const pose = art.pose({moving, fleeing, direction, headingX: 1}, t);
      keys.add(pose.key);
      assert.ok(art.assets.some(asset => asset.key === pose.key));
      assert.equal(pose.frame, 0); assert.equal(pose.originY, 87 / 96);
      assert.equal(pose.scale, .75); assert.equal(pose.flipX, direction === 'left');
    }
  }
  assert.equal(keys.size, 6);
  assert.equal(art.pose({}, NaN).index, 0);
});

test('fallback masks only submerged feet and thumbnail includes the whole visible head and body', () => {
  const calls = [];
  const context = {save() {}, restore() {}, translate(...args) {calls.push(['translate', ...args]);},
    scale(...args) {calls.push(['scale', ...args]);}, drawImage(...args) {calls.push(['drawImage', ...args]);}};
  const image = {complete: true, naturalWidth: 96};
  art.draw(context, image, {direction: 'left'}, 7, 8);
  assert.deepEqual(calls[0], ['translate', 7, 8]);
  assert.deepEqual(calls[1], ['scale', -.75, .75]);
  assert.deepEqual(calls[2].slice(2, 6), [0, 0, 96, 87]);
  calls.length = 0;
  art.thumbnail(context, image, 96, 96);
  assert.deepEqual(calls[0].slice(2, 6), [15, 45, 51, 42]);
  assert.equal(art.hitTest({x: 100, y: 400}, 100, 385), true);
  assert.equal(art.hitTest({x: 100, y: 400}, 150, 385), false);
});
