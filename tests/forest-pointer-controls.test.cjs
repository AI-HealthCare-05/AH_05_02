const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const source = readFileSync(path.join(__dirname, '../src/frontend/forest-phaser.js'), 'utf8');

function setup() {
  const events = [];
  const listeners = new Map();
  const document = {
    activeElement: { tagName: 'DIV' },
    getElementById: () => ({ focus() {} }),
    querySelector: () => null,
  };
  const Phaser = {
    Scene: class {}, AUTO: 0, Scale: { FIT: 1, CENTER_BOTH: 1 },
    Game: class { constructor(config) { this.config = config; } },
  };
  const window = {
    Phaser, dispatchEvent: (event) => events.push(event),
    matchMedia: () => ({ matches: false }),
    addEventListener: (type, handler) => listeners.set(type, handler),
    removeEventListener: (type) => listeners.delete(type),
  };
  const context = vm.createContext({
    window, document, Phaser, localStorage: { getItem: () => null },
    performance: { now: () => 2000 },
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options?.detail; } },
  });
  vm.runInContext(source, context);
  return { scene: new window.carrotForestPhaserGame.config.scene(), context, document, window, events, listeners };
}

function actor() {
  return {
    handlers: {}, visible: false,
    on(type, handler) { this.handlers[type] = handler; return this; },
    setOrigin(x, y = x) { this.originX = x; this.originY = y; return this; },
    setDepth(value) { this.depth = value; return this; }, setInteractive() { return this; },
    setVisible(value) { this.visible = value; return this; },
    setPosition(x, y) { this.x = x; this.y = y; return this; },
    setScale(x, y = x) { this.scaleX = x; this.scaleY = y; return this; },
  };
}

function attackFactory() {
  return {
    text(x, y, text, style) {
      return Object.assign(actor(), {
        x, y, text, style, width: style.fixedWidth, height: style.fixedHeight,
        setText(value) { this.text = value; return this; },
        setInteractive(options) {
          this.input = { hitArea: { x: 0, y: 0, width: this.width, height: this.height }, cursor: options.useHandCursor ? 'pointer' : '' };
          return this;
        },
      });
    },
    graphics() {
      return Object.assign(actor(), {
        commands: [],
        clear() { this.commands = []; return this; },
        fillStyle(...args) { this.commands.push(['fillStyle', ...args]); return this; },
        fillRoundedRect(...args) { this.commands.push(['fillRoundedRect', ...args]); return this; },
        fillPoints(...args) { this.commands.push(['fillPoints', ...args]); return this; },
        fillTriangle(...args) { this.commands.push(['fillTriangle', ...args]); return this; },
        lineStyle(...args) { this.commands.push(['lineStyle', ...args]); return this; },
        strokeRoundedRect(...args) { this.commands.push(['strokeRoundedRect', ...args]); return this; },
      });
    },
  };
}

test('world-space click targets arrive exactly, reject blocked positions and pause during placement', () => {
  const { scene } = setup();
  scene.avatar.x = 384;
  scene.avatar.y = 352;
  assert.equal(scene.requestMoveTo(410, 420), true);
  for (let i = 0; i < 100; i += 1) {
    const step = scene.pointerMovementStep(3, i * 20);
    if (step) Object.assign(scene.avatar, { x: step.x, y: step.y });
  }
  assert.equal(scene.avatar.x, 410);
  assert.equal(scene.avatar.y, 420);
  assert.equal(scene.movePath.length, 0);
  assert.equal(scene.requestMoveTo(120, 130), false);
  assert.equal(scene.requestMoveTo(NaN, 420), false);
  scene.placementActive = true;
  assert.equal(scene.requestMoveTo(450, 420), false);
});

