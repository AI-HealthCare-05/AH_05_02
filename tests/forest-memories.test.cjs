const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const memories = require('../src/frontend/forest-memories.js');
const animals = require('../src/frontend/forest-animals.js');
const frontend = path.join(__dirname, '../src/frontend');
const source = fs.readFileSync(path.join(frontend, 'forest-memories.js'), 'utf8');
const tick = () => new Promise(resolve => setImmediate(resolve));
const presets = () => memories.NICKNAMES.map((nickname, index) => ({ number: index + 1, nickname: 'never overwrite my nickname', avatar: {
  engine: 'lpc', name: `saved-${index}`, gender: index % 2 ? 'female' : 'male', mounted: true, sitting: true,
  cosmetics: { lpcOutfit: `actual-outfit-${index}`, outfitColor: `actual-color-${index}`, pet: 'white_pup' },
} }));

function setup({ prepare = async () => true, missing = [], snapshotError = false, canvasCapture = false, opaqueTop, draw = () => true, pets } = {}) {
  let now = 1000;
  const events = [], listeners = new Map(), renders = [], removed = [], calls = [];
  const window = {
    performance: { now: () => now }, document: { fonts: { ready: Promise.resolve() } },
    setTimeout, clearTimeout, atob, Blob, matchMedia: () => ({ matches: false }), ForestAnimals: animals, ForestPets: pets,
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options.detail; } },
    addEventListener(type, fn) { listeners.set(type, fn); },
    removeEventListener(type) { listeners.delete(type); },
    dispatchEvent(event) { events.push(event); },
    LpcAvatarEngine: { prepare, draw(...args) { calls.push(args); return draw(...args); } },
  };
  vm.runInNewContext(source, { window, Uint8Array, module: { exports: {} } });
  const scene = {
    sceneName: 'world', input: { enabled: true }, time: { now: 3000, timeScale: .7 }, tweens: { timeScale: .8 },
    children: { list: [], depthSort() { this.list.sort((a, b) => (a.depth || 0) - (b.depth || 0)); } },
    avatar: { x: 410, y: 350, direction: 'left', mounted: false, cosmetics: { pet: 'white_pup' } },
    movePath: [{ x: 419, y: 390 }], forcedDirection: 'right', forcedUntil: 1300,
    ratActive: true, ratEventId: 19, ratNextSpawnAt: 6000, ratDespawnAt: 9000, rabbitActionUntil: 7000,
    petFollowX: 417, petFollowY: 395, petTrail: [{ x: 416, y: 398 }],
  };
  function actor(type, x = 0, y = 0, key) {
    const object = { scene, type, x, y, key, visible: true, scaleX: 1, scaleY: 1,
      setVisible(value) { this.visible = value; return this; },
      setPosition(x, y) { Object.assign(this, { x, y }); return this; },
      setOrigin(x, y) { this.originX = x; this.originY = y; return this; },
      setScale(x, y = x) { this.scaleX = x; this.scaleY = y; return this; },
      setDepth(value) { this.depth = value; return this; },
      setTexture(key, frame) { this.key = key; this.frame = frame; return this; },
      setFrame(frame) { this.frame = frame; return this; },
      setFlipX(value) { this.flipX = value; return this; },
      destroy() { this.destroyed = true; this.scene = null; scene.children.list = scene.children.list.filter(item => item !== this); },
    };
    scene.children.list.push(object);
    return object;
  }
  scene.add = {
    image: (x, y, key) => actor('image', x, y, key), sprite: (x, y, key) => actor('sprite', x, y, key),
    ellipse: (x, y) => actor('shadow', x, y),
    text(x, y, text, style) {
      // Conservative 22-world-pixel text box includes 10px Korean glyphs,
      // line metrics, 3px stroke and both 2px padding edges.
      return Object.assign(actor('text', x, y), { text, style, displayHeight: 22,
        getBounds() { return { top: this.y - this.displayHeight * this.originY, bottom: this.y }; },
      });
    },
  };
  scene.background = actor('background', 384, 256, 'world-bg');
  for (const key of ['player', 'pet', 'petOverlay', 'petEmoji', 'petHeart', 'ratActor', 'ratAttackButton', 'ratAttackPlate', 'placementGrid', 'memoryCameraActor', 'nightOverlay', 'lightFx']) scene[key] = actor(key, 410, 350);
  scene.petEmoji.visible = false;
  scene.player.anims = { timeScale: .6 };
  scene.placedObjectActors = [actor('furniture', 510, 370), actor('furniture', 120, 180)];
  const camera = {
    x: 0, y: 0, width: 1536, height: 1024, zoom: 3.2, scrollX: 12.75, scrollY: -88.25,
    _follow: scene.player, followOffset: { x: 4, y: 43 }, lerp: { x: .8, y: .6 }, useBounds: true, roundPixels: false,
    stopFollow() { this._follow = null; return this; },
    startFollow(target, roundPixels, x, y, offsetX, offsetY) { this._follow = target; this.roundPixels = roundPixels; this.lerp = { x, y }; this.setFollowOffset(offsetX, offsetY); return this; },
    setFollowOffset(x, y) { this.followOffset = { x, y }; return this; },
    setZoom(value) { this.zoom = value; return this; },
    setViewport(x, y, width, height) { Object.assign(this, { x, y, width, height }); return this; },
    centerOn(x, y) { this.scrollX = x - this.width / 2; this.scrollY = y - this.height / 2; return this; },
  };
  scene.cameras = { main: camera };
  scene.textures = {
    exists: key => !missing.includes(key),
    createCanvas() {
      const context = { clearRect() {} };
      if (opaqueTop != null) context.getImageData = () => {
        const data = new Uint8Array(224 * 288 * 4);
        data[(opaqueTop * 224 + 112) * 4 + 3] = 255;
        return { data };
      };
      return { getContext: () => context, refresh() {} };
    },
    remove: key => removed.push(key),
  };
  scene.make = { renderTexture(config) {
    const target = {
      config, camera: { setZoom(value) { this.zoom = value; }, centerOn(x, y) { this.x = x; this.y = y; } },
      draw(objects) { target.objects = [...objects]; },
      snapshot(callback, format) { target.callback = callback; target.format = format; if (snapshotError) throw new Error('snapshot failure'); },
      destroy() { target.destroyed = true; },
    };
    if (canvasCapture) target.texture = { canvas: {
      width: config.width, height: config.height,
      toDataURL(format) { target.canvasFormat = format; return 'data:image/png;base64,iVBORw0KGgo='; },
    } };
    renders.push(target); return target;
  } };
  const controller = new window.ForestMemories.Controller(scene);
  scene.memoryController = controller;
  return { scene, window, controller, events, listeners, renders, removed, calls, setNow(value) { now = value; } };
}

