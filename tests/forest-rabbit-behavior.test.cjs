const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const ForestAnimals = require('../src/frontend/forest-animals.js');
const source = readFileSync(path.join(__dirname, '../src/frontend/forest-phaser.js'), 'utf8');

// Synthetic metadata keeps behavior tests runnable without redistributing the
// licensed PNGs. The real source manifest is also exercised below.
const fixtureVariants = [
  { id: 'bunbun', key: 'test-bunbun', label: 'Bunbun', scale: 1.8,
    actions: ['idle', 'jump_up', 'jump_forward', 'jump_front', 'jump_back', 'kick', 'sleep', 'dig'] },
  { id: 'last-tick', key: 'test-last-tick', label: 'Last tick', scale: 1.8,
    actions: ['idle', 'walk', 'sleep', 'dig', 'kick', 'jump'] },
];
const fixtureAnimals = {
  ...ForestAnimals,
  rabbitVariants: fixtureVariants,
  rabbitAssets: fixtureVariants.map(variant => ({ key: variant.key, url: `/test/${variant.id}.png`, frameWidth: 32, frameHeight: 32 })),
  rabbitAction(id, name) {
    if (!fixtureVariants.find(variant => variant.id === id)?.actions.includes(name)) return null;
    return { name, durationMs: 2000, loop: name === 'idle' || name === 'sleep',
      moves: ['walk', 'jump', 'jump_forward', 'jump_front', 'jump_back'].includes(name),
      direction: name === 'jump_front' ? 'down' : name === 'jump_back' ? 'up' : undefined };
  },
  rabbitPose(id, { action, direction, elapsedMs, reducedMotion }) {
    const variant = fixtureVariants.find(item => item.id === id);
    return { key: variant.key, frame: variant.actions.indexOf(action) * 4 + (reducedMotion ? 0 : Math.floor(elapsedMs / 500) % 4),
      originX: .5, originY: 1, scale: variant.scale, flipX: direction === 'left', done: elapsedMs >= 2000 };
  },
};

function actor(x = 0, y = 0) {
  return {
    x, y, width: 32, height: 32, scaleX: 1, scaleY: 1, angle: 0, visible: true, handlers: {},
    input: { hitArea: { width: 32, height: 32 } },
    setPosition(x, y) { this.x = x; this.y = y; return this; },
    setOrigin(x, y = x) { this.originX = x; this.originY = y; return this; },
    setScale(x, y = x) { this.scaleX = x; this.scaleY = y; return this; },
    setAngle(value) { this.angle = value; return this; },
    setAlpha(value) { this.alpha = value; return this; },
    setDepth(value) { this.depth = value; return this; },
    setVisible(value) { this.visible = value; return this; },
    setInteractive() { return this; },
    on(name, callback) { this.handlers[name] = callback; return this; },
    setFrame(value) { this.frame = value; return this; },
    setTexture(value, frame) {
      this.texture = value; this.frame = frame;
      this.width = this.height = value === 'forest-rabbit' ? 72 : 32;
      return this;
    },
    setFlipX(value) { this.flipX = value; return this; },
    setY(value) { this.y = value; return this; },
    destroy() { this.destroyed = true; },
  };
}

function setup({ animals = fixtureAnimals, loaded = animals.rabbitVariants?.map(variant => variant.key) || [] } = {}) {
  let reduced = false;
  const events = [], listeners = new Map();
  const Phaser = {
    Scene: class {}, AUTO: 0, Scale: { FIT: 1, CENTER_BOTH: 1 },
    Game: class { constructor(config) { this.config = config; } },
    Math: { Between: minimum => minimum, Distance: { Between: (x1, y1, x2, y2) => Math.hypot(x2 - x1, y2 - y1) } },
    Utils: { Array: { GetRandom: values => values.includes('rabbit') ? 'rabbit' : values[0] } },
  };
  const window = {
    Phaser, ForestAnimals: animals, ForestObjects: { INDIVIDUAL_ASSETS: [] },
    matchMedia: () => ({ matches: reduced }), dispatchEvent: event => events.push(event),
    addEventListener: (type, handler) => listeners.set(type, handler), removeEventListener() {},
  };
  vm.runInNewContext(source, {
    window, Phaser, document: { getElementById: () => ({ focus() {} }), querySelector: () => null },
    localStorage: { getItem: () => null }, performance: { now: () => 1000 },
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options?.detail; } },
  });
  const scene = new window.carrotForestPhaserGame.config.scene();
  scene.ratActor = actor(420, 350);
  scene.ratSprite = actor();
  scene.ratShadow = actor();
  scene.textures = { exists: key => loaded.includes(key) };
  scene.add = { text: (x, y) => actor(x, y) };
  scene.tweens = { add() {} };
  scene.time = { now: 1000 };
  scene.isBlocked = () => false;
  scene.ratTurnAt = Infinity;
  scene.ratDespawnAt = Infinity;
  scene.ratActive = true;
  scene.avatar = { x: 400, y: 350, direction: 'right', cosmetics: {} };
  return { scene, events, listeners, window, setReduced: value => { reduced = value; } };
}

