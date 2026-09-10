const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const animals = require('../src/frontend/forest-animals.js');

const expectedVariantIds = [
  'bunbun', 'last-tick', 'bunbun-cream', 'bunbun-brown', 'bunbun-black',
  'last-tick-white', 'last-tick-cream', 'last-tick-brown',
];

// Hand-verified source-cell metadata, not licensed image fixtures. Keeping this
// test independent of PNGs makes it runnable from a clean public clone.
const lastTickRowCounts = [
  8, 6, 6, 6, 6, 6, 6, 6, 6, 6, 2, 2, 2, 2, 2, 2,
  9, 9, 9, 9, 9, 9, 9, 9, 9, 4, 8, 5, 6, 8, 5, 6, 11, 11,
];
const bunbunFrames = {
  idle: [0, 2], jump_up: [4, 6], jump_forward: [10, 11],
  jump_front: [8, 9], jump_back: [12, 13], kick: [16, 18],
  sleep: [20, 22], dig: [24, 25, 26, 27],
};
const expectedLastTickNames = [
  'pose_down', 'pose_up', 'pose_left', 'pose_right',
  'pose_down_left', 'pose_down_right', 'pose_up_right', 'pose_up_left',
  'pose_stretched_left', 'pose_stretched_right', 'pose_loaf_left',
  'pose_loaf_right', 'pose_flat_left', 'pose_flat_right',
  'hop_down', 'hop_up', 'hop_right', 'hop_left',
  'hop_down_left', 'hop_down_right', 'hop_up_right', 'hop_up_left',
  'rest_stretched_left', 'rest_stretched_right', 'rest_loaf_left',
  'rest_loaf_right', 'rest_flat_left', 'rest_flat_right',
  'head_lower_down', 'head_lower_up', 'head_lower_left', 'head_lower_right',
  'head_lower_down_left', 'head_lower_down_right', 'head_lower_up_right', 'head_lower_up_left',
  'look_around', 'upright_bob', 'ear_flick_1', 'ear_flick_2', 'ear_flick_3',
  'ear_flick_4', 'ear_flick_5', 'ear_flick_6', 'head_tilt_1', 'head_tilt_2',
];
const sortFrames = frames => [...frames].sort((a, b) => a - b);
const actionsFor = id => animals.rabbitVariants.find(variant => variant.id === id).actions
  .map(name => animals.rabbitAction(id, name));
const everyAction = () => animals.rabbitVariants.flatMap(variant =>
  actionsFor(variant.id).map(action => ({ variant, action })));

test('rabbit metadata loads with no image, audio, network or licensed-file access', () => {
  const forbidden = () => { throw new Error('metadata import must not load external assets'); };
  const context = vm.createContext({
    module: { exports: {} }, Image: forbidden, Audio: forbidden, fetch: forbidden,
    require: forbidden,
  });
  const source = fs.readFileSync(path.join(__dirname, '../src/frontend/forest-animals.js'), 'utf8');
  vm.runInContext(source, context);
  const api = context.module.exports;
  assert.equal(api.rabbitVariants.length, 8);
  assert.equal(api.rabbitPose('bunbun', { action: 'dig' }).frame, 24);
  assert.equal(api.rabbitPose('last-tick', { action: 'head_tilt_2' }).frame, 363);
});

