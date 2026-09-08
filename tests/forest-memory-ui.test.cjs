const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const source = readFileSync(path.join(__dirname, '../src/frontend/forest-game.js'), 'utf8');
const html = readFileSync(path.join(__dirname, '../src/frontend/forest.html'), 'utf8');
const css = readFileSync(path.join(__dirname, '../src/frontend/forest-game.css'), 'utf8');
const memoryCode = source.slice(source.indexOf('  const MEMORY_PRESET_GUESTS'), source.indexOf('  function generateNickname()'));
const roles = ['female', 'male', 'moon_mage', 'forest_witch', 'inventor', 'knight'];
const names = ['성실한 당근', '꾸준한 상균', '달빛의 빛샘', '숲속의 수인', '발명의 준혁', '해결의 세준'];
const png = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==';

function sampleState() {
  return {
    avatar: { name: '실제 사용자 닉네임', gender: 'male', engine: 'old', x: 255, y: 321, cosmetics: { userOnly: true } },
    carrots: 937, privateProfile: { email: 'private@example.test' },
    outfitHistory: [...roles].reverse().map((presetRole, index) => ({
      id: `id-${presetRole}`, presetRole, label: `기존 옷장 이름 ${presetRole}`, engine: 'old',
      gender: ['male', 'inventor', 'knight'].includes(presetRole) ? 'male' : 'female',
      cosmetics: { lpcOutfit: `saved-look-${presetRole}`, custom: { colors: ['blue', index] } },
      tuning: { worldScale: .43, nested: { y: index } },
    })),
  };
}

class EventTargetStub {
  constructor() { this.listeners = new Map(); }
  addEventListener(type, handler) {
    const list = this.listeners.get(type) || [];
    list.push(handler); this.listeners.set(type, list);
  }
  dispatchEvent(event) {
    for (const handler of this.listeners.get(event.type) || []) handler(event);
    return true;
  }
}

function setup() {
  const state = sampleState(), events = [], downloads = [], revokes = [], urls = [], timers = new Map();
  const eventTarget = new EventTargetStub(), doc = new EventTargetStub();
  let timerId = 0, clock = 1700000000000;
  class Element extends EventTargetStub {
    constructor(id) { super(); this.id = id; this.hidden = false; this.disabled = false; this.attrs = {}; this.isConnected = true; }
    setAttribute(name, value) { this.attrs[name] = value; }
    removeAttribute(name) { delete this.attrs[name]; if (['src', 'href', 'download'].includes(name)) delete this[name]; }
    focus() { doc.activeElement = this; }
    show() { this.open = true; }
    close() { this.open = false; this.dispatchEvent({ type: 'close' }); }
    remove() { this.removed = true; }
    click() {
      if (this.disabled) return;
      const event = { type: 'click', defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } };
      this.dispatchEvent(event);
      if (['a', 'save'].includes(this.id) && this.href && !event.defaultPrevented) downloads.push({ href: this.href, filename: this.download });
    }
  }
  const ids = ['dialog', 'status', 'progress', 'preview', 'figure', 'save', 'retake', 'close'];
  const elements = Object.fromEntries(ids.map((id) => [id, new Element(id)]));
  const world = new Element('phaser-world'), originalFocus = new Element('camera');
  const wardrobe = new Element('wardrobe'), previouslyInert = new Element('already-inert');
  previouslyInert.inert = true;
  const bodyClasses = new Set();
  doc.body = { classList: { add: (name) => bodyClasses.add(name), remove: (name) => bodyClasses.delete(name) }, appendChild() {} };
  const frame = new Element('frame'), workspace = new Element('workspace');
  frame.children = [world, elements.dialog];
  workspace.children = [frame, wardrobe];
  doc.body.children = [workspace, previouslyInert];
  for (const parent of [frame, workspace, doc.body]) for (const child of parent.children) child.parentElement = parent;
  doc.querySelector = (selector) => selector === '#phaser-world' ? world : elements[selector.replace('#forest-memory-', '')];
  doc.createElement = (tag) => new Element(tag);
  doc.activeElement = originalFocus;
  const urlApi = { createObjectURL: (blob) => { urls.push(blob); return `blob:local-photo-${urls.length}`; }, revokeObjectURL: (url) => revokes.push(url) };
  const setTimer = (handler, delay) => { timers.set(++timerId, { handler, at: clock + delay }); return timerId; };
  const clearTimer = (id) => timers.delete(id);
  const advance = (duration) => {
    clock += duration;
    for (const [id, value] of [...timers]) if (value.at <= clock) { timers.delete(id); value.handler(); }
  };
  const context = vm.createContext({ Blob, Date, URL, CustomEvent: class { constructor(type, init) { this.type = type; this.detail = init.detail; } } });
  vm.runInContext(memoryCode, context);
  const options = { getState: () => state, eventTarget, doc, urlApi, setTimer, clearTimer, now: () => clock };
  for (const type of ['forest-memory-start', 'forest-memory-cancel', 'forest-controls-hidden']) {
    eventTarget.addEventListener(type, (event) => events.push(event));
  }
  const ui = context.createForestMemoryUi(options);
  const emit = (type, detail = {}) => eventTarget.dispatchEvent({ type, detail });
  const starts = () => events.filter((event) => event.type === 'forest-memory-start');
  const request = () => { emit('forest-memory-request'); return starts().at(-1)?.detail; };
  return { context, ui, state, doc, elements, bodyClasses, events, downloads, revokes, urls, timers, advance, emit, starts, request, world, wardrobe, previouslyInert, originalFocus };
}