test('path routes around blocked map geometry without clipping corners', () => {
  const { scene } = setup();
  scene.avatar.x = 350;
  scene.avatar.y = 150;
  const destination = { x: 700, y: 320 };
  assert.equal(scene.canWalkSegment(scene.avatar, destination), false);
  const route = scene.findMovePath(destination.x, destination.y);
  assert.ok(route.length > 1);
  let previous = scene.avatar;
  for (const point of route) {
    assert.equal(scene.canWalkSegment(previous, point), true);
    previous = point;
  }
  assert.equal(previous.x, destination.x);
  assert.equal(previous.y, destination.y);
});

test('the exact fractional destination is emitted once after the final throttled step', () => {
  const { scene, events } = setup();
  scene.avatar.x = 400;
  scene.avatar.y = 325;
  const destination = { x: 400.5, y: 319.75 };
  assert.equal(scene.requestMoveTo(destination.x, destination.y), true);
  events.length = 0;
  // performance.now stays constant in this harness, suppressing every ordinary
  // emitPosition() call; only the forced arrival update can reach the UI/store.
  for (let i = 0; i < 20; i += 1) {
    const step = scene.pointerMovementStep(1.84, 2000 + i * 20);
    if (step) {
      Object.assign(scene.avatar, { x: step.x, y: step.y });
      scene.emitPosition();
    }
  }
  const positions = events.filter(event => event.type === 'forest-phaser-position');
  assert.equal(positions.length, 1);
  assert.equal(positions[0].detail.x, destination.x);
  assert.equal(positions[0].detail.y, destination.y);
  assert.equal(scene.movePath.length, 0);
});

test('hover reveals attack and tapping the animal starts the same action as its button', () => {
  const { scene } = setup();
  scene.add = attackFactory();
  scene.ratSprite = actor();
  scene.ratActor = { x: 440, y: 350 };
  scene.ratActive = true;
  scene.createRatAttackButton();
  scene.updateRatAttackButton();
  assert.equal(scene.ratAttackButton.visible, false);
  scene.ratSprite.handlers.pointerover();
  scene.updateRatAttackButton();
  assert.equal(scene.ratAttackButton.visible, true);
  assert.equal(scene.ratAttackButton.x, 440);
  assert.equal(scene.ratAttackButton.y, 278);
  let stopped = 0;
  scene.ratSprite.handlers.pointerdown({ wasTouch: true }, 0, 0, { stopPropagation: () => stopped++ });
  assert.equal(stopped, 1);
  assert.equal(scene.ratAttackPinned, true);
  assert.equal(scene.pointerAttackEventId, scene.ratEventId);
  scene.ratAttackButton.handlers.pointerdown({ wasTouch: true }, 0, 0, { stopPropagation() {} });
  assert.equal(scene.pointerAttackEventId, scene.ratEventId);
  scene.placementActive = true;
  scene.updateRatAttackButton();
  assert.equal(scene.ratAttackButton.visible, false);
});

test('animal and button clicks catch rabbit +1 and mouse +0 exactly once despite same-scene saves', () => {
  for (const species of ['rabbit', 'mouse']) for (const target of ['ratSprite', 'ratAttackButton']) for (const wasTouch of [false, true]) {
    const { scene, context, events } = setup();
    let now = 2000;
    context.performance.now = () => now;
    scene.avatar.x = 384;
    scene.avatar.y = 350;
    scene.avatar.cosmetics.lpcWeapon = 'wand';
    scene.ratActor = Object.assign(actor(), { x: 620, y: 350 });
    scene.ratSprite = actor();
    scene.add = attackFactory();
    scene.ratActive = true;
    scene.ratSpecies = species;
    scene.ratEventId = 9;
    scene.player = actor();
    scene.background = { setTexture() { return this; }, setDisplaySize() { return this; } };
    scene.keys = Object.fromEntries(['A', 'S', 'D', 'W'].map(key => [key, { isDown: false }]));
    scene.cursors = Object.fromEntries(['left', 'right', 'up', 'down'].map(key => [key, { isDown: false }]));
    for (const method of ['updateWorldAtmosphere', 'updatePlacedObjectMotion', 'updateRat', 'updatePet', 'setPremiumFrame']) scene[method] = () => {};
    const catches = [];
    scene.dismissRat = (time, caught) => { catches.push(caught); scene.ratActive = false; };
    scene.createRatAttackButton();
    let stopped = false;
    scene[target].handlers.pointerdown({ wasTouch, button: 0 }, 0, 0, { stopPropagation() { stopped = true; } });
    assert.equal(stopped, true);
    assert.equal(scene.pointerAttackEventId, 9);
    for (let i = 0; i < 160; i++) {
      now += 20;
      // A save announces scene: world again while the avatar is approaching.
      if (i % 5 === 0) scene.setScene('world');
      scene.update(now, 20);
    }
    assert.deepEqual(catches, [true], `${species}/${target}, touch=${wasTouch}`);
    const rewards = events.filter(event => event.type === 'forest-rat-caught');
    assert.equal(rewards.length, 1);
    assert.equal(rewards[0].detail.species, species);
    assert.equal(rewards[0].detail.amount, species === 'rabbit' ? 1 : 0);
    assert.equal(scene.actionPose, 'attack');
    assert.equal(scene.avatar.direction, 'right');
    assert.equal(scene.pointerAttackEventId, null);
  }
});