test('six numbered portrait aliases are detached copies of the exact current official outfits', () => {
  const input = presets();
  const before = JSON.stringify(input);
  const output = memories.portraitPresets(input.reverse());
  assert.deepEqual(output.map(item => item.nickname), memories.NICKNAMES);
  output.forEach((item, index) => {
    assert.equal(item.avatar.cosmetics.lpcOutfit, `actual-outfit-${index}`);
    assert.equal(item.avatar.cosmetics.outfitColor, `actual-color-${index}`);
    assert.equal(item.avatar.name, `saved-${index}`);
    assert.equal(item.avatar.mounted, false);
    assert.equal(item.avatar.sitting, false);
  });
  output[0].avatar.cosmetics.lpcOutfit = 'mutated';
  input.reverse();
  assert.equal(JSON.stringify(input), before);
  assert.throws(() => memories.portraitPresets(input.slice(0, 5)));
  assert.throws(() => memories.portraitPresets([...input.slice(0, 5), input[0]]));
});

test('preset3 through preset6 bring their four actual kittens into the photo, including a matching ribbon', async () => {
  const pets = require('../src/frontend/forest-pets.js');
  const input = presets(), ids = ['last_tick_white', 'last_tick_ribbon', 'last_tick_ginger', 'last_tick_gray'];
  ids.forEach((id, index) => { input[index + 2].avatar.cosmetics.pet = id; });
  const saved = JSON.stringify(input);
  const { controller, scene } = setup({ pets });
  await controller.start({ requestId: 'kitten-portrait', presets: input });
  const kittens = controller.session.animals.filter(animal => animal.kind === 'preset-pet');
  assert.deepEqual(Array.from(kittens, item => item.petId), ids);
  assert.equal(scene.petOverlay.visible, false);
  controller.update(controller.session.stagedAt + 1800);
  for (const animal of kittens) {
    const pose = pets.pose(animal.petId, { action: 'sit', direction: 'down', elapsed: 1800 });
    assert.equal(animal.sprite.key, pose.key); assert.equal(animal.sprite.frame, pose.frame);
    assert.equal(animal.sprite.originY, pose.originY);
    assert.equal(animal.overlay.visible, Boolean(pose.overlay));
    if (pose.overlay) {
      assert.equal(animal.overlay.frame, animal.sprite.frame);
      assert.equal(animal.overlay.key, pose.overlay.key);
      assert.deepEqual([animal.overlay.x, animal.overlay.y], [animal.sprite.x, animal.sprite.y]);
    }
  }
  controller.cancel();
  assert.equal(scene.petOverlay.visible, true);
  assert.equal(JSON.stringify(input), saved);
});