test('eight rabbit variants reuse only two optional source sheets and their exact action lists', () => {
  assert.deepEqual(animals.rabbitVariants.map(variant => variant.id).sort(), [...expectedVariantIds].sort());
  assert.equal(animals.rabbitAssets.length, 2, 'generated colors do not request additional licensed files');
  assert.equal(new Set(animals.rabbitVariants.map(variant => variant.key)).size, 8);
  for (const variant of animals.rabbitVariants) {
    const family = variant.id.startsWith('bunbun') ? 'bunbun' : 'last-tick';
    const original = animals.rabbitVariants.find(item => item.id === family);
    assert.equal(variant.family, family);
    assert.equal(variant.sourceKey, original.key);
    assert.equal(variant.generated, variant.id !== family);
    assert.deepEqual(variant.actions, family === 'bunbun' ? Object.keys(bunbunFrames) : expectedLastTickNames);
    assert.equal(variant.actions.length, family === 'bunbun' ? 8 : 46);
    assert.equal(variant.scale, original.scale);
    assert.ok(Object.isFrozen(variant) && Object.isFrozen(variant.actions));
  }
  for (const [id, columns, frameCount] of [['bunbun', 4, 32], ['last-tick', 11, 374]]) {
    const variant = animals.rabbitVariants.find(item => item.id === id);
    const asset = animals.rabbitAssets.find(item => item.key === variant.key);
    assert.ok(asset, `${id} has a registered optional source asset`);
    assert.equal(asset.frameWidth, 32);
    assert.equal(asset.frameHeight, 32);
    assert.equal(asset.columns, columns);
    assert.equal(asset.frameCount, frameCount);
    assert.match(asset.url, /\/licensed-rabbits\/[^/]+\.png(?:\?|$)/);
    assert.ok(Object.isFrozen(variant) && Object.isFrozen(variant.actions));
  }
});

test('Bunbun maps all 18 rabbit cells exactly once and never animates carrot or blank tiles', () => {
  for (const [name, frames] of Object.entries(bunbunFrames)) {
    assert.deepEqual(animals.rabbitAction('bunbun', name).frames, frames, name);
  }
  const actual = actionsFor('bunbun').flatMap(action => action.frames);
  const expected = [0, 2, 4, 6, 8, 9, 10, 11, 12, 13, 16, 18, 20, 22, 24, 25, 26, 27];
  assert.equal(actual.length, 18);
  assert.equal(new Set(actual).size, 18);
  assert.deepEqual(sortFrames(actual), expected);
  for (const excluded of [1, 3, 5, 7, 14, 15, 17, 19, 21, 23, 28, 29, 30, 31]) {
    assert.equal(actual.includes(excluded), false, `tile ${excluded} is blank or ancillary carrot art`);
  }
});

test('Last tick covers exactly 219 occupied cells across all 34 source rows', () => {
  const expected = lastTickRowCounts.flatMap((count, row) =>
    Array.from({ length: count }, (_, column) => row * 11 + column));
  const actual = actionsFor('last-tick').flatMap(action => action.frames);
  assert.equal(expected.length, 219);
  assert.equal(actual.length, 219);
  assert.equal(new Set(actual).size, 219, 'no cell is omitted by replacing it with a duplicate');
  assert.deepEqual(sortFrames(actual), expected);
  for (const [row, count] of lastTickRowCounts.entries()) {
    assert.equal(actual.filter(frame => Math.floor(frame / 11) === row).length, count, `row ${row}`);
  }
  // Static directional/rest poses occupy the first two rows individually;
  // every remaining animation stays inside its corresponding source row.
  for (const [index, action] of actionsFor('last-tick').entries()) {
    if (index < 14) assert.equal(action.frames.length, 1, action.name);
    else {
      const row = index - 12;
      assert.deepEqual(action.frames,
        Array.from({ length: lastTickRowCounts[row] }, (_, column) => row * 11 + column), action.name);
    }
  }
});

