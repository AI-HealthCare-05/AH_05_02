const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const pets = require('../src/frontend/forest-pets.js');
const code = fs.readFileSync(path.join(__dirname, '../src/frontend/forest-game.js'), 'utf8');

test('pet menu contains three LPC walkers, three free-color kittens and all free equipment without duplicate choices', () => {
  const start = code.indexOf('    pet: ['), end = code.indexOf('    speech: [', start);
  const menu = vm.runInNewContext(`({${code.slice(start, end)}}).pet`, { window: { ForestPets: pets } });
  const companions = menu.filter(item => item.slot === 'pet');
  const equipment = menu.filter(item => item.slot === 'petAccessory');
  assert.equal(menu.length, 23);
  assert.equal(new Set(menu.map(item => item.id)).size, menu.length);
  assert.deepEqual(pets.classicCatalog.map(pet => pet.id), ['lpc_white_cat', 'lpc_orange_cat', 'lpc_brown_dog']);
  assert.equal(companions.length, 7);
  assert.equal(companions[0].itemId, 'none');
  assert.equal(equipment.length, 16);
  assert.ok(pets.catalog.every(pet => pet.group === '고양이'));
  assert.ok(pets.classicCatalog.every(pet => pet.group === '강아지'));
  assert.ok(pets.equipment.every(item => item.group === '펫 장비'));
  for (const pet of companions.slice(1)) {
    assert.ok(!pet.static);
    assert.ok(!Object.hasOwn(pets.aliases, pet.itemId), 'compatibility IDs do not duplicate menu cards');
    assert.notEqual(pets.pose(pet.itemId, { action: 'walk', elapsed: 0 }).frame,
      pets.pose(pet.itemId, { action: 'walk', elapsed: 160 }).frame);
  }
});

test('static portrait loading and frame registration are absent while source PNG files are preserved', () => {
  for (const property of ['legacyCatalog', 'legacyAssets', 'registerLegacyFrames']) assert.equal(pets[property], undefined);
  const moduleSource = fs.readFileSync(path.join(__dirname, '../src/frontend/forest-pets.js'), 'utf8');
  const phaser = fs.readFileSync(path.join(__dirname, '../src/frontend/forest-phaser.js'), 'utf8');
  for (const source of [moduleSource, phaser]) assert.doesNotMatch(source, /forest-original-pets|forest-original-cats|registerLegacyFrames/);
  for (const filename of ['carrot-forest-cosmetics-atlas-v1.png', 'carrot-forest-cat-pets-v1.png']) {
    assert.ok(fs.existsSync(path.join(__dirname, '../src/frontend/assets', filename)));
    assert.ok(!pets.assets.some(asset => asset.url.includes(filename)));
  }
});

test('old saved IDs resolve only to animated pets without mutating saved data', () => {
  const expected = { white_pup: 'lpc_brown_dog', brown_pup: 'lpc_brown_dog', cat: 'lpc_white_cat', fox: 'lpc_orange_cat',
    blue_eyes_white_cat: 'last_tick_white', gold_eyes_orange_cat: 'last_tick_ginger', last_tick_ribbon: 'last_tick_white' };
  assert.deepEqual(pets.aliases, expected);
  for (const [oldId, id] of Object.entries(expected)) {
    const saved = Object.freeze({ pet: oldId });
    assert.equal(pets.canonicalId(saved.pet), id);
    assert.equal(pets.definition(saved.pet).id, id);
    const oldPose = pets.pose(saved.pet, { action: 'walk', elapsed: 160 });
    const newPose = pets.pose(id, { action: 'walk', elapsed: 160 });
    if (oldId === 'last_tick_ribbon') {
      assert.equal(oldPose.overlay.key, 'forest-kitten-valentine-bow-red');
      assert.equal(pets.pose(oldId, { action: 'walk', elapsed: 160, equipment: 'none' }).overlay.key,
        'forest-kitten-valentine-bow-red');
      delete oldPose.overlay;
    }
    assert.deepEqual(oldPose, newPose);
    assert.equal(saved.pet, oldId);
  }
  assert.equal(pets.canonicalId('none'), 'none');
  assert.equal(pets.definition('not-a-pet'), null);
});

test('studio selection resolves a saved alias to its current card without changing the draft', () => {
  const start = code.indexOf('  function selectedAvatarItem('), end = code.indexOf('\n  function ', start + 1);
  for (const [oldId, id] of Object.entries(pets.aliases)) {
    const avatarDraft = { pet: oldId };
    const context = vm.createContext({ window: { ForestPets: pets }, avatarDraft,
      avatarItemsForCategory: () => [{ id: 'pet:none', itemId: 'none', slot: 'pet' },
        ...[...pets.classicCatalog, ...pets.catalog].map(item => ({ ...item, id: `pet:${item.id}`, itemId: item.id, slot: 'pet' }))] });
    vm.runInContext(code.slice(start, end), context);
    assert.equal(context.selectedAvatarItem('pet').itemId, id);
    assert.equal(avatarDraft.pet, oldId);
  }
  assert.match(code, /itemSlot === "pet" \? window.ForestPets\?\.canonicalId\?\.\(avatarDraft.pet\)/);
});

test('existing LPC walkers preserve four directional three-frame gait and honest stopped gait cells', () => {
  for (const pet of pets.classicCatalog) {
    for (const [direction, row] of Object.entries({ down: 0, left: 1, right: 2, up: 3 })) {
      assert.deepEqual([0, 150, 300].map(elapsed => pets.pose(pet.id, { direction, action: 'walk', elapsed }).frame),
        [0, 1, 2].map(column => row * 9 + pet.fallbackColumn + column));
      for (const action of ['idle', 'sit', 'feed', 'attack']) {
        const pose = pets.pose(pet.id, { direction, action, elapsed: 400 });
        assert.equal(pose.frame, row * 9 + pet.fallbackColumn + 1);
        assert.equal(pose.action, 'idle');
        assert.equal(pose.supportsSit, false);
      }
    }
  }
});