test('optional rabbit packs preload separately and loaded variants alternate without starvation', () => {
  const { scene } = setup();
  const sheets = [];
  scene.load = { image() {}, spritesheet: (...args) => sheets.push(args) };
  scene.preload();
  for (const asset of fixtureAnimals.rabbitAssets) {
    assert.ok(sheets.some(([key, url, options]) => key === asset.key && url === asset.url && options.frameWidth === 32));
  }
  const variants = [];
  for (let i = 0; i < 6; i++) {
    scene.setRatSpecies('rabbit');
    variants.push(scene.rabbitVariant);
    scene.setRatSpecies('mouse');
  }
  assert.deepEqual(variants, ['bunbun', 'last-tick', 'bunbun', 'last-tick', 'bunbun', 'last-tick']);
});

test('unavailable licensed sheets retain LPC fallback, original mouse scale, and pointer listeners', () => {
  const { scene } = setup({ loaded: [] });
  const hover = () => {};
  scene.ratSprite.on('pointerover', hover);
  scene.setRatSpecies('rabbit');
  assert.equal(scene.rabbitVariant, null);
  assert.equal(scene.ratSprite.texture, 'forest-rabbit');
  assert.equal(scene.ratSprite.scaleX, 1.35);
  assert.equal(scene.ratSprite.input.hitArea.width, 72);
  scene.setRatSpecies('mouse');
  assert.equal(scene.ratSprite.texture, 'lpc-rat');
  assert.equal(scene.ratSprite.scaleX, 1.4);
  assert.equal(scene.ratSprite.originY, 1);
  assert.equal(scene.ratSprite.flipX, false);
  assert.equal(scene.ratSprite.input.hitArea.width, 32);
  assert.equal(scene.ratSprite.handlers.pointerover, hover);
  const onePack = setup({ loaded: ['test-last-tick'] }).scene;
  for (let i = 0; i < 3; i++) {
    onePack.setRatSpecies('rabbit');
    assert.equal(onePack.rabbitVariant, 'last-tick');
  }
});

function assertBehaviorSequence(animals) {
  for (const variant of animals.rabbitVariants) {
    const { scene } = setup({ animals });
    scene.setRatSpecies('rabbit', variant.id, 1000);
    assert.equal(scene.rabbitVariant, variant.id);
    const observed = [];
    let time = 1000;
    for (const name of variant.actions) {
      const action = animals.rabbitAction(variant.id, name);
      const before = [scene.ratActor.x, scene.ratActor.y];
      scene.updateRat(time + 1, 40);
      observed.push(scene.rabbitBehaviorSequence[scene.rabbitActionIndex].name);
      if (action.moves) assert.notDeepEqual([scene.ratActor.x, scene.ratActor.y], before, `${variant.id}/${name} travels`);
      else assert.deepEqual([scene.ratActor.x, scene.ratActor.y], before, `${variant.id}/${name} stays in place`);
      assert.equal(scene.ratSprite.texture, variant.key);
      assert.ok(Number.isInteger(scene.ratSprite.frame) && scene.ratSprite.frame >= 0);
      assert.deepEqual([scene.ratSprite.x, scene.ratSprite.y, scene.ratSprite.angle], [0, 0, 0], 'no whole-body wobble');
      assert.equal(scene.ratSprite.scaleX, scene.ratSprite.scaleY);
      assert.equal(scene.ratSprite.originY, 1);
      time += action.durationMs;
    }
    assert.deepEqual(observed, Array.from(variant.actions), `${variant.id} exposes every source action`);
    assert.ok(time - 1000 <= 43800, 'the complete sequence fits the bounded encounter');
    scene.updateRat(time + 1, 40);
    assert.equal(scene.rabbitBehaviorSequence[scene.rabbitActionIndex].name, variant.actions[0]);
  }
}