test('all six photo guests clone the actual saved role presets in fixed order without account data or mutations', () => {
  const env = setup(), before = JSON.stringify(env.state);
  const guests = env.context.buildMemoryPresets(env.state);
  assert.equal(guests.length, 6);
  guests.forEach((guest, index) => {
    const original = env.state.outfitHistory.find((look) => look.presetRole === roles[index]);
    assert.equal(guest.number, index + 1);
    assert.equal(guest.nickname, names[index]);
    assert.equal(guest.avatar.name, names[index]);
    assert.equal(guest.avatar.engine, 'lpc');
    assert.equal(guest.avatar.gender, original.gender);
    assert.equal(JSON.stringify(guest.avatar.cosmetics), JSON.stringify(original.cosmetics));
    assert.equal(JSON.stringify(guest.avatar.tuning), JSON.stringify(original.tuning));
    assert.deepEqual(Object.keys(guest.avatar).sort(), ['cosmetics', 'direction', 'engine', 'gender', 'name', 'tuning']);
    guest.avatar.cosmetics.custom.colors.push('scene-local');
    guest.avatar.tuning.nested.y = 999;
  });
  assert.equal(JSON.stringify(env.state), before);
  assert.ok(!JSON.stringify(guests).includes('private@example.test'));
  assert.ok(!JSON.stringify(guests).includes('실제 사용자 닉네임'));
});

test('missing saved preset fails explicitly and never invents a replacement outfit', () => {
  const env = setup();
  env.state.outfitHistory = env.state.outfitHistory.filter((look) => look.presetRole !== 'forest_witch');
  assert.throws(() => env.context.buildMemoryPresets(env.state), /프리셋4/);
  env.request();
  assert.equal(env.starts().length, 0);
  assert.equal(env.elements.save.attrs['aria-disabled'], 'true');
  assert.equal(env.elements.retake.disabled, false);
  assert.match(env.elements.status.textContent, /프리셋4/);
  assert.equal(env.bodyClasses.has('forest-memory-shooting'), false);
});

