const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const code = fs.readFileSync(path.join(__dirname, '../src/frontend/forest-game.js'), 'utf8');

function setup(pose, missing = []) {
  const calls = [], transforms = [];
  const dimensions = { 'lpc-pets': [288, 128] };
  const sheet = key => ({ key, complete: !missing.includes(key), naturalWidth: (dimensions[key] || [352, 1696])[0], naturalHeight: (dimensions[key] || [352, 1696])[1] });
  const target = {
    save() { transforms.push('save'); }, restore() { transforms.push('restore'); },
    translate(x, y) { transforms.push([x, y]); }, scale(x, y) { transforms.push([x, y]); },
    drawImage(...args) { calls.push(args); },
  };
  const c = vm.createContext({ window: { ForestPets: { pose: () => pose } },
    petSpriteImages: new Map(['kitten', 'bow'].map(key => [key, sheet(key)])), catPetAtlas: sheet('lpc-pets') });
  vm.runInContext(code.slice(code.indexOf('  function catPetSpriteIndex'), code.indexOf('  function drawAtlasCell')), c);
  return { draw: (id = 'last_tick_ribbon') => c.drawPetFrame(target, id, {}, 48, 84, 88), target, calls, transforms };
}

test('preview draws actual 32px kitten cell and matching bow overlay without resampling', () => {
  const s = setup({ key: 'kitten', frame: 23, flipX: true, originX: .5, originY: .875, overlay: { key: 'bow', frame: 23 } });
  assert.equal(s.draw(), true);
  assert.deepEqual(s.calls.map(call => [call[0].key, ...call.slice(1, 5)]), [['kitten', 32, 64, 32, 32], ['bow', 32, 64, 32, 32]]);
  assert.equal(s.target.imageSmoothingEnabled, false);
  assert.equal(s.transforms.filter(value => value === 'save').length, 2);
  assert.equal(s.transforms.filter(value => value === 'restore').length, 2);
});

test('absent optional art falls back to the existing companion and none draws nothing', () => {
  const s = setup({ key: 'kitten', frame: 1 }, ['kitten', 'bow']);
  assert.equal(s.draw('last_tick_ginger'), true);
  assert.deepEqual([s.calls[0][0].key, ...s.calls[0].slice(1, 5)], ['lpc-pets', 128, 0, 32, 32]);
  assert.equal(s.draw('none'), false);
  assert.equal(s.calls.length, 1);
});

test('out-of-range optional cells do not paint adjacent sprites or a full sheet', () => {
  const s = setup({ key: 'kitten', frame: 9999 });
  assert.equal(s.draw(), true);
  assert.equal(s.calls[0][0].key, 'lpc-pets');
});

test('a ribbon-only load failure chooses the same bundled fallback as Phaser and photos', () => {
  const s = setup({ key: 'kitten', frame: 1, overlay: { key: 'bow', frame: 1 } }, ['bow']);
  assert.equal(s.draw(), true);
  assert.equal(s.calls.length, 1);
  assert.equal(s.calls[0][0].key, 'lpc-pets');
});

test('live LPC canvas, studio, and menu all use shared pet rendering', () => {
  const avatar = code.slice(code.indexOf('  function drawAvatar()'), code.indexOf('  function drawSceneEffects'));
  assert.ok(avatar.indexOf('drawPetFrame(context') < avatar.indexOf('    return;'));
  const studio = code.slice(code.indexOf('  function renderAvatarPreview()'), code.indexOf('  function drawPreviewAccessoryOverlay'));
  assert.match(studio, /drawPetFrame\(previewContext, avatarDraft.pet/);
  assert.match(code, /data-pet-thumb="\$\{itemId\}"/);
  assert.match(code, /thumbnail.dataset.petThumb/);
  assert.match(code, /\.\.\.\(window.ForestPets\?\.catalog \|\| \[\]\)/);
});

test('older saved IDs preview the same animated frame as their canonical pet without loading a static portrait', () => {
  const pets = require('../src/frontend/forest-pets.js');
  for (const [oldId, id] of Object.entries(pets.aliases)) {
    const pose = pets.pose(oldId, { action: 'walk', elapsed: 400 });
    const canonical = pets.pose(id, { action: 'walk', elapsed: 400 });
    if (oldId === 'last_tick_ribbon') {
      assert.equal(pose.overlay.key, 'forest-kitten-valentine-bow-red');
      assert.deepEqual({ ...pose, overlay: undefined }, { ...canonical, overlay: undefined });
    } else assert.deepEqual(pose, canonical);
    const previewPose = { ...pose, key: pose.key === 'lpc-pets' ? pose.key : 'kitten' };
    if (previewPose.overlay) previewPose.overlay = { ...previewPose.overlay, key: 'bow' };
    const s = setup(previewPose);
    assert.equal(s.draw(oldId), true);
    assert.equal(s.calls[0][0].key, previewPose.key);
    assert.deepEqual(s.calls[0].slice(3, 5), [32, 32]);
  }
});

test('all three existing LPC walkers retain their 32px preview frames', () => {
  const pets = require('../src/frontend/forest-pets.js');
  for (const pet of pets.classicCatalog) {
    const pose = pets.pose(pet.id, { action: 'walk', direction: 'right', elapsed: 160 });
    const s = setup(pose);
    assert.equal(s.draw(pet.id), true);
    assert.deepEqual([s.calls[0][0].key, ...s.calls[0].slice(1, 5)], ['lpc-pets', (pose.frame % 9) * 32, 64, 32, 32]);
  }
});