test('all actions have finite turns; sleeping, digging, kicking and vertical jumping never glide', () => {
  assertBehaviorSequence(fixtureAnimals);
});

test('the production source manifests expose every action through the same live scene behavior', () => {
  assert.ok(ForestAnimals.rabbitVariants?.length >= 2, 'both requested source packs have behavior metadata');
  assertBehaviorSequence(ForestAnimals);
});

test('every populated production rabbit cell reaches the live renderer during its finite sequence', () => {
  for (const variant of ForestAnimals.rabbitVariants) {
    const { scene } = setup({ animals: ForestAnimals });
    scene.setRatSpecies('rabbit', variant.id, 1000);
    let time = 1000;
    const observed = new Set(), expected = new Set();
    for (const name of variant.actions) {
      const action = ForestAnimals.rabbitAction(variant.id, name);
      action.frames.forEach(frame => expected.add(frame));
      for (let elapsed = 1; elapsed < action.durationMs; elapsed += action.frameMs) {
        scene.updateRat(time + elapsed, 16);
        observed.add(scene.ratSprite.frame);
      }
      time += action.durationMs;
    }
    assert.deepEqual([...observed].sort((a, b) => a - b), [...expected].sort((a, b) => a - b), variant.id);
    assert.equal(observed.size, variant.id === 'bunbun' ? 18 : 219);
  }
});

test('blocked eight-direction hops keep a matching stationary source view', () => {
  const { scene } = setup({ animals: ForestAnimals });
  scene.setRatSpecies('rabbit', 'last-tick', 1000);
  scene.setRabbitAction('hop_up_left', 1000);
  scene.isBlocked = () => true;
  scene.updateRat(1100, 40);
  assert.equal(scene.ratDirection, 'up_left');
  assert.equal(scene.ratSprite.frame, ForestAnimals.rabbitAction('last-tick', 'pose_up_left').frames[0]);
});

test('source-locked front/back jumps travel in their matching direction, while blocked motion holds idle', () => {
  const { scene } = setup();
  scene.setRatSpecies('rabbit', 'bunbun', 1000);
  scene.setRabbitAction('jump_front', 1000);
  scene.ratTurnAt = 0;
  scene.ratDirection = 'left';
  const before = [scene.ratActor.x, scene.ratActor.y];
  scene.updateRat(1100, 40);
  assert.equal(scene.ratDirection, 'down');
  assert.equal(scene.ratActor.x, before[0]);
  assert.ok(scene.ratActor.y > before[1]);
  scene.isBlocked = () => true;
  const blocked = [scene.ratActor.x, scene.ratActor.y];
  scene.updateRat(1200, 40);
  assert.deepEqual([scene.ratActor.x, scene.ratActor.y], blocked);
  assert.equal(scene.ratSprite.frame, 0, 'blocked travel shows the still idle pose');
  scene.setRabbitAction('jump_back', 1300);
  assert.equal(scene.ratDirection, 'up');
});

test('diagonal source actions use normalized travel and switching back to a mouse restores cardinal movement', () => {
  const animals = { ...fixtureAnimals, rabbitAction(id, name) {
    const action = fixtureAnimals.rabbitAction(id, name);
    return action && name === 'jump' ? { ...action, direction: 'up_right' } : action;
  } };
  const { scene } = setup({ animals });
  scene.setRatSpecies('rabbit', 'last-tick', 1000);
  scene.setRabbitAction('jump', 1000);
  scene.ratTurnAt = 0;
  const before = [scene.ratActor.x, scene.ratActor.y];
  scene.updateRat(1100, 40);
  const dx = scene.ratActor.x - before[0], dy = scene.ratActor.y - before[1];
  assert.equal(scene.ratDirection, 'up_right');
  assert.ok(dx > 0 && dy < 0);
  assert.ok(Math.abs(dx + dy) < 1e-9);
  assert.ok(Math.abs(Math.hypot(dx, dy) - .92) < 1e-9, 'diagonal travel has the same 23px/sec speed');
  scene.setRatSpecies('mouse', null, 1200);
  assert.equal(scene.ratDirection, 'down');
  scene.ratTurnAt = Infinity;
  const mouseX = scene.ratActor.x;
  scene.updateRat(1300, 40);
  assert.equal(scene.ratActor.x, mouseX);
});

