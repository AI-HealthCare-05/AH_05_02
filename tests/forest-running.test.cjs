const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const source = name => readFileSync(path.join(__dirname, '../src/frontend', name), 'utf8');
const game = source('forest-game.js');
const phaser = source('forest-phaser.js');

test('run mode toggles one shared state and updates all buttons', () => {
  const attributes = {};
  const context = vm.createContext({
    window: {},
    document: { querySelectorAll: () => [{ setAttribute: (key, value) => { attributes[key] = value; } }] },
    setStatus: () => {},
  });
  const toggle = game.slice(game.indexOf('  function toggleRunning()'), game.indexOf('  async function moveAvatar('));
  vm.runInContext(`let running = false; ${toggle}; toggleRunning();`, context);
  assert.equal(context.window.carrotForestRunning, true);
  assert.equal(attributes['aria-pressed'], 'true');
  vm.runInContext('toggleRunning()', context);
  assert.equal(context.window.carrotForestRunning, false);
  assert.equal(attributes['aria-pressed'], 'false');
  assert.ok(!game.includes('running: avatar.running'));
});

test('Phaser R ignores auto-repeat and dispatches the same toggle as the button', () => {
  const events = [];
  const context = vm.createContext({
    window: { dispatchEvent: event => events.push(event.detail) },
    CustomEvent: class { constructor(type, options) { this.detail = options.detail; } },
    formFocused: () => false,
    input: { keyboard: { on: (name, handler) => { context.handler = handler; } } },
  });
  const keyHandler = phaser.slice(phaser.indexOf('      this.input.keyboard.on("keydown-R"'), phaser.indexOf('      this.input.keyboard.on("keydown-X"'));
  vm.runInContext(keyHandler, context);
  context.handler({ repeat: false, preventDefault() {} });
  context.handler({ repeat: true, preventDefault() {} });
  assert.deepEqual(events, ['run']);
  assert.ok(game.includes('if (event.detail === "run") toggleRunning()'));
  assert.ok(!phaser.includes('this.keys.R.isDown'));
});

test('button-mode running drives actual Phaser distance, pose and footsteps without held R', () => {
  const update = phaser.slice(phaser.indexOf('    update(time, delta) {'), phaser.indexOf('    spawnRat(time) {'));
  const context = vm.createContext({
    window: { carrotForestRunning: false, dispatchEvent: event => sounds.push(event.detail.name) },
    document: { activeElement: { tagName: 'BUTTON' } },
    performance: { now: () => 10 },
    CustomEvent: class { constructor(type, options) { this.detail = options.detail; } },
  });
  const sounds = [];
  const frames = [];
  const scene = {
    sceneName: 'world', forcedUntil: 100, forcedDirection: 'right',
    avatar: { x: 384, y: 410, mounted: false }, lastStepSfxAt: 0,
    player: { setPosition() { return this; }, setDepth() {} },
    updateWorldAtmosphere() {}, updatePlacedObjectMotion() {}, updateRat() {}, updatePet() {}, emitPosition() {},
    isBlocked: () => false,
    setPremiumFrame: (...args) => frames.push(args),
  };
  const tick = vm.runInContext(`({ ${update} }).update`, context);
  tick.call(scene, 1000, 20);
  const walkingDistance = scene.avatar.x - 384;
  scene.avatar.x = 384;
  context.window.carrotForestRunning = true;
  tick.call(scene, 2000, 20);
  assert.ok(Math.abs(walkingDistance - 1.84) < 0.00001);
  assert.equal(scene.avatar.x - 384, 3);
  assert.equal(frames[0][3], false);
  assert.equal(frames[1][3], true);
  assert.deepEqual(sounds, ['step-grass', 'run-grass']);
});
