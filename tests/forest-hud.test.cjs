const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../src/frontend/forest-hud.js'), 'utf8');

function createHud({ width = 1400, height = 900, storedName = null, storageBlocked = false } = {}) {
  const elements = {}, events = [], classes = new Set(), storage = new Map();
  if (storedName !== null) storage.set('carrot-forest-name-v1', storedName);
  const ids = ['map-title', 'edit-forest-name', 'forest-name-form', 'forest-name-input', 'cancel-forest-name',
    'zoom-in', 'zoom-out', 'zoom-level', 'ui-toggle', 'controls-toggle', 'controls-content', 'objects-toggle', 'placed-list'];
  for (const id of ids) {
    const listeners = {}, attrs = {};
    elements[id] = { hidden: id === 'forest-name-form', style: {}, value: '', textContent: '', disabled: false,
      addEventListener(type, callback) { listeners[type] = callback; },
      setAttribute(name, value) { attrs[name] = value; }, getAttribute(name) { return attrs[name]; },
      focus() { this.focused = true; }, select() { this.selected = true; },
      setCustomValidity(message) { this.validationMessage = message; }, reportValidity() { this.reported = true; },
      emit(type, values = {}) { listeners[type]?.({ preventDefault() {}, stopPropagation() {}, ...values }); },
    };
  }
  const area = { clientWidth: width, clientHeight: height }, frame = { style: {} };
  let refreshCount = 0, resizeCallback;
  const window = {
    carrotForestPhaserGame: { scale: { refresh() { refreshCount += 1; } } },
    dispatchEvent(event) { events.push(event); }, addEventListener() {},
  };
  const document = {
    getElementById: id => elements[id], querySelector: selector => selector === '.canvas-workarea' ? area : frame,
    body: { classList: { toggle(name, value) { if (value) classes.add(name); else classes.delete(name); } } },
  };
  vm.runInNewContext(source, { window, document,
    localStorage: { getItem(key) { if (storageBlocked) throw Error('blocked'); return storage.get(key) ?? null; },
      setItem(key, value) { if (storageBlocked) throw Error('blocked'); storage.set(key, value); } },
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options?.detail; } },
    requestAnimationFrame: callback => callback(), ResizeObserver: class { constructor(callback) { resizeCallback = callback; } observe() {} },
  });
  return { hud: window.ForestHud, elements, area, frame, events, classes, storage,
    resize: () => resizeCallback(), refreshCount: () => refreshCount,
    click: id => elements[id].emit('click'), submit: () => elements['forest-name-form'].emit('submit') };
}

test('the game starts at its original 768×512 size, never stretching into free space', () => {
  const app = createHud();
  assert.equal(app.frame.style.width, '768px');
  assert.equal(app.frame.style.height, '512px');
  assert.equal(app.elements['zoom-level'].textContent, '100%');
  assert.equal(app.refreshCount(), 1);
  app.resize();
  assert.equal(app.refreshCount(), 1, 'unchanged ResizeObserver callbacks must not loop scale refresh');
});

test('narrow and short screens fit the original aspect ratio and display actual zoom', () => {
  const app = createHud({ width: 400, height: 200 });
  assert.equal(app.frame.style.width, '300px');
  assert.equal(app.frame.style.height, '200px');
  assert.equal(app.elements['zoom-level'].textContent, '39%');
  app.area.clientWidth = 600; app.area.clientHeight = 500; app.resize();
  assert.equal(app.frame.style.width, '600px');
  assert.equal(app.frame.style.height, '400px');
  app.area.clientWidth = 0; app.resize();
  assert.equal(app.frame.style.width, '600px', 'temporarily hidden areas must not erase the viewport');
});

test('zoom changes in 25 percent increments within 25–150 percent and always preserves ratio', () => {
  const app = createHud();
  app.click('zoom-in');
  assert.equal(app.frame.style.width, '960px');
  assert.equal(app.frame.style.height, '640px');
  app.click('zoom-in'); app.click('zoom-in');
  assert.equal(app.hud.zoom, 1.5);
  assert.equal(app.elements['zoom-in'].disabled, true);
  for (let i = 0; i < 6; i++) app.click('zoom-out');
  assert.equal(app.hud.zoom, .25);
  assert.equal(app.elements['zoom-out'].disabled, true);
  assert.equal(app.frame.style.width, '192px');
  assert.equal(app.frame.style.height, '128px');
});

test('zoom-out steps from the visible fitted size, and zoom-in stops at available space', () => {
  const app = createHud({ width: 768 * .71 });
  assert.equal(app.elements['zoom-level'].textContent, '71%');
  assert.equal(app.elements['zoom-in'].disabled, true);
  app.click('zoom-in');
  assert.equal(app.hud.zoom, 1, 'clicking the fitted upper bound cannot build up invisible requested zoom');
  app.click('zoom-out');
  assert.equal(app.hud.zoom, .5);
  assert.equal(app.elements['zoom-level'].textContent, '50%');
  assert.equal(app.elements['zoom-in'].disabled, false);
  app.click('zoom-in');
  assert.equal(app.elements['zoom-level'].textContent, '71%');
  assert.equal(app.elements['zoom-in'].disabled, true);
  app.area.clientWidth = 768 * .45; app.resize();
  assert.equal(app.elements['zoom-level'].textContent, '45%');
  app.click('zoom-out');
  assert.equal(app.elements['zoom-level'].textContent, '25%');
  assert.equal(app.elements['zoom-out'].disabled, true);
});