test('reduced motion keeps source frames still without disabling behavior', () => {
  const { scene, setReduced } = setup();
  scene.setRatSpecies('rabbit', 'bunbun', 1000);
  scene.setRabbitAction('dig', 1000);
  setReduced(true);
  scene.updateRat(1100, 40);
  const before = [scene.ratActor.x, scene.ratActor.y, scene.ratSprite.frame, scene.ratSprite.scaleX];
  scene.updateRat(1800, 40);
  assert.deepEqual([scene.ratActor.x, scene.ratActor.y, scene.ratSprite.frame, scene.ratSprite.scaleX], before);
});

test('encounters announce their variant and last long enough for every finite source action', () => {
  const { scene, events } = setup();
  scene.spawnRat(1000);
  assert.equal(scene.ratSpecies, 'rabbit');
  assert.equal(scene.ratDespawnAt, 18200);
  assert.equal(events[0].type, 'forest-rat-appeared');
  assert.equal(events[0].detail.variant, 'bunbun');
  assert.equal(events[0].detail.variantLabel, 'Bunbun');
  scene.spawnRat(3000);
  assert.equal(scene.rabbitVariant, 'last-tick');
  assert.equal(events[1].detail.eventId, events[0].detail.eventId + 1);
});

test('explicit variant and action state updates select supported poses without a new reward event', () => {
  const { scene, events, listeners } = setup();
  scene.attachWindowEvents();
  listeners.get('forest-state-updated')({ detail: { rat: { species: 'rabbit', variant: 'last-tick', action: 'sleep' } } });
  assert.equal(scene.rabbitVariant, 'last-tick');
  assert.equal(scene.rabbitBehaviorSequence[scene.rabbitActionIndex].name, 'sleep');
  assert.equal(scene.setRabbitAction('not-a-source-action', 1000), false);
  assert.equal(events.length, 0);
});

test('both new rabbit variants preserve one manual or automatic pet reward through the existing event', () => {
  for (const variant of fixtureVariants) for (const method of ['manual', 'pet']) {
    const { scene, events } = setup();
    scene.setRatSpecies('rabbit', variant.id, 1000);
    scene.ratEventId = 7;
    scene.ratActor.setPosition(420, 350);
    if (method === 'manual') {
      scene.tryAttackRat(5000);
      scene.tryAttackRat(5500);
    } else {
      scene.pet = actor(420, 350);
      scene.petEmoji = actor().setVisible(false);
      scene.petFollowX = 420;
      scene.petFollowY = 350;
      scene.updatePet(5000, 40, false);
      scene.updatePet(5500, 40, false);
    }
    const catches = events.filter(event => event.type === 'forest-rat-caught');
    assert.equal(catches.length, 1, `${variant.id}/${method}`);
    assert.equal(catches[0].detail.species, 'rabbit');
    assert.equal(catches[0].detail.eventId, 7);
    assert.equal(catches[0].detail.amount, 5);
    assert.equal(catches[0].detail.source, method === 'pet' ? 'pet' : undefined);
    assert.equal(scene.ratActive, false);
  }
});

test('rabbit appearance text is color-neutral and includes the supplied source label', () => {
  const game = readFileSync(path.join(__dirname, '../src/frontend/forest-game.js'), 'utf8');
  const handlers = new Map(), messages = [];
  vm.runInNewContext(game.slice(game.indexOf('  let currentWildEncounter = null;'), game.indexOf('  window.addEventListener("forest-placement-confirm"')), {
    window: { addEventListener: (name, callback) => handlers.set(name, callback) },
    setStatus: message => messages.push(message), state: { avatar: { cosmetics: {} } },
  });
  handlers.get('forest-rat-appeared')({ detail: { species: 'rabbit', variantLabel: 'Bunbun' } });
  assert.match(messages[0], /토끼.*Bunbun/);
  assert.doesNotMatch(messages[0], /하얀/);
});