test('camera double clicks and duplicate ready events produce exactly one automatic PNG download', () => {
  const env = setup(), before = JSON.stringify(env.state), { requestId } = env.request();
  assert.equal(env.elements.dialog.open, true);
  assert.equal(env.elements.progress.hidden, false);
  assert.equal(env.bodyClasses.has('forest-memory-shooting'), true);
  env.request(); env.elements.retake.click();
  assert.equal(env.starts().length, 1);
  env.emit('forest-memory-progress', { requestId, message: '동물 친구들이 모이고 있어요.', stage: 'gather' });
  assert.equal(env.elements.status.textContent, '동물 친구들이 모이고 있어요.');
  const detail = { requestId, blob: new Blob(['png'], { type: 'image/png' }) };
  env.emit('forest-memory-ready', detail);
  env.emit('forest-memory-ready', detail);
  assert.equal(env.downloads.length, 1);
  assert.equal(env.urls.length, 1);
  assert.equal(env.elements.preview.src, 'blob:local-photo-1');
  assert.equal(env.elements.figure.hidden, false);
  assert.equal(env.elements.progress.hidden, true);
  assert.equal(env.elements.save.attrs['aria-disabled'], 'false');
  assert.equal(env.bodyClasses.has('forest-memory-shooting'), true);
  assert.equal(env.bodyClasses.has('forest-memory-developing'), true);
  assert.match(env.elements.status.textContent, /컬러 PNG/);
  assert.match(env.elements.status.textContent, /사진관에서 나가기/);
  assert.match(env.downloads[0].filename, /^당근의숲_추억사진_\d{8}_\d{6}\.png$/);
  assert.equal(JSON.stringify(env.state), before);
  env.elements.save.click();
  assert.equal(env.downloads.length, 2, 'an explicit user retry may save the same photo again');
  assert.equal(env.downloads[0].filename, env.downloads[1].filename);
});

test('close cancels assembly, ignores stale results and restores focus; Escape works nonmodally', () => {
  const env = setup(), { requestId } = env.request();
  env.elements.close.click();
  assert.equal(env.elements.dialog.open, false);
  assert.equal(env.doc.activeElement, env.originalFocus);
  assert.equal(env.events.filter((event) => event.type === 'forest-memory-cancel').at(-1).detail.requestId, requestId);
  env.emit('forest-memory-ready', { requestId, dataUrl: png });
  assert.equal(env.downloads.length, 0);
  const second = env.request();
  assert.notEqual(second.requestId, requestId);
  env.emit('forest-memory-ready', { requestId, dataUrl: png });
  assert.equal(env.downloads.length, 0);
  let prevented = false, stopped = false;
  env.doc.dispatchEvent({ type: 'keydown', key: 'Escape', preventDefault: () => { prevented = true; }, stopPropagation: () => { stopped = true; } });
  assert.equal(prevented, true); assert.equal(stopped, true);
  assert.equal(env.elements.dialog.open, false);
  assert.equal(env.bodyClasses.has('forest-memory-shooting'), false);
  assert.equal(env.doc.activeElement, env.originalFocus);
});

test('error is plain text and retry creates a fresh session while ignoring earlier callbacks', () => {
  const env = setup(), { requestId } = env.request();
  env.emit('forest-memory-error', { requestId, message: '<img onerror=bad> 준비 실패' });
  assert.equal(env.elements.status.textContent, '<img onerror=bad> 준비 실패');
  assert.equal(env.elements.save.attrs['aria-disabled'], 'true');
  assert.equal(env.elements.retake.disabled, false);
  env.elements.retake.click();
  const next = env.starts().at(-1).detail;
  assert.notEqual(next.requestId, requestId);
  env.emit('forest-memory-error', { requestId, message: 'stale' });
  env.emit('forest-memory-ready', { requestId, dataUrl: png });
  assert.equal(env.downloads.length, 0);
  env.emit('forest-memory-ready', { requestId: next.requestId, dataUrl: png });
  assert.equal(env.downloads.length, 1);
  assert.equal(env.downloads[0].href, png);
});

test('only owned PNG blobs or inline PNG data URLs can reach the preview and download', () => {
  for (const dataUrl of ['https://elsewhere.test/photo.png', 'blob:unowned', 'javascript:alert(1)', 'data:text/html;base64,AAAA', 'data:image/svg+xml;base64,AAAA', 'data:image/png;base64,AAAA']) {
    const env = setup(), { requestId } = env.request();
    env.emit('forest-memory-ready', { requestId, dataUrl });
    assert.equal(env.downloads.length, 0);
    assert.equal(env.elements.save.attrs['aria-disabled'], 'true');
    assert.equal(env.elements.retake.disabled, false);
    assert.equal(env.elements.preview.src, undefined);
  }
  for (const blob of [new Blob([], { type: 'image/png' }), new Blob(['<svg/>'], { type: 'image/svg+xml' })]) {
    const env = setup(), { requestId } = env.request();
    env.emit('forest-memory-ready', { requestId, blob });
    assert.equal(env.urls.length, 0);
    assert.equal(env.downloads.length, 0);
  }
});

