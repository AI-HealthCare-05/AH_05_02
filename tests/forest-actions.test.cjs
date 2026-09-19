const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const root = path.join(__dirname, '..');
const manifest = JSON.parse(readFileSync(path.join(root, 'src/frontend/assets/lpc-pack/manifest.json')));
const code = readFileSync(path.join(root, 'src/frontend/lpc-avatar-engine.js'), 'utf8').replace(
  'window.LpcAvatarEngine = {',
  'window.testEngine = { resolvedAnimation, selectedLayers, images }; window.LpcAvatarEngine = {'
);
async function setup() {
  const window = { dispatchEvent() {} };
  vm.runInNewContext(code, { window, fetch: async () => ({ ok: true, json: async () => manifest }), CustomEvent: class {}, console });
  await window.LpcAvatarEngine.ready();
  for (const record of manifest.items) for (const layers of Object.values(record.sources)) {
    for (const layer of layers) window.testEngine.images.set(layer.file, { file: layer.file });
  }
  return window;
}
const avatar = (weapon = 'none', tool = 'none') => ({ gender: 'female', cosmetics: {
  bodyType: 'female', lpcWeapon: weapon, lpcTool: tool, lpcArms: 'none',
  lpcEyes: 'none', lpcNose: 'none', lpcWrinkles: 'none', lpcHat: 'none', lpcGlasses: 'none',
} });
function render(window, person, options) {
  const calls = [];
  const ctx = new Proxy({ drawImage: (...args) => calls.push(args) }, { get: (target, key) => target[key] || (() => {}) });
  window.LpcAvatarEngine.draw(ctx, person, options, { width: 192, height: 192 });
  return calls;
}
test('wand always casts; empty weapon and tool have different unarmed actions', async () => {
  const w = await setup();
  assert.equal(w.testEngine.resolvedAnimation(avatar('wand'), { pose: 'attack' }), 'spellcast');
  assert.equal(w.testEngine.resolvedAnimation(avatar('bow'), { pose: 'attack' }), 'shoot');
  assert.equal(w.testEngine.selectedLayers(avatar('bow'), { pose: 'attack' }).some(l => l.category === 'weapon'), true);
  assert.equal(w.testEngine.resolvedAnimation(avatar(), { pose: 'attack' }), 'spellcast');
  assert.equal(w.testEngine.resolvedAnimation(avatar(), { pose: 'harvest' }), 'thrust');
  for (const person of [avatar(), avatar('wand')]) {
    assert.equal(w.testEngine.selectedLayers(person, { pose: 'attack' }).some(l => l.category === 'weapon'), false);
  }
  assert.equal(w.testEngine.selectedLayers(avatar(), { pose: 'harvest' }).some(l => l.category === 'tool'), false);
  assert.equal(w.testEngine.selectedLayers(avatar('bow','axe'), {}).some(l => ['tool','weapon'].includes(l.category)), false);
});
test('axe, hammer and pickaxe thrust like a shovel using held tools, without overhead layers', async () => {
  const w = await setup();
  for (const tool of ['axe', 'hammer', 'pickaxe']) {
    for (let i = 0; i < 8; i++) {
      const calls = render(w, avatar('none', tool), { pose:'harvest', direction:'down', progress:(i+.1)/8 });
      const body = calls.find(c => c[0].file.startsWith('body-'));
      const props = calls.filter(c => c[0].file.startsWith('tool-'));
      assert.equal(body[1] / 64, i);
      assert.equal(body[2] / 64, manifest.animationRows.thrust + 2);
      assert.equal(props.length, 1);
      assert.equal(props[0][3], 64);
      assert.equal(props[0][1], 0);
      assert.equal(props[0][2] / 64, manifest.animationRows.walk + 2);
      assert.equal(props[0][6], [0,-1,-2,2,7,7,3,0][i] * 3);
    }
  }
});
test('watering holds pouring frame; actions start at zero and do not wrap at completion', async () => {
  const w = await setup();
  const calls = render(w, avatar('none','watering_can'), {pose:'harvest',progress:.5});
  assert.equal(calls.find(c => c[0].file.startsWith('body-'))[1] / 64, 4);
  assert.equal(calls.find(c => c[0].file.startsWith('tool-'))[1] / 64, 4);
  for (const [progress, expected] of [[0,0],[1,6]]) {
    const body = render(w, avatar('wand'), {pose:'attack',progress,frame:100}).find(c => c[0].file.startsWith('body-'));
    assert.equal(body[1] / 64, expected);
    assert.equal(body[2] / 64, manifest.animationRows.spellcast + 2);
  }
  for (const tool of ['hoe','shovel']) assert.equal(w.testEngine.resolvedAnimation(avatar('none',tool), {pose:'harvest'}), 'thrust');
});
