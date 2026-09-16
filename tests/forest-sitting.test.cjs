const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.join(__dirname, '..');
const game = fs.readFileSync(path.join(root, 'src/frontend/forest-game.js'), 'utf8');
const engine = fs.readFileSync(path.join(root, 'src/frontend/lpc-avatar-engine.js'), 'utf8');

function sittingContext(scene) {
  const statuses = [];
  const persisted = [];
  const context = vm.createContext({
    currentScene: scene,
    state: { avatar: { sitting: false, mounted: false, sitVariant: 'field', x: 10, y: 10 }, placed: [] },
    seatObjectCodes: new Set(['chair_green', 'chair_red', 'bench']),
    setStatus: message => statuses.push(message),
    playSfx() {},
    renderCanvas() {},
    persist: async message => persisted.push(message),
    sitAtPlacedObject: async () => { throw new Error('unexpected seat snap'); },
    Math,
  });
  const start = game.indexOf('  async function toggleSit()');
  const end = game.indexOf('  async function sitAtPlacedObject', start);
  vm.runInContext(game.slice(start, end), context);
  return { context, statuses, persisted };
}

test('sit is a single on/off toggle with distinct field and home variants', async () => {
  const field = sittingContext('world');
  await vm.runInContext('toggleSit()', field.context);
  assert.equal(field.context.state.avatar.sitting, true);
  assert.equal(field.context.state.avatar.sitVariant, 'field');
  await vm.runInContext('toggleSit()', field.context);
  assert.equal(field.context.state.avatar.sitting, false);

  const home = sittingContext('home');
  await vm.runInContext('toggleSit()', home.context);
  assert.equal(home.context.state.avatar.sitting, true);
  assert.equal(home.context.state.avatar.sitVariant, 'home');
  assert.match(home.persisted[0], /집 안/);
});

test('garden rejects sitting without changing avatar state', async () => {
  const garden = sittingContext('garden');
  await vm.runInContext('toggleSit()', garden.context);
  assert.equal(garden.context.state.avatar.sitting, false);
  assert.equal(garden.persisted.length, 0);
  assert.match(garden.statuses[0], /메인 필드와 집 안/);
});

test('LPC sitting holds different stable frames indoors and outdoors', () => {
  const start = engine.indexOf('  function stableSitFrame(');
  const end = engine.indexOf('  const wingMobilityIds', start);
  const context = vm.createContext({});
  vm.runInContext(engine.slice(start, end), context);
  const cycle = [0, 0, 1, 1, 2, 2];
  assert.equal(vm.runInContext(`stableSitFrame({ sitVariant: "field" }, [${cycle}])`, context), 2);
  assert.equal(vm.runInContext(`stableSitFrame({ sitVariant: "home" }, [${cycle}])`, context), 1);
});