test('owned URLs survive download startup then revoke on replacement, close and page exit', () => {
  const env = setup(), first = env.request();
  env.emit('forest-memory-ready', { requestId: first.requestId, blob: new Blob(['png'], { type: 'image/png' }) });
  env.elements.retake.click();
  assert.deepEqual(env.revokes, []);
  env.advance(9999); assert.deepEqual(env.revokes, []);
  env.advance(1); assert.deepEqual(env.revokes, ['blob:local-photo-1']);
  const second = env.starts().at(-1).detail;
  env.emit('forest-memory-ready', { requestId: second.requestId, blob: new Blob(['png'], { type: 'image/png' }) });
  env.elements.close.click();
  assert.equal(env.elements.preview.src, undefined);
  assert.equal(env.revokes.length, 1);
  env.advance(10000); assert.deepEqual(env.revokes, ['blob:local-photo-1', 'blob:local-photo-2']);
  const third = env.request();
  env.emit('forest-memory-ready', { requestId: third.requestId, blob: new Blob(['png'], { type: 'image/png' }) });
  env.emit('pagehide');
  assert.deepEqual(env.revokes, ['blob:local-photo-1', 'blob:local-photo-2', 'blob:local-photo-3']);
  assert.equal(env.timers.size, 0);
  assert.equal(env.bodyClasses.has('forest-memory-shooting'), false);
});

test('timed out assembly can retry and never saves a late photo', () => {
  const env = setup(), { requestId } = env.request();
  env.advance(45000);
  assert.equal(env.elements.retake.disabled, false);
  assert.match(env.elements.status.textContent, /오래/);
  env.emit('forest-memory-ready', { requestId, dataUrl: png });
  assert.equal(env.downloads.length, 0);
  env.elements.retake.click();
  assert.equal(env.starts().length, 2);
});

test('background interactions freeze during assembly without hiding the field or losing preexisting inert state', () => {
  const env = setup(), { requestId } = env.request();
  assert.equal(env.world.inert, true);
  assert.equal(env.wardrobe.inert, true);
  assert.equal(env.previouslyInert.inert, true);
  assert.equal(env.world.hidden, false);
  assert.notEqual(env.elements.dialog.inert, true);
  env.emit('forest-memory-ready', { requestId, dataUrl: png });
  assert.equal(env.world.inert, true);
  assert.equal(env.wardrobe.inert, true);
  assert.equal(env.bodyClasses.has('forest-memory-developing'), true);
  assert.equal(env.previouslyInert.inert, true);
  env.elements.retake.click();
  assert.equal(env.world.inert, true);
  env.elements.close.click();
  assert.equal(env.world.inert, false);
  assert.equal(env.wardrobe.inert, false);
  assert.equal(env.previouslyInert.inert, true);
  assert.equal(env.bodyClasses.has('forest-memory-developing'), false);
});

test('a synchronous reentrant ready callback inside the download cannot trigger a second save', () => {
  const env = setup(), { requestId } = env.request();
  const detail = { requestId, blob: new Blob(['png'], { type: 'image/png' }) };
  const click = env.elements.save.click.bind(env.elements.save);
  env.elements.save.click = () => { env.emit('forest-memory-ready', detail); click(); };
  env.emit('forest-memory-ready', detail);
  assert.equal(env.downloads.length, 1);
  assert.equal(env.urls.length, 1);
});