test('coral sword attack plate has raised depth, bright hover, and green approach feedback with a fixed hit target', () => {
  const { scene, context, window } = setup();
  let now = 2000;
  context.performance.now = () => now;
  scene.add = attackFactory();
  scene.ratSprite = actor();
  scene.ratActor = { x: 620, y: 350 };
  scene.ratActive = true;
  scene.ratEventId = 4;
  scene.createRatAttackButton();
  scene.ratSprite.handlers.pointerover();
  scene.updateRatAttackButton();
  const button = scene.ratAttackButton, plate = scene.ratAttackPlate;
  assert.equal(button.text, '공격  ›');
  assert.equal(button.style.color, '#fff9e9');
  assert.deepEqual({ ...button.style.padding }, { left: 29, right: 7, top: 10, bottom: 10 }, 'asymmetric padding reserves the sword without squeezing the approach label');
  assert.equal(button.originX, .5); assert.equal(button.originY, .5);
  assert.ok(button.depth > plate.depth);
  assert.equal(plate.visible, true);
  assert.equal(button.input.cursor, 'pointer');
  const hitArea = { ...button.input.hitArea };
  const originalHitArea = button.input.hitArea;
  const position = [button.x, button.y];
  assert.deepEqual(hitArea, { x: 0, y: 0, width: 112, height: 38 });
  assert.deepEqual(position, [620, 278]);
  const rgb = color => [color >> 16 & 255, color >> 8 & 255, color & 255];
  const fills = plate.commands.filter(command => command[0] === 'fillStyle');
  assert.ok(fills.some(([, color, alpha]) => {
    const [red, green, blue] = rgb(color);
    return alpha === 1 && red > 150 && red > green * 1.15 && green > blue;
  }), 'idle attack face has a warm orange/coral fill');
  assert.ok(fills.some(([, , alpha]) => alpha > 0 && alpha < 1), 'a translucent shadow separates the button from the scene');
  assert.ok(plate.commands.filter(command => command[0] === 'fillRoundedRect').length >= 3, 'layered base, face, and highlights give the plate raised depth');
  assert.ok(plate.commands.some(command => command[0] === 'fillPoints'), 'the sword uses vector geometry, not a font glyph');
  assert.ok(plate.commands.some(command => command[0] === 'fillTriangle'), 'the icon or button accents retain their pointed geometry');
  const idleLines = plate.commands.filter(command => command[0] === 'lineStyle');
  const idleCommands = JSON.stringify(plate.commands);
  button.handlers.pointerover();
  assert.notEqual(JSON.stringify(plate.commands), idleCommands);
  const hoverLines = plate.commands.filter(command => command[0] === 'lineStyle');
  const brightness = color => rgb(color).reduce((sum, channel) => sum + channel, 0);
  assert.ok(hoverLines.some((line, index) => idleLines[index] && brightness(line[2]) > brightness(idleLines[index][2])), 'hover brightens a border while preserving the interaction rectangle');
  assert.deepEqual([button.x, button.y], position);
  button.handlers.pointerdown({ wasTouch: false, button: 2 }, 0, 0, { stopPropagation() { throw Error('right click must be ignored'); } });
  assert.equal(scene.pointerAttackEventId, null);
  button.handlers.pointerdown({ wasTouch: false, button: 0 }, 0, 0, { stopPropagation() {} });
  assert.equal(scene.pointerAttackEventId, 4);
  assert.equal(button.text, '접근 중…');
  assert.deepEqual([button.x, button.y], position, 'pressed feedback must not move the clickable text');
  assert.deepEqual([plate.x, plate.y], position, 'only local plate drawing changes when pressed');
  assert.equal(button.input.hitArea, originalHitArea);
  assert.deepEqual(button.input.hitArea, hitArea);
  assert.ok(plate.commands.filter(command => command[0] === 'fillStyle').some(([, color]) => {
    const [red, green, blue] = rgb(color);
    return green > red && green > blue;
  }), 'approaching changes the face to green');
  const pressedCommands = JSON.stringify(plate.commands);
  window.matchMedia = () => ({ matches: true });
  scene.updateRatAttackButton();
  assert.notEqual(JSON.stringify(plate.commands), pressedCommands, 'reduced motion removes only the painted face displacement, retaining the pressed color');
  assert.deepEqual([button.x, button.y], position, 'reduced motion uses the same fixed world-space hit target');
  assert.equal(button.input.hitArea, originalHitArea);
  button.handlers.pointerup();
  assert.notEqual(JSON.stringify(plate.commands), pressedCommands);
  assert.deepEqual([button.x, button.y, plate.x, plate.y], [...position, ...position]);
  button.handlers.pointerout();
  now += 1000;
  scene.updateRatAttackButton();
  assert.equal(button.visible, true, 'a selected target remains visible while approaching');
  assert.equal(button.text, '접근 중…');
  scene.cancelPointerMovement();
  scene.updateRatAttackButton();
  assert.equal(button.text, '공격  ›');
  scene.ratActor.x = 0;
  scene.updateRatAttackButton();
  assert.equal(button.x, 60, 'the full fixed-size button remains inside the left map edge');
  scene.ratActor.x = 768;
  scene.updateRatAttackButton();
  assert.equal(button.x, 708);
  scene.placementActive = true;
  scene.updateRatAttackButton();
  assert.equal(button.visible, false);
  assert.equal(plate.visible, false);
});