test('optional kitten PNG failures keep photography available using the existing pet fallback', async () => {
  const pets = require('../src/frontend/forest-pets.js'), input = presets();
  input[2].avatar.cosmetics.pet = 'last_tick_ginger';
  const { controller } = setup({ pets, missing: pets.assets.map(asset => asset.key) });
  assert.equal(await controller.start({ requestId: 'optional-kitten-fallback', presets: input }), true);
  const ginger = controller.session.animals.find(animal => animal.petId === 'last_tick_ginger');
  assert.equal(ginger.sprite.key, 'lpc-pets');
  assert.equal(ginger.sprite.frame, 4);
  assert.equal(ginger.overlay.visible, false);
  controller.cancel();
});

test('generated square decorations are cropped at visible alpha 16 and fit uniformly, independent of source dimensions', () => {
  const pixels = new Uint8Array(8 * 6 * 4);
  pixels[(0 * 8 + 0) * 4 + 3] = 15;
  for (let y = 2; y <= 5; y++) for (let x = 3; x <= 6; x++) pixels[(y * 8 + x) * 4 + 3] = 16;
  assert.deepEqual(memories.alphaBounds(pixels, 8, 6), { x: 3, y: 2, width: 4, height: 4 });
  assert.equal(memories.alphaBounds(new Uint8Array(64), 4, 4), null);
  assert.deepEqual(memories.fitWithin(700, 1000, 52, 76), { width: 52, height: 1000 * 52 / 700 });
  assert.deepEqual(memories.fitWithin(1254, 627, 76, 108), { width: 76, height: 38 });
});

test('each nickname sits at least four world pixels above its actual clothed alpha top, including tall hats', async () => {
  for (const opaqueTop of [58, 78, 96, 112]) {
    const { controller } = setup({ opaqueTop });
    await controller.start({ requestId: `hat-${opaqueTop}`, presets: presets() });
    const session = controller.session;
    controller.update(session.stagedAt + 1800);
    for (const person of session.people) {
      const renderedHatTop = person.y + (opaqueTop - 288 * person.sprite.originY) * person.sprite.scaleY;
      assert.ok(Math.abs(person.label.y - (renderedHatTop - 4)) < 1e-9);
      assert.equal(person.label.visible, true);
      assert.ok(person.label.getBounds().top > memories.FRAME.y + 4,
        'every settled nickname, including the tallest source hat, retains four pixels of crop headroom');
    }
    controller.cancel();
  }
});

test('portrait live view is centered without stretching or changing export, then restores an offset original viewport', async () => {
  const { controller, scene, renders } = setup();
  const camera = scene.cameras.main;
  camera.setViewport(7, 11, 738, 1100);
  await controller.start({ requestId: 'portrait-framing', presets: presets() });
  assert.ok(Math.abs(camera.x + camera.width / 2 - (7 + 738 / 2)) <= .5);
  assert.ok(Math.abs(camera.y + camera.height / 2 - (11 + 1100 / 2)) <= .5);
  assert.ok(Math.abs(camera.width / camera.height - memories.FRAME.width / memories.FRAME.height) < .005);
  controller.update(controller.session.stagedAt + 3200);
  assert.equal(renders[0].config.width, 1856); assert.equal(renders[0].config.height, 1044);
  assert.equal(memories.FRAME.width / memories.FRAME.height, 16 / 9);
  assert.equal(memories.FRAME.y + memories.FRAME.height, 490, 'only the crop top changes; people and animal positions stay intact');
  controller.cancel();
  assert.deepEqual({ x: camera.x, y: camera.y, width: camera.width, height: camera.height }, { x: 7, y: 11, width: 738, height: 1100 });
});

