const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../src/frontend/forest-game.js'), 'utf8');
const functions = source.slice(source.indexOf('  function placementCellValid('), source.indexOf('  function placementEventDetail('));

function setup(code = 'animated_fountain', placed = []) {
  const context = vm.createContext({
    currentScene: 'world', placementCode: code, waterObjectCodes: new Set(['duck_float']),
    WORLD_WIDTH: 768, WORLD_HEIGHT: 512, state: { placed },
    window: { ForestRiverDuck: require('../src/frontend/forest-riverduck.js'), ForestMemories: { CAMERA: { x: 694, y: 338, width: 52, height: 76 } } },
    blocked() { throw new Error('Decorative traversal collision must not reserve grass'); },
  });
  vm.runInContext(functions, context);
  return context;
}

test('fountain belongs on free land; only a floating duck is restricted to the pond', () => {
  assert.match(source, /const waterObjectCodes = new Set\(\["duck_float"\]\)/);
  const fountain = setup();
  assert.equal(fountain.placementCellValid(384, 320), true);
  assert.equal(fountain.placementCellValid(128, 400), false);
  const duck = setup('duck_float');
  assert.equal(duck.placementCellValid(384, 320), false);
  assert.equal(duck.placementCellValid(128, 400), true);
  assert.equal(duck.placementCellValid(180, 410), false, 'the wooden dock is not water');
  assert.equal(duck.placementCellValid(45, 380), false, 'the complete contact footprint must clear the bank');
});

test('world boundaries, house, garden, pond, and occupied cells prevent placement', () => {
  const context = setup('bench');
  for (const [x, y] of [[32, 320], [32, 32], [384, 320], [576, 352], [736, 480]]) {
    assert.equal(context.placementCellValid(x, y), true, `${x},${y} grass`);
  }
  for (const [x, y] of [[192, 128], [576, 128], [128, 400], [0, 320], [384, 510], [NaN, 320]]) {
    assert.equal(context.placementCellValid(x, y), false, `${x},${y} reserved`);
  }
  context.currentScene = 'home';
  assert.equal(context.placementCellValid(384, 320), false);
});

test('adjacent 32px grass cells are usable but actual overlapping centers remain blocked', () => {
  const context = setup('bench', [{ code: 'lantern', x: 416, y: 320 }]);
  assert.equal(context.placementCellValid(384, 320), true);
  assert.equal(context.placementCellValid(416, 320), false);
  assert.equal(context.placementCellValid(400, 320), false);
  context.state.placed = [{ code: 'bench', x: 416, y: 320 }];
  assert.equal(context.placementCellValid(416, 320), true, 'moving the selected item must not collide with itself');
  assert.ok(context.placementGridCells().some(cell => cell.x === 32 && cell.y === 32 && cell.valid));
});

test('the permanent camera reserves only overlapping tripod-foot cells and preserves adjacent lawn', () => {
  const context = setup('bench');
  for (const [x, y] of [[694, 338], [672, 320], [704, 320], [672, 352], [704, 352]]) {
    assert.equal(context.placementCellValid(x, y), false, `${x},${y} overlaps camera feet`);
  }
  for (const [x, y] of [[640, 320], [736, 320], [640, 352], [736, 352], [672, 288], [704, 288], [672, 384], [704, 384]]) {
    assert.equal(context.placementCellValid(x, y), true, `${x},${y} adjacent grass stays usable`);
  }
  assert.equal(context.placementGridCells().filter(cell => !cell.valid && cell.x >= 640 && cell.y >= 288 && cell.y <= 384).length, 4);
  context.window.ForestMemories.CAMERA = { x: 416, y: 320 };
  assert.equal(context.placementCellValid(416, 320), false, 'the shared camera center is authoritative');
  assert.equal(context.placementCellValid(694, 338), true, 'the old center is not permanently hardcoded');
});