test('the monster hover button and plate hide during placement, indoor scenes, modals, memory capture, and inactive encounters', () => {
  for (const mode of ['placement', 'home', 'garden', 'modal', 'memory', 'inactive']) {
    const { scene, document } = setup();
    scene.add = attackFactory(); scene.ratSprite = actor(); scene.ratActor = { x: 440, y: 350 };
    scene.ratActive = true; scene.ratEventId = 5;
    scene.createRatAttackButton(); scene.ratSprite.handlers.pointerover(); scene.updateRatAttackButton();
    assert.equal(scene.ratAttackButton.visible, true);
    if (mode === 'placement') scene.placementActive = true;
    if (mode === 'home' || mode === 'garden') scene.sceneName = mode;
    if (mode === 'modal') document.querySelector = () => ({ open: true });
    if (mode === 'memory') scene.memoryCapturing = true;
    if (mode === 'inactive') scene.ratActive = false;
    scene.updateRatAttackButton();
    assert.equal(scene.ratAttackButton.visible, false, mode);
    assert.equal(scene.ratAttackPlate.visible, false, mode);
    scene.requestRatAttack();
    assert.equal(scene.pointerAttackEventId, null, `${mode} cannot queue a hidden attack`);
  }
});

test('same-scene sync preserves a path, but entering a different room cancels path and attack', () => {
  const { scene } = setup();
  scene.background = { setTexture() { return this; }, setDisplaySize() { return this; } };
  scene.updateWorldAtmosphere = () => {};
  scene.avatar.x = 384;
  scene.avatar.y = 350;
  scene.requestMoveTo(620, 350);
  const path = scene.movePath;
  scene.pointerAttackEventId = 4;
  scene.ratAttackPinned = true;
  scene.setScene('world');
  assert.equal(scene.movePath, path);
  assert.equal(scene.pointerAttackEventId, 4);
  assert.equal(scene.ratAttackPinned, true);
  scene.setScene('home');
  assert.equal(scene.movePath.length, 0);
  assert.equal(scene.pointerAttackEventId, null);
  assert.equal(scene.ratAttackPinned, false);
});