test('frameRect honors original and generated sheet columns and validates complete sheet bounds', () => {
  for (const variant of animals.rabbitVariants) {
    const asset = animals.rabbitAssets.find(item => item.key === variant.sourceKey);
    const width = asset.columns * 32;
    const height = asset.frameCount / asset.columns * 32;
    for (let frame = 0; frame < asset.frameCount; frame++) {
      const rect = animals.frameRect(variant.key, frame);
      assert.deepEqual(rect, {
        x: frame % asset.columns * 32,
        y: Math.floor(frame / asset.columns) * 32,
        width: 32, height: 32,
      });
      assert.ok(rect.x >= 0 && rect.x + rect.width <= width);
      assert.ok(rect.y >= 0 && rect.y + rect.height <= height);
    }
    for (const invalid of [-1, asset.frameCount, asset.frameCount + 1, 0.5, NaN, Infinity, -Infinity, '0', null, undefined]) {
      assert.equal(animals.frameRect(variant.key, invalid), null, `${variant.key}: ${String(invalid)}`);
    }
  }
  assert.deepEqual(animals.frameRect('forest-rabbit-last-tick', 10), { x: 320, y: 0, width: 32, height: 32 });
  assert.deepEqual(animals.frameRect('forest-rabbit-last-tick', 11), { x: 0, y: 32, width: 32, height: 32 });
  assert.deepEqual(animals.frameRect('forest-rabbit-last-tick', 373), { x: 320, y: 1056, width: 32, height: 32 });
  assert.deepEqual(animals.frameRect('forest-rabbit-bunbun', 31), { x: 96, y: 224, width: 32, height: 32 });
  assert.equal(animals.frameRect('missing-rabbit-pack', 0), null);
});

test('every source action has valid finite application timing and fits the 43.8-second encounter budget', () => {
  for (const variant of animals.rabbitVariants) {
    let total = 0;
    for (const action of actionsFor(variant.id)) {
      assert.ok(Object.isFrozen(action) && Object.isFrozen(action.frames), action.name);
      assert.ok(typeof action.label === 'string' && action.label.trim().length > 0);
      assert.ok(Number.isSafeInteger(action.frameMs) && action.frameMs > 0, action.name);
      assert.ok(Number.isSafeInteger(action.durationMs) && action.durationMs > 0, action.name);
      const repeats = action.repeats ?? 1;
      assert.ok(Number.isSafeInteger(repeats) && repeats >= 1);
      assert.equal(action.durationMs, action.frames.length * action.frameMs * repeats, action.name);
      assert.equal(action.loop, repeats > 1, action.name);
      assert.equal(typeof action.moves, 'boolean');
      total += action.durationMs;
    }
    assert.ok(total > 0 && total <= 43800, `${variant.id}: ${total} ms`);
  }
});

test('rabbitPose advances every original frame in order including finite repeats', () => {
  for (const { variant, action } of everyAction()) {
    const steps = action.durationMs / action.frameMs;
    for (let step = 0; step < steps; step++) {
      const pose = animals.rabbitPose(variant.id, { action: action.name, elapsedMs: step * action.frameMs });
      assert.equal(pose.frame, action.frames[step % action.frames.length], `${variant.id}/${action.name}/${step}`);
      assert.equal(pose.done, false);
      assert.equal(pose.key, variant.key);
      assert.equal(pose.scale, variant.scale);
      assert.equal(pose.originX, 0.5);
      assert.equal(pose.originY, 1);
      assert.ok(animals.frameRect(pose.key, pose.frame));
    }
  }
});

test('negative and non-finite elapsed times safely resolve to the first unfinished pose', () => {
  for (const { variant, action } of everyAction()) {
    const first = animals.rabbitPose(variant.id, { action: action.name, elapsedMs: 0 });
    for (const elapsedMs of [-1000, -0.1, NaN, Infinity, -Infinity, undefined, '100', null]) {
      assert.deepEqual(animals.rabbitPose(variant.id, { action: action.name, elapsedMs }), first,
        `${variant.id}/${action.name}/${String(elapsedMs)}`);
    }
    assert.equal(first.frame, action.frames[0]);
    assert.equal(first.done, false);
  }
});