test('resize and HUD toggling recalculate zoom availability including sub-25 percent screens', () => {
  const app = createHud({ width: 768 * .71 });
  assert.equal(app.elements['zoom-in'].disabled, true);
  app.area.clientWidth = 1400;
  app.click('ui-toggle');
  assert.equal(app.elements['zoom-level'].textContent, '100%');
  assert.equal(app.elements['zoom-in'].disabled, false);
  app.area.clientWidth = 768 * .71;
  app.click('ui-toggle');
  assert.equal(app.elements['zoom-in'].disabled, true);
  app.area.clientWidth = 1400; app.resize();
  assert.equal(app.elements['zoom-in'].disabled, false);
  app.area.clientWidth = 100; app.resize();
  assert.equal(app.elements['zoom-in'].disabled, true);
  assert.equal(app.elements['zoom-out'].disabled, true);
  app.click('zoom-out');
  assert.equal(app.hud.zoom, 1);
  assert.equal(app.frame.style.width, '100px');
});

test('forest name editing saves a bounded normalized name and announces it to scene chrome', () => {
  const app = createHud();
  assert.equal(app.hud.forestName, '우리의 작은 숲');
  app.click('edit-forest-name');
  assert.equal(app.elements['forest-name-input'].value, '우리의 작은 숲');
  assert.equal(app.elements['forest-name-form'].hidden, false);
  assert.equal(app.elements['forest-name-input'].selected, true);
  app.elements['forest-name-input'].value = '  함께\n  자라는 숲  '; app.submit();
  assert.equal(app.hud.forestName, '함께 자라는 숲');
  assert.equal(app.storage.get('carrot-forest-name-v1'), '함께 자라는 숲');
  assert.equal(app.events.at(-1).type, 'forest-name-updated');
  assert.equal(app.events.at(-1).detail.name, '함께 자라는 숲');
  assert.equal(app.elements['forest-name-form'].hidden, true);
  assert.equal(app.elements['edit-forest-name'].getAttribute('aria-expanded'), 'false');
  assert.equal(createHud({ storedName: app.hud.forestName }).hud.forestName, '함께 자라는 숲');
  app.hud.setForestName('🌳'.repeat(30));
  assert.equal(Array.from(app.hud.forestName).length, 24);
});

test('empty names cannot be saved, and Cancel/Escape preserve the current name', () => {
  const app = createHud({ storedName: '우리 팀 숲' });
  app.click('edit-forest-name');
  app.elements['forest-name-input'].value = '\t \n'; app.submit();
  assert.equal(app.hud.forestName, '우리 팀 숲');
  assert.equal(app.elements['forest-name-form'].hidden, false);
  assert.ok(app.elements['forest-name-input'].validationMessage);
  app.elements['forest-name-input'].value = '임시 이름'; app.click('cancel-forest-name');
  assert.equal(app.hud.forestName, '우리 팀 숲');
  assert.equal(app.elements['forest-name-form'].hidden, true);
  app.click('edit-forest-name');
  app.elements['forest-name-form'].emit('keydown', { key: 'Escape' });
  assert.equal(app.elements['forest-name-form'].hidden, true);
  assert.equal(app.hud.forestName, '우리 팀 숲');
  const blocked = createHud({ storageBlocked: true });
  assert.equal(blocked.hud.setForestName('새 숲'), true);
  assert.equal(blocked.hud.forestName, '새 숲');
});

test('UI and individual panels can be restored; hidden movement controls release held input', () => {
  const app = createHud();
  app.click('controls-toggle');
  assert.equal(app.elements['controls-content'].hidden, true);
  assert.equal(app.elements['controls-toggle'].getAttribute('aria-expanded'), 'false');
  assert.equal(app.events.at(-1).type, 'forest-controls-hidden');
  app.click('objects-toggle');
  assert.equal(app.elements['placed-list'].hidden, true);
  assert.equal(app.elements['objects-toggle'].textContent, '오브젝트 보이기');
  app.click('edit-forest-name'); app.click('ui-toggle');
  assert.equal(app.classes.has('forest-ui-hidden'), true);
  assert.equal(app.elements['ui-toggle'].textContent, 'UI 보이기');
  assert.equal(app.elements['forest-name-form'].hidden, true);
  assert.equal(app.events.filter(event => event.type === 'forest-controls-hidden').length, 2);
  app.click('ui-toggle');
  assert.equal(app.classes.has('forest-ui-hidden'), false);
  assert.equal(app.elements['controls-content'].hidden, true, 'restoring all UI preserves individual panel preference');
  app.click('controls-toggle'); app.click('objects-toggle');
  assert.equal(app.elements['controls-content'].hidden, false);
  assert.equal(app.elements['placed-list'].hidden, false);
  assert.equal(app.elements['controls-toggle'].getAttribute('aria-expanded'), 'true');
});
