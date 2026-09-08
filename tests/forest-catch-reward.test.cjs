const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const source = readFileSync(path.join(__dirname, '../src/frontend/forest-game.js'), 'utf8');

function setup() {
  const listeners = new Map();
  const labels = new Map([
    ['#carrot-balance', { textContent: '30' }],
    ['#preview-carrot-balance', { textContent: '30' }],
  ]);
  const state = { carrots: 30, avatar: { cosmetics: {} } };
  const saves = [];
  const sounds = [];
  const begin = source.indexOf('  let currentWildEncounter = null;');
  const end = source.indexOf('  window.addEventListener("forest-placement-confirm"', begin);
  assert.ok(begin >= 0 && end > begin, 'the production encounter handlers must be present');
  vm.runInNewContext(source.slice(begin, end), {
    window: { addEventListener: (type, callback) => listeners.set(type, callback) },
    $: (selector) => labels.get(selector) || null,
    state,
    setStatus() {},
    playSfx: (name, options) => sounds.push({ name, ...options }),
    persist: async (message) => saves.push({ carrots: state.carrots, message }),
  });
  return { listeners, labels, state, saves, sounds };
}

test('manual rabbit and pet mouse catches persist rewards without the removed profile counter', async () => {
  for (const encounter of [
    { species: 'rabbit', message: '야생 토끼와 만나 당근 5개를 얻었습니다!', rate: 1 },
    { species: 'mouse', source: 'pet', message: '펫이 가까운 야생 쥐를 자동으로 잡아 당근 5개를 가져왔습니다!', rate: 1.08 },
  ]) {
    const { listeners, labels, state, saves, sounds } = setup();
    assert.equal(labels.has('#profile-carrots'), false);
    await listeners.get('forest-rat-caught')({
      detail: { eventId: 7, amount: 5, species: encounter.species, source: encounter.source },
    });
    assert.equal(state.carrots, 35);
    assert.equal(labels.get('#carrot-balance').textContent, '35');
    assert.equal(labels.get('#preview-carrot-balance').textContent, '35');
    assert.deepEqual(saves, [{ carrots: 35, message: encounter.message }]);
    assert.equal(sounds[0].name, 'rat-caught');
    assert.equal(sounds[0].rate, encounter.rate);
  }
});

test('a catch without a species keeps the active rabbit encounter reward message', async () => {
  const { listeners, saves } = setup();
  listeners.get('forest-rat-appeared')({ detail: { eventId: 8, species: 'rabbit' } });
  await listeners.get('forest-rat-caught')({ detail: { eventId: 8, amount: 5 } });
  assert.deepEqual(saves, [{ carrots: 35, message: '야생 토끼와 만나 당근 5개를 얻었습니다!' }]);
});

test('reward handlers no longer reference the removed profile carrot counter', () => {
  assert.doesNotMatch(source, /#profile-carrots/);
});
