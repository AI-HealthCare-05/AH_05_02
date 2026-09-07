const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const source = readFileSync(path.join(__dirname, '../src/frontend/forest-phaser.js'), 'utf8');

// Mirrors the bundled Phaser 3.90 Camera's center-origin transforms and bounds
// math. The canvas is physical pixels; every actor remains in 768x512 units.
class Camera {
  constructor(width, height) {
    Object.assign(this, { width, height, zoom: 1, scrollX: 0, scrollY: 0, handlers: new Map() });
    this.matrix = { transformPoint: (x, y) => ({
      x: (x - this.width / 2) * this.zoom + this.width / 2,
      y: (y - this.height / 2) * this.zoom + this.height / 2,
    }) };
  }
  setBounds(x, y, width, height) { this.bounds = { x, y, width, height }; return this; }
  startFollow(target, roundPixels, lerpX, lerpY, offsetX, offsetY) {
    Object.assign(this, { target, roundPixels, lerpX, lerpY });
    return this.setFollowOffset(offsetX, offsetY);
  }
  setFollowOffset(x, y) { this.offset = { x, y }; return this; }
  setZoom(zoom) { this.zoom = zoom; return this; }
  on(type, callback) { this.handlers.set(type, callback); return this; }
  off(type) { this.handlers.delete(type); return this; }
  centerOn(x, y) {
    const visibleWidth = this.width / this.zoom, visibleHeight = this.height / this.zoom;
    const minX = this.bounds.x + (visibleWidth - this.width) / 2;
    const minY = this.bounds.y + (visibleHeight - this.height) / 2;
    this.scrollX = Math.max(minX, Math.min(minX + this.bounds.width - visibleWidth, x - this.width / 2));
    this.scrollY = Math.max(minY, Math.min(minY + this.bounds.height - visibleHeight, y - this.height / 2));
    return this;
  }
  preRender() {
    this.centerOn(this.target.x - this.offset.x, this.target.y - this.offset.y);
    this.handlers.get('followupdate')?.();
  }
  getWorldPoint(x, y) {
    return {
      x: (x - this.width / 2) / this.zoom + this.width / 2 + this.scrollX,
      y: (y - this.height / 2) / this.zoom + this.height / 2 + this.scrollY,
    };
  }
}

function setup({ devicePixelRatio = 1, zoom = 1 } = {}) {
  const events = [], listeners = new Map();
  const Phaser = {
    Scene: class {}, AUTO: 0, Scale: { FIT: 1, CENTER_BOTH: 1 },
    Game: class { constructor(config) { this.config = config; } },
  };
  const window = {
    Phaser, devicePixelRatio, ForestHud: { zoom },
    dispatchEvent: event => events.push(event),
    addEventListener: (type, callback) => listeners.set(type, callback),
    removeEventListener: type => listeners.delete(type),
  };
  const context = vm.createContext({
    window, Phaser, localStorage: { getItem: () => null }, performance: { now: () => 0 },
    document: { getElementById: () => ({}), activeElement: { tagName: 'DIV' } },
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options?.detail; } },
  });
  vm.runInContext(source, context);
  const config = window.carrotForestPhaserGame.config;
  const scene = new config.scene();
  const camera = new Camera(config.width, config.height);
  scene.cameras = { main: camera };
  scene.player = { x: scene.avatar.x, y: scene.avatar.y };
  scene.configureWorldCamera();
  scene.attachWindowEvents();
  return { scene, camera, config, window, events, listeners };
}

function near(actual, expected) { assert.ok(Math.abs(actual - expected) < 1e-9, `${actual} should equal ${expected}`); }

test('dense backing stays 3:2 without changing saved coordinates, sprite scale, or world zoom', () => {
  for (const [devicePixelRatio, backing] of [[1, 4], [1.25, 4], [2, 4], [3, 4], [4, 4]]) {
    const { config, scene, camera } = setup({ devicePixelRatio });
    assert.equal(config.width, 768 * backing);
    assert.equal(config.height, 512 * backing);
    assert.equal(config.width / config.height, 3 / 2);
    assert.equal(scene.avatar.x, 384);
    assert.equal(scene.avatar.y, 352);
    assert.equal(scene.avatar.tuning.worldScale, .43);
    assert.equal(scene.cameraZoom, 1);
    assert.equal(scene.worldCameraZoom, 2);
    assert.equal(camera.zoom, 2 * backing);
    assert.equal(camera.width / camera.zoom, 384);
    assert.equal(camera.height / camera.zoom, 256);
    assert.equal(config.scale.mode, 1);
    assert.equal(config.pixelArt, true);
  }
});