test('finished actions clamp to the final source frame rather than wrapping or overflowing', () => {
  for (const { variant, action } of everyAction()) {
    const before = animals.rabbitPose(variant.id, { action: action.name, elapsedMs: action.durationMs - 1 });
    assert.equal(before.frame, action.frames.at(-1));
    assert.equal(before.done, false);
    for (const elapsedMs of [action.durationMs, action.durationMs + 1, action.durationMs * 10, Number.MAX_SAFE_INTEGER]) {
      const pose = animals.rabbitPose(variant.id, { action: action.name, elapsedMs });
      assert.equal(pose.frame, action.frames.at(-1), `${variant.id}/${action.name}/${elapsedMs}`);
      assert.equal(pose.done, true);
    }
  }
});

test('reduced motion always uses the first source pose while preserving completion state', () => {
  for (const { variant, action } of everyAction()) {
    for (const elapsedMs of [0, action.frameMs, action.durationMs - 1, action.durationMs, action.durationMs + 10000]) {
      const pose = animals.rabbitPose(variant.id, { action: action.name, elapsedMs, reducedMotion: true });
      assert.equal(pose.frame, action.frames[0], `${variant.id}/${action.name}`);
      assert.equal(pose.done, elapsedMs >= action.durationMs);
      assert.equal(pose.scale, variant.scale);
    }
  }
});

test('Bunbun source directions separate travel from stationary actions and only mirror side poses', () => {
  const moving = { jump_forward: 'right', jump_front: 'down', jump_back: 'up' };
  const directions = ['left', 'right', 'up', 'down', 'up_left', 'up_right', 'down_left', 'down_right'];
  for (const action of actionsFor('bunbun')) {
    assert.equal(action.moves, Object.hasOwn(moving, action.name), action.name);
    if (action.moves) assert.equal(action.direction, moving[action.name]);
    const fixedArt = ['jump_front', 'jump_back', 'dig'].includes(action.name);
    for (const direction of directions) {
      const pose = animals.rabbitPose('bunbun', { action: action.name, direction, elapsedMs: action.frameMs });
      assert.equal(pose.flipX, !fixedArt && direction.includes('left'), `${action.name}/${direction}`);
      assert.equal(pose.frame, action.frames[1], 'mirroring does not substitute another action or pose');
    }
  }
});

test('Last tick retains all eight original movement directions without mirrored source frames', () => {
  const expectedDirections = ['down', 'up', 'left', 'right', 'down_left', 'down_right', 'up_right', 'up_left'];
  for (const direction of expectedDirections) {
    assert.equal(animals.rabbitAction('last-tick', `pose_${direction}`).direction, direction);
    assert.equal(animals.rabbitAction('last-tick', `hop_${direction}`).direction, direction);
    assert.equal(animals.rabbitAction('last-tick', `head_lower_${direction}`).direction, direction);
  }
  for (const action of actionsFor('last-tick')) {
    assert.equal(action.moves, action.name.startsWith('hop_'), action.name);
    assert.ok(expectedDirections.includes(action.direction), action.name);
    for (const requestedDirection of expectedDirections) {
      const pose = animals.rabbitPose('last-tick', {
        action: action.name, direction: requestedDirection, elapsedMs: 0,
      });
      assert.equal(pose.flipX, false, `${action.name}/${requestedDirection}`);
      assert.equal(pose.frame, action.frames[0], 'the source action controls its artwork direction');
    }
  }
});

test('unsupported variants and action lookups fail safely while unknown actions use the default pose', () => {
  assert.equal(animals.rabbitAction('missing-pack', 'idle'), null);
  assert.equal(animals.rabbitAction('bunbun', 'missing-action'), null);
  assert.equal(animals.rabbitPose('missing-pack'), null);
  for (const variant of animals.rabbitVariants) {
    const first = animals.rabbitAction(variant.id, variant.actions[0]);
    assert.deepEqual(animals.rabbitPose(variant.id, { action: 'missing-action' }), animals.rabbitPose(variant.id));
    assert.equal(animals.rabbitPose(variant.id).frame, first.frames[0]);
  }
});