test('photoshoot source actors are six clothed avatars plus both rabbits, three pets, mouse and cow', async () => {
  const { controller, scene, calls } = setup();
  const originalAvatar = JSON.stringify(scene.avatar);
  await controller.start({ requestId: 'one', presets: presets() });
  assert.equal(scene.memoryCapturing, true);
  const session = controller.session;
  assert.equal(session.people.length, 6);
  assert.deepEqual(Array.from(session.animals, item => item.kind), ['bunbun', 'last-tick', 'mouse', 'pet', 'pet', 'pet', 'cow']);
  assert.deepEqual(Array.from(session.animals.filter(item => item.kind === 'pet'), item => item.column), [0, 3, 6]);
  controller.update(session.stagedAt + 300);
  assert.ok(calls.some(call => call[2].moving && call[2].frame > 0), 'actual source walk frames, not a static avatar contact sheet');
  const lastTick = session.animals.find(animal => animal.kind === 'last-tick');
  assert.equal(lastTick.sprite.frame, animals.rabbitPose('last-tick', { action: 'hop_right', elapsedMs: 300 }).frame);
  assert.equal(session.animals.find(animal => animal.kind === 'cow').sprite.key, 'forest-cow-walk');
  const movingPets = session.animals.filter(animal => animal.kind === 'pet');
  assert.equal(Math.floor(movingPets[0].sprite.frame / 9), 2, 'white cat approaches rightward with a right source row');
  assert.equal(Math.floor(movingPets[1].sprite.frame / 9), 1, 'orange cat approaches leftward with a left source row');
  controller.update(session.stagedAt + 1800);
  assert.ok(session.people.every(person => person.label.visible));
  assert.ok(session.animals.every(animal => Number.isInteger(animal.sprite.frame)));
  assert.equal(JSON.stringify(scene.avatar), originalAvatar);
  assert.equal(scene.player.visible, false);
  assert.equal(scene.placedObjectActors[0].visible, false);
  assert.equal(scene.placedObjectActors[1].visible, true);
  controller.cancel();
});

test('exact live state, visibility, follow, zoom, pan, existing paused speeds and saved data survive cancellation', async () => {
  const { controller, scene, setNow, events, removed } = setup();
  const before = JSON.stringify({ avatar: scene.avatar, path: scene.movePath, trail: scene.petTrail });
  await controller.start({ requestId: 'restore', presets: presets() });
  assert.equal(scene.tweens.timeScale, 0);
  assert.equal(scene.player.anims.timeScale, 0);
  setNow(4000); scene.time.now = 6000;
  assert.equal(controller.cancel('', 'wrong-request'), false);
  assert.equal(controller.cancel('', 'restore'), true);
  assert.equal(controller.cancel(), false);
  assert.equal(scene.player.visible, true); assert.equal(scene.petEmoji.visible, false);
  assert.equal(scene.placedObjectActors[0].visible, true);
  assert.equal(scene.tweens.timeScale, .8); assert.equal(scene.time.timeScale, .7);
  assert.equal(scene.player.anims.timeScale, .6); assert.equal(scene.input.enabled, true);
  assert.equal(scene.memoryCapturing, false);
  assert.equal(scene.cameras.main._follow, scene.player);
  assert.equal(scene.cameras.main.zoom, 3.2);
  assert.equal(scene.cameras.main.scrollX, 12.75); assert.equal(scene.cameras.main.scrollY, -88.25);
  assert.deepEqual(scene.cameras.main.followOffset, { x: 4, y: 43 });
  assert.equal(scene.ratDespawnAt, 12000, 'encounter gets its remaining lifetime back');
  assert.equal(scene.forcedUntil, 4300);
  assert.equal(JSON.stringify({ avatar: scene.avatar, path: scene.movePath, trail: scene.petTrail }), before);
  assert.equal(removed.length, 6);
  assert.equal(events.some(event => /caught|position|state-updated/.test(event.type)), false);
});