test('pointer attack approaches its target then faces it and uses the existing equipped action once', () => {
  const { scene } = setup();
  scene.avatar.x = 384;
  scene.avatar.y = 350;
  scene.ratActor = { x: 620, y: 350 };
  scene.ratActive = true;
  scene.ratEventId = 7;
  scene.avatar.cosmetics.lpcWeapon = 'wand';
  const actions = [];
  scene.playAction = (...args) => actions.push(args);
  scene.requestRatAttack();
  for (let i = 0; i < 100; i += 1) {
    const step = scene.pointerMovementStep(3, i * 20);
    if (step) Object.assign(scene.avatar, { x: step.x, y: step.y });
  }
  assert.deepEqual(actions, [['attack', 980]]);
  assert.equal(scene.avatar.direction, 'right');
  assert.ok(scene.avatar.x < scene.ratActor.x);
  assert.ok(scene.ratActor.x - scene.avatar.x <= 68);
  assert.equal(scene.pointerAttackEventId, null);
  scene.requestRatAttack();
  scene.ratEventId = 8;
  assert.equal(scene.pointerMovementStep(3, 2100), null);
  assert.equal(actions.length, 1);
});

test('stationary hover keeps attack visible; only crossing the gap uses the grace timeout', () => {
  const { scene, context } = setup();
  let now = 2000;
  context.performance.now = () => now;
  scene.add = attackFactory();
  scene.ratSprite = actor();
  scene.ratActor = Object.assign(actor(), { x: 440, y: 350 });
  scene.ratActive = true;
  scene.createRatAttackButton();
  scene.ratSprite.handlers.pointerover();
  now = 10000;
  scene.updateRatAttackButton();
  assert.equal(scene.ratAttackButton.visible, true);
  scene.ratSprite.handlers.pointerout();
  now = 10640;
  scene.updateRatAttackButton();
  assert.equal(scene.ratAttackButton.visible, true);
  scene.ratAttackButton.handlers.pointerover();
  now = 20000;
  scene.updateRatAttackButton();
  assert.equal(scene.ratAttackButton.visible, true);
  scene.ratAttackButton.handlers.pointerout();
  now = 20660;
  scene.updateRatAttackButton();
  assert.equal(scene.ratAttackButton.visible, false);

  scene.background = { setTexture() { return this; }, setDisplaySize() { return this; } };
  scene.updateWorldAtmosphere = () => {};
  scene.ratSprite.handlers.pointerover();
  scene.setScene('world');
  assert.equal(scene.ratHovered, true, 'a same-scene state sync must not erase stationary hover');
  scene.ratAttackButton.handlers.pointerover();
  scene.setScene('home');
  assert.equal(scene.ratHovered, false);
  assert.equal(scene.ratAttackHovered, false);
  assert.equal(scene.ratHoverUntil, 0);
  scene.setScene('world');
  scene.updateRatAttackButton();
  assert.equal(scene.ratAttackButton.visible, false);

  scene.ratSprite.handlers.pointerover();
  scene.ratAttackButton.handlers.pointerover();
  context.Phaser.Math = { Between: (minimum) => minimum };
  scene.dismissRat(now);
  assert.equal(scene.ratHovered, false);
  assert.equal(scene.ratAttackHovered, false);
  assert.equal(scene.ratHoverUntil, 0);
  assert.equal(scene.ratAttackButton.visible, false);
  assert.equal(scene.ratAttackPlate.visible, false);
});