test('50 through 200 percent changes only camera magnification and centers the stable avatar body', () => {
  const { scene, camera, config, events, listeners, window } = setup();
  const saved = JSON.stringify(scene.avatar), backingWidth = config.width;
  for (const zoom of [.5, .75, 1, 1.25, 1.5, 1.75, 2]) {
    listeners.get('forest-camera-zoom')({ detail: { zoom } });
    assert.equal(scene.cameraZoom, zoom);
    assert.equal(scene.worldCameraZoom, zoom * 2);
    assert.equal(camera.zoom, zoom * 8);
    assert.equal(config.width, backingWidth);
    assert.equal(JSON.stringify(scene.avatar), saved);
    if (zoom >= .75) {
      const center = window.ForestCamera.worldToScreen(scene.player.x, scene.player.y - scene.cameraFocusOffsetY());
      near(center.x, .5);
      near(center.y, .5);
    }
  }
  assert.equal(events.some(event => event.type === 'forest-phaser-position'), false);
  assert.equal(camera.target, scene.player);
  assert.equal(camera.roundPixels, false, 'a fractional player center must not be rounded during camera following');
});

test('world bounds fill every viewport corner at all zoom levels and following never exposes blank edges', () => {
  const { scene, camera } = setup();
  for (const zoom of [.5, .75, 1, 1.25, 1.5, 1.75, 2]) {
    scene.setCameraZoom(zoom);
    for (const [x, y] of [[28, 42], [740, 42], [28, 480], [740, 480], [384, 352]]) {
      Object.assign(scene.player, { x, y });
      camera.preRender();
      const topLeft = camera.getWorldPoint(0, 0), bottomRight = camera.getWorldPoint(camera.width, camera.height);
      assert.ok(topLeft.x >= -1e-9 && topLeft.y >= -1e-9);
      assert.ok(bottomRight.x <= 768 + 1e-9 && bottomRight.y <= 512 + 1e-9);
      if (zoom === .5) {
        near(topLeft.x, 0); near(topLeft.y, 0);
        near(bottomRight.x, 768); near(bottomRight.y, 512);
      }
    }
  }
});

test('DOM projection and pointer inverse agree immediately after zoom and avatar follow updates', () => {
  const { scene, camera, window, events } = setup();
  for (const zoom of [.5, 1, 2]) {
    scene.setCameraZoom(zoom);
    for (const point of [{ x: 0, y: 0 }, { x: 384, y: 352 }, { x: 650, y: 410 }]) {
      const screen = window.ForestCamera.worldToScreen(point.x, point.y);
      const inverse = camera.getWorldPoint(screen.x * camera.width, screen.y * camera.height);
      near(inverse.x, point.x); near(inverse.y, point.y);
    }
  }
  const count = events.length;
  camera.preRender();
  assert.equal(events.length, count, 'an unchanged view does not repeat DOM layout notifications');
  scene.player.x += 7.125;
  camera.preRender();
  assert.equal(events.length, count + 1);
  const update = events.at(-1);
  assert.equal(update.type, 'forest-camera-view');
  assert.equal(update.detail.displayZoom, 2);
  assert.equal(update.detail.worldZoom, 4);
  assert.equal(update.detail.viewportWidth, 3072);
  assert.deepEqual({ ...update.detail.avatar }, { ...window.ForestCamera.avatarAnchor() });
});

test('nickname projection stays sharp in DOM and updates when only the edge-bound avatar or name changes', () => {
  const { scene, camera, window, events } = setup({ zoom: .5 });
  const first = window.ForestCamera.avatarAnchor();
  assert.equal(first.name, scene.avatar.name);
  assert.equal(first.scene, 'world');
  assert.ok(first.y < window.ForestCamera.worldToScreen(scene.player.x, scene.player.y).y);
  const scroll = [camera.scrollX, camera.scrollY], count = events.length;
  scene.player.x += 8; camera.preRender();
  assert.deepEqual([camera.scrollX, camera.scrollY], scroll, 'minimum zoom keeps the whole world in frame');
  assert.equal(events.length, count + 1, 'avatar label must move even when camera scroll cannot');
  assert.ok(events.at(-1).detail.avatar.x > first.x);
  scene.avatar.name = '바뀐 닉네임'; camera.preRender();
  assert.equal(events.at(-1).detail.avatar.name, '바뀐 닉네임');
  assert.doesNotMatch(source, /this\.nameplate\s*=/, 'nickname must not also be drawn into the pixel canvas');
});