test('one actual field render yields one PNG, no HUD, original actors, or responsive-canvas resize', async () => {
  const { controller, scene, renders, events } = setup();
  await controller.start({ requestId: 'snapshot', presets: presets() });
  const session = controller.session;
  controller.update(session.stagedAt + 3200);
  controller.update(session.stagedAt + 3400);
  assert.equal(renders.length, 1);
  const target = renders[0];
  assert.equal(target.config.width, 1856); assert.equal(target.config.height, 1044);
  assert.equal(target.config.add, false); assert.equal(target.camera.zoom, 4);
  assert.equal(target.format, 'image/png');
  assert.ok(target.objects.includes(scene.background));
  assert.ok(!target.objects.includes(scene.player));
  assert.ok(!target.objects.includes(scene.ratActor));
  assert.equal(target.objects.filter(object => object.type === 'text').length, 6);
  target.callback({ src: 'data:image/png;base64,iVBORw0KGgo=' });
  await tick();
  const ready = events.filter(event => event.type === 'forest-memory-ready');
  assert.equal(ready.length, 1); assert.equal(ready[0].detail.requestId, 'snapshot');
  assert.equal(ready[0].detail.blob.type, 'image/png');
  assert.equal(scene.memoryCapturing, false); assert.equal(scene.player.visible, true);
  assert.equal(target.destroyed, true); assert.equal(scene.cameras.main.width, 1536);
  assert.ok(!source.includes('localStorage') && !source.includes('scale.resize'));
});

test('double start, cancel during preload, and a late prior snapshot cannot create a second/stale photo', async () => {
  let finishPrepare;
  const loading = setup({ prepare: () => new Promise(resolve => { finishPrepare = resolve; }) });
  const pending = loading.controller.start({ requestId: 'loading', presets: presets() });
  assert.equal(await loading.controller.start({ requestId: 'duplicate', presets: presets() }), false);
  loading.controller.cancel(); finishPrepare(true); await pending;
  assert.equal(loading.controller.active, false);
  assert.equal(loading.scene.input.enabled, true);
  assert.equal(loading.renders.length, 0);
  const photo = setup();
  await photo.controller.start({ requestId: 'old', presets: presets() });
  photo.controller.update(photo.controller.session.stagedAt + 3300);
  photo.controller.cancel();
  await photo.controller.start({ requestId: 'new', presets: presets() });
  photo.renders[0].callback({ src: 'data:image/png;base64,iVBORw0KGgo=' });
  await tick();
  assert.equal(photo.controller.session.requestId, 'new');
  assert.equal(photo.events.some(event => event.type === 'forest-memory-ready'), false);
  photo.controller.cancel();
});

test('Canvas fallback reads the full offscreen backing instead of Phaser main-viewport-clamped snapshot', async () => {
  const { controller, scene, renders, events } = setup({ canvasCapture: true });
  scene.cameras.main.width = 640; scene.cameras.main.height = 480;
  await controller.start({ requestId: 'canvas-small', presets: presets() });
  controller.update(controller.session.stagedAt + 3200);
  await tick();
  assert.equal(renders[0].texture.canvas.width, 1856);
  assert.equal(renders[0].texture.canvas.height, 1044);
  assert.equal(renders[0].canvasFormat, 'image/png');
  assert.equal(renders[0].callback, undefined, 'never use the clamping snapshot path');
  assert.equal(events.filter(event => event.type === 'forest-memory-ready').length, 1);
  assert.equal(scene.cameras.main.width, 640);
});