test('canvas event converts through the camera and ignores right clicks', () => {
  const { scene, context, events } = setup();
  let handle;
  scene.input = { on: (_type, callback) => { handle = callback; } };
  scene.cameras = { main: { getWorldPoint: (x, y) => ({ x: x / 2 + 10, y: y / 2 + 20 }) } };
  scene.lastPetPointerAt = 0;
  const begin = source.indexOf('      this.input.on("pointerdown", (pointer) => {');
  const end = source.indexOf('      this.emitPosition(true);', begin);
  context.scene = scene;
  vm.runInContext(`(function() { ${source.slice(begin, end)} }).call(scene)`, context);
  handle({ x: 400, y: 300, button: 2 });
  assert.equal(events.length, 0);
  handle({ x: 400, y: 300, button: 0 });
  assert.equal(events[0].type, 'forest-world-pointer');
  assert.equal(events[0].detail.x, 210);
  assert.equal(events[0].detail.y, 170);
});

test('keyboard movement overrides pointer paths and hiding controls releases virtual direction', () => {
  const { scene, listeners } = setup();
  scene.avatar.x = 384;
  scene.avatar.y = 410;
  scene.requestMoveTo(600, 410);
  scene.attachWindowEvents();
  scene.forcedDirection = 'right';
  scene.forcedUntil = 3000;
  listeners.get('forest-controls-hidden')();
  assert.equal(scene.forcedDirection, null);
  assert.equal(scene.forcedUntil, 0);
  scene.keys = Object.fromEntries(['A', 'S', 'D', 'W'].map(key => [key, { isDown: key === 'A' }]));
  scene.cursors = Object.fromEntries(['left', 'right', 'up', 'down'].map(key => [key, { isDown: false }]));
  scene.player = actor();
  for (const method of ['updateWorldAtmosphere', 'updateRat', 'updatePet', 'emitPosition', 'setPremiumFrame']) scene[method] = () => {};
  scene.update(2500, 20);
  assert.equal(scene.movePath.length, 0);
  assert.equal(scene.avatar.direction, 'left');
  assert.ok(scene.avatar.x < 384);
  scene.detachWindowEvents();
  assert.equal(listeners.has('forest-move-to'), false);
  assert.equal(listeners.has('forest-controls-hidden'), false);
});

test('opening a modal cancels auto-movement and queued attacks without resuming after close', () => {
  const { scene, document, events } = setup();
  scene.avatar.x = 384;
  scene.avatar.y = 410;
  scene.requestMoveTo(600, 410);
  scene.pointerAttackEventId = 7;
  scene.forcedDirection = 'right';
  scene.forcedUntil = 3000;
  scene.keys = Object.fromEntries(['A', 'S', 'D', 'W'].map(key => [key, { isDown: false }]));
  scene.cursors = Object.fromEntries(['left', 'right', 'up', 'down'].map(key => [key, { isDown: false }]));
  scene.player = actor();
  for (const method of ['updateWorldAtmosphere', 'updateRat', 'updatePet', 'setPremiumFrame']) scene[method] = () => {};
  document.querySelector = () => ({ open: true });
  scene.update(2500, 20);
  assert.equal(scene.movePath.length, 0);
  assert.equal(scene.pointerAttackEventId, null);
  assert.equal(scene.forcedUntil, 0);
  assert.equal(scene.avatar.x, 384);
  assert.equal(scene.requestMoveTo(600, 410), false);
  assert.ok(events.some(event => event.type === 'forest-phaser-position' && event.detail.x === 384));
  document.querySelector = () => null;
  scene.update(2600, 20);
  assert.equal(scene.avatar.x, 384);
});