test('a persistent native download link prefers a verified inline PNG and a manual click does not double-trigger', () => {
  const env = setup(), { requestId } = env.request(), save = env.elements.save;
  assert.equal(save.href, undefined);
  assert.equal(save.tabIndex, -1);
  save.click(); assert.equal(env.downloads.length, 0);
  env.emit('forest-memory-ready', { requestId, blob: new Blob(['png'], { type: 'image/png' }), dataUrl: png });
  assert.equal(env.elements.preview.src, 'blob:local-photo-1');
  assert.equal(save.href, png);
  assert.equal(save.tabIndex, 0);
  assert.equal(env.downloads.length, 1);
  assert.equal(env.downloads[0].href, png);
  assert.equal(save.removed, undefined);
  save.click(); assert.equal(env.downloads.length, 2);
  const enter = { type: 'keydown', key: 'Enter', defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } };
  save.dispatchEvent(enter);
  assert.equal(enter.defaultPrevented, false, 'Enter keeps native anchor activation');
  assert.equal(env.downloads.length, 2, 'Enter handler must not synthesize a duplicate click');
  const space = { type: 'keydown', key: ' ', defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } };
  save.dispatchEvent(space);
  assert.equal(space.defaultPrevented, true); assert.equal(env.downloads.length, 3);
  env.elements.retake.click();
  assert.equal(save.href, undefined); assert.equal(save.download, undefined);
  assert.equal(save.attrs['aria-disabled'], 'true'); assert.equal(save.tabIndex, -1);
  save.click(); assert.equal(env.downloads.length, 3);
});

test('photo filename contains only a Korean title and the local timestamp', () => {
  const env = setup();
  assert.equal(env.context.memoryPhotoFilename(new Date(2026, 8, 8, 3, 4, 5)), '당근의숲_추억사진_20260908_030405.png');
});

test('photo UI is nonmodal, in the fullscreen field, accessible and entirely local', () => {
  assert.ok(html.indexOf('/static/forest-memories.js?') < html.indexOf('/static/forest-phaser.js?'));
  assert.match(html, /id="forest-memory-dialog"[^>]*aria-labelledby="forest-memory-title"[^>]*aria-describedby="forest-memory-status"[^>]*aria-modal="false"/);
  assert.ok(html.indexOf('id="forest-memory-dialog"') > html.indexOf('class="canvas-frame"'));
  assert.ok(html.indexOf('id="forest-memory-dialog"') < html.indexOf('class="right-hud"'));
  assert.match(html, /id="forest-memory-status" role="status" aria-live="polite"/);
  assert.match(html, /id="forest-memory-preview" alt="[^"]+"/);
  assert.match(html, /id="forest-memory-close"[^>]*aria-label="사진관에서 나가기"[^>]*>사진관에서 나가기<\/button>/);
  assert.match(css, /\.forest-memory-dialog\{[^}]*position:absolute;[^}]*width:min\(310px/);
  assert.match(css, /\.forest-memory-developing #phaser-world canvas[^}]*animation:forestMemoryToMonochrome 5\.2s/);
  assert.match(css, /@keyframes forestMemoryToMonochrome\{[^}]*grayscale\(0\)[^}]*\}100%\{[^}]*grayscale\(1\)/);
  assert.doesNotMatch(css, /\.forest-memory-dialog::backdrop/);
  assert.doesNotMatch(memoryCode, /showModal\(|localStorage|sessionStorage|fetch\(|adapter\.save|innerHTML/);
});

test('2D LP fallback alpha-fits the new whole image without changing its aspect ratio or music catalog', () => {
  assert.match(source, /homeRecordPlayerImage\.src = "\/static\/assets\/home-record-player-v159\.png/);
  assert.match(source, /homeRecordPlayerBounds = window\.ForestObjects\.alphaBounds/);
  const block = source.slice(source.indexOf('  function drawHomeRecordPlayer()'), source.indexOf('  function drawPlacedObject('));
  const draws = [], image = { complete: true, naturalWidth: 1254, naturalHeight: 1254 };
  const context = vm.createContext({ homeRecordPlayerImage: image, homeRecordPlayerBounds: { x: 80, y: 100, width: 1000, height: 500 }, state: { homeRecordPlaying: false }, context: { drawImage: (...args) => draws.push(args) } });
  vm.runInContext(block, context); context.drawHomeRecordPlayer();
  assert.deepEqual(draws[0], [image, 80, 100, 1000, 500, 414, 282, 76, 38]);
  assert.match(source, /home: \{ name: "우리 집", audioKey: "homeRecordHome" \}/);
  assert.match(source, /forestFairy: \{ name: "숲 속의 요정", audioKey: "homeRecordForestFairy" \}/);
});