test('missing licensed rabbit, partial clothing, render failures and shutdown fail closed and restore', async () => {
  for (const options of [
    { missing: ['forest-rabbit-last-tick'] },
    { prepare: async () => { throw new Error('missing garment'); } },
    { draw: () => false },
    { snapshotError: true },
  ]) {
    const { controller, scene, events } = setup(options);
    await controller.start({ requestId: 'failure', presets: presets() });
    if (controller.active) controller.update(controller.session.stagedAt + 3200);
    await tick();
    assert.equal(controller.active, false);
    assert.equal(scene.input.enabled, true);
    assert.equal(scene.tweens.timeScale, .8);
    assert.equal(scene.player.visible, true);
    assert.equal(events.filter(event => event.type === 'forest-memory-error').length, 1);
    assert.equal(events.some(event => event.type === 'forest-memory-ready'), false);
  }
  const { controller, listeners, scene } = setup();
  await controller.start({ requestId: 'shutdown', presets: presets() });
  controller.destroy();
  assert.equal(listeners.size, 0); assert.equal(scene.memoryCapturing, false);
  assert.equal(scene.player.visible, true);
});

test('actual Phaser shutdown order can destroy the camera before scene cleanup without leaking listeners or capture state', async () => {
  const { controller, scene, listeners, renders, events } = setup();
  await controller.start({ requestId: 'shutdown-camera-first', presets: presets() });
  controller.update(controller.session.stagedAt + 3300);
  scene.cameras.main = undefined;
  controller.session.objects[0].destroy = () => { throw new Error('already destroyed object'); };
  assert.doesNotThrow(() => controller.destroy());
  assert.equal(scene.memoryCapturing, false);
  assert.equal(scene.input.enabled, true);
  assert.equal(scene.player.visible, true);
  assert.equal(listeners.size, 0);
  renders[0].callback({ src: 'data:image/png;base64,iVBORw0KGgo=' });
  await tick();
  assert.equal(events.some(event => event.type === 'forest-memory-ready'), false);
});

test('engine prepare loads every selected outfit layer including apron base and rejects partial failures', async () => {
  const engineSource = fs.readFileSync(path.join(frontend, 'lpc-avatar-engine.js'), 'utf8');
  async function engine(failedFile, omitCategory) {
    const requested = [];
    const records = [
      { category: 'body', id: 'body', sources: { male: [{ file: 'body.png', z: 0 }], muscular: [{ file: 'body.png', z: 0 }] } },
      { category: 'head', id: 'human_male', sources: { male: [{ file: 'head.png', z: 4 }], muscular: [{ file: 'head.png', z: 4 }] } },
      { category: 'shoes', id: 'shoes', sources: { male: [{ file: 'shoes.png', z: 1 }] } },
      { category: 'bottom', id: 'pants', sources: { male: [{ file: 'pants.png', z: 1 }] } },
      { category: 'outfit', id: 'tshirt', sources: { male: [{ file: 'shirt.png', z: 2 }] } },
      { category: 'outfit', id: 'apron', definition: '/aprons/woodworker', sources: { male: [{ file: 'apron.png', z: 3 }] } },
    ];
    const window = { dispatchEvent() {} };
    vm.runInNewContext(engineSource, {
      window, console: { error() {} }, fetch: async () => ({ ok: true, json: async () => ({ items: records.filter(item => item.category !== omitCategory) }) }),
      requestAnimationFrame: fn => fn(), CustomEvent: class {},
      Image: class {
        constructor() { this.events = {}; }
        addEventListener(type, callback) { this.events[type] = callback; }
        set src(url) { requested.push(url); queueMicrotask(() => this.events[url.endsWith(failedFile || 'not-missing') ? 'error' : 'load']()); }
      },
    });
    const avatar = { gender: 'male', cosmetics: { bodyType: 'muscular', lpcOutfit: 'apron', lpcBottom: 'pants' } };
    return { requested, preparing: window.LpcAvatarEngine.prepare([avatar]) };
  }
  const loaded = await engine();
  await loaded.preparing;
  assert.ok(loaded.requested.some(url => url.endsWith('apron.png')));
  assert.ok(loaded.requested.some(url => url.endsWith('shirt.png')), 'apron base shirt cannot be omitted');
  assert.ok(loaded.requested.some(url => url.endsWith('pants.png')), 'wearables honor muscular to adult source fallback');
  const failed = await engine('apron.png');
  await assert.rejects(failed.preparing, /공식 의상/);
  for (const category of ['body', 'head', 'outfit', 'bottom', 'shoes']) {
    const omitted = await engine(null, category);
    await assert.rejects(omitted.preparing, /레이어/);
    assert.equal(omitted.requested.length, 0, 'do not proceed with one missing core layer');
  }
});