test('nickname uses actual LPC opaque bounds instead of the transparent composite margin', () => {
  const { scene } = setup();
  const pixels = new Uint8ClampedArray(224 * 288 * 4);
  for (let y = 111; y <= 249; y++) for (let x = 75; x <= 148; x++) pixels[(y * 224 + x) * 4 + 3] = 255;
  pixels[3] = 1; pixels[(20 * 224 + 100) * 4 + 3] = 31;
  const bounds = scene.measureAvatarOpaqueBounds(pixels, 224, 288);
  assert.deepEqual({ ...bounds }, { left: 75, top: 111, right: 148, bottom: 249 });
  assert.equal(scene.measureAvatarOpaqueBounds(new Uint8ClampedArray(224 * 288 * 4), 224, 288), null);
  scene.avatarOpaqueBounds = bounds;
  scene.premiumAvatar = { y: 0, height: 288, originY: .87, scaleY: .43 };
  scene.game = { canvas: { clientHeight: 933 } };
  const headWorldY = scene.player.y + (111 - 288 * .87) * .43;
  const hairTop = scene.worldToScreen(scene.player.x, headWorldY);
  const anchor = scene.avatarAnchor();
  near((hairTop.y - anchor.y) * 933, 8);
  const obsoleteTop = scene.worldToScreen(scene.player.x, scene.player.y - 288 * .87 * .43 - 7);
  assert.ok((anchor.y - obsoleteTop.y) * 933 > 180, 'regression: remove the roughly 180px floating gap seen in the large viewport');
});

test('nickname stays eight CSS pixels above visible hair across zoom, resized frames, scale, and jumping', () => {
  const { scene, camera, events } = setup();
  scene.avatarOpaqueBounds = { left: 75, top: 111, right: 148, bottom: 249 };
  scene.premiumAvatar = { y: 0, height: 288, originY: .87, scaleY: .43 };
  scene.game = { canvas: { clientHeight: 512 } };
  for (const cssHeight of [220, 512, 933, 1024]) for (const zoom of [.5, 1, 2]) for (const scale of [.32, .43, .58]) {
    scene.game.canvas.clientHeight = cssHeight;
    scene.premiumAvatar.scaleY = scale;
    scene.setCameraZoom(zoom);
    for (const jumpY of [0, -16]) {
      scene.premiumAvatar.y = jumpY;
      const headY = scene.player.y + jumpY + (111 - 288 * .87) * scale;
      const hair = scene.worldToScreen(scene.player.x, headY);
      near((hair.y - scene.avatarAnchor().y) * cssHeight, 8);
    }
  }
  const count = events.length;
  scene.avatarOpaqueBounds.top = 108; camera.preRender();
  assert.equal(events.length, count + 1, 'a changed hair bound updates the DOM even without camera movement');
  const y = events.at(-1).detail.avatar.y;
  scene.game.canvas.clientHeight = 768; camera.preRender();
  assert.notEqual(events.at(-1).detail.avatar.y, y, 'responsive resizing recomputes the CSS-pixel gap');
});

test('the rendered LPC frame supplies fresh opaque bounds and empty intermediate loads retain the last valid bounds', () => {
  const { scene, window } = setup();
  let pixels = new Uint8ClampedArray(224 * 288 * 4);
  pixels[(109 * 224 + 112) * 4 + 3] = 255;
  pixels[(249 * 224 + 112) * 4 + 3] = 255;
  const context = { clearRect() {}, getImageData() { return { data: pixels }; } };
  scene.compositeTexture = { getContext: () => context, refresh() {} };
  scene.premiumAvatar = { setVisible() { return this; }, setScale(value) { this.scaleY = value; return this; } };
  window.CarrotAvatarCompositor = {};
  window.LpcAvatarEngine = { draw: () => true };
  scene.setPremiumFrame('down', false, 0);
  assert.equal(scene.avatarOpaqueBounds.top, 109);
  assert.equal(scene.premiumAvatar.scaleY, .43);
  pixels = new Uint8ClampedArray(224 * 288 * 4);
  scene.setPremiumFrame('down', false, 140);
  assert.equal(scene.avatarOpaqueBounds.top, 109, 'temporary empty redraws must not fling the label up to texture y=0');
});

test('HUD boot zoom, clamps, resets, and event cleanup use one camera contract', () => {
  const { scene, camera, listeners, window } = setup({ zoom: 1.5 });
  assert.equal(scene.cameraZoom, 1.5);
  for (const [value, expected] of [[-1, .5], [12, 2], [NaN, 1], [undefined, 1], [1, 1]]) {
    listeners.get('forest-camera-zoom')({ detail: { zoom: value } });
    assert.equal(scene.cameraZoom, expected);
  }
  scene.detachWindowEvents();
  assert.equal(listeners.has('forest-camera-zoom'), false);
  assert.equal(camera.handlers.has('followupdate'), false);
  assert.equal(window.ForestCamera, undefined);
  assert.doesNotMatch(source, /keyboard\.on\("keydown-C"/);
  assert.doesNotMatch(source, /event\.key !== "0"/);
});
