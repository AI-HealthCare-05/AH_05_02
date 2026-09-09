const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const source = readFileSync(path.join(__dirname, '../src/frontend/forest-game.js'), 'utf8');

function section(start, end) {
  const begin = source.indexOf(start), finish = source.indexOf(end, begin);
  assert.ok(begin >= 0 && finish > begin, `chat source boundary exists: ${start}`);
  return source.slice(begin, finish);
}

function setup({ phaserActive = true } = {}) {
  const elements = new Map(), timers = new Map(), windowListeners = new Map(), events = [], keys = [];
  let nextTimer = 0, modal = null;
  const document = {
    activeElement: null,
    querySelector: () => modal,
    addEventListener(type, callback) { if (type === 'keydown') keys.push(callback); },
  };
  function element(tagName = 'DIV') {
    const listeners = new Map(), attributes = new Map();
    return {
      tagName, hidden: false, value: '', textContent: '', children: [], isContentEditable: false,
      addEventListener(type, callback) { listeners.set(type, callback); },
      emit(type, values = {}) {
        const event = { type, target: this, defaultPrevented: false,
          preventDefault() { this.defaultPrevented = true; }, ...values };
        listeners.get(type)?.(event);
        return event;
      },
      setAttribute(name, value) { attributes.set(name, value); },
      getAttribute(name) { return attributes.get(name); },
      focus() { document.activeElement = this; },
      append(...children) { for (const child of children) { child.parent = this; this.children.push(child); } },
      remove() { this.parent.children.splice(this.parent.children.indexOf(this), 1); },
      get firstElementChild() { return this.children[0]; },
      get scrollHeight() { return this.children.length * 20; },
    };
  }
  for (const [id, tag] of [['chat-panel', 'SECTION'], ['chat-input', 'INPUT'], ['chat-form', 'FORM'],
    ['chat-toggle', 'BUTTON'], ['chat-close', 'BUTTON'], ['ui-toggle', 'BUTTON'], ['chat-messages', 'DIV'], ['phaser-world', 'DIV']]) {
    elements.set(`#${id}`, element(tag));
  }
  const classes = new Set(), canvas = element('CANVAS');
  document.body = { classList: { contains: name => classes.has(name) } };
  document.createElement = element;
  document.activeElement = elements.get('#phaser-world');
  elements.get('#chat-panel').hidden = true;
  const window = {
    carrotForestPhaserActive: phaserActive,
    clearTimeout: id => timers.delete(id),
    setTimeout(callback) { timers.set(++nextTimer, callback); return nextTimer; },
    dispatchEvent: event => events.push(event),
    addEventListener: (type, callback) => windowListeners.set(type, callback),
  };
  const context = vm.createContext({
    window, document, canvas, $: id => elements.get(id), state: { avatar: { name: '숲 친구' } },
    renderSceneChrome() {},
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options?.detail; } },
  });
  vm.runInContext(section('  let chatFocusTimer = 0;', '  async function toggleSit()') +
    section('  $("#chat-close").addEventListener', '  $("#music-toggle").addEventListener'), context);
  const get = id => elements.get(`#${id}`);
  return {
    get, document, canvas, events, classes, element,
    setModal: value => { modal = value; },
    flushTimers() { const pending = [...timers.values()]; timers.clear(); pending.forEach(callback => callback()); },
    key(key, options = {}) {
      const event = { key, target: document.activeElement, defaultPrevented: false,
        preventDefault() { this.defaultPrevented = true; }, ...options };
      keys.forEach(callback => callback(event));
      return event;
    },
  };
}

test('C and Enter open collapsed chat once, release movement and defer input focus until keydown finishes', () => {
  for (const key of ['c', 'C', 'Enter']) {
    const app = setup(), originalFocus = app.document.activeElement;
    const event = app.key(key);
    assert.equal(event.defaultPrevented, true);
    assert.equal(app.get('chat-panel').hidden, false);
    assert.equal(app.get('chat-toggle').hidden, true);
    assert.equal(app.get('chat-toggle').getAttribute('aria-expanded'), 'true');
    assert.equal(app.events[0].type, 'forest-controls-hidden');
    assert.equal(app.document.activeElement, originalFocus, 'opening Enter cannot land in the input and submit during the same keydown');
    app.flushTimers();
    assert.equal(app.document.activeElement, app.get('chat-input'));
  }
});

test('C and Escape close focused chat, restore its launcher and return keyboard movement focus', () => {
  for (const key of ['c', 'C', 'Escape']) {
    const app = setup();
    app.key('c'); app.flushTimers();
    app.get('chat-input').value = '입력 중인 문장';
    assert.equal(app.key(key).defaultPrevented, true);
    assert.equal(app.get('chat-panel').hidden, true);
    assert.equal(app.get('chat-toggle').hidden, false);
    assert.equal(app.get('chat-toggle').getAttribute('aria-expanded'), 'false');
    assert.equal(app.document.activeElement, app.get('phaser-world'));
    assert.equal(app.get('chat-input').value, '입력 중인 문장');
    app.flushTimers();
    assert.equal(app.document.activeElement, app.get('phaser-world'));
  }
  const fallback = setup({ phaserActive: false });
  fallback.key('c'); fallback.flushTimers(); fallback.key('Escape');
  assert.equal(fallback.document.activeElement, fallback.canvas);
});

test('rapid open/close and the close button cancel pending focus callbacks', () => {
  const app = setup();
  app.key('c'); app.key('c'); app.flushTimers();
  assert.equal(app.document.activeElement, app.get('phaser-world'));
  assert.equal(app.get('chat-panel').hidden, true);
  app.get('chat-toggle').emit('click');
  app.get('chat-close').emit('click'); app.flushTimers();
  assert.equal(app.document.activeElement, app.get('phaser-world'));
  assert.equal(app.get('chat-panel').hidden, true);
});

test('normal editable controls retain C, Enter and Escape, including contenteditable text', () => {
  for (const tagName of ['INPUT', 'TEXTAREA', 'SELECT', 'DIV']) {
    for (const key of ['c', 'Enter', 'Escape']) {
      const app = setup(), field = app.element(tagName);
      field.isContentEditable = tagName === 'DIV';
      field.focus();
      assert.equal(app.key(key).defaultPrevented, false);
      assert.equal(app.get('chat-panel').hidden, true);
      assert.equal(app.events.length, 0);
      assert.equal(app.document.activeElement, field);
    }
  }
  const app = setup();
  app.key('c'); app.flushTimers();
  const field = app.element('INPUT'); field.focus();
  assert.equal(app.key('Escape').defaultPrevented, false);
  assert.equal(app.get('chat-panel').hidden, false, 'editing another form does not collapse chat');
  app.get('chat-close').focus();
  assert.equal(app.key('Enter').defaultPrevented, false, 'native button activation must not be hijacked');
});

test('modal, composing, repeated and modified keydowns never toggle chat', () => {
  for (const modal of [{ open: true }, { id: 'reward-celebration' }]) {
    const app = setup(); app.setModal(modal);
    for (const key of ['c', 'Enter', 'Escape']) {
      assert.equal(app.key(key).defaultPrevented, false);
      assert.equal(app.get('chat-panel').hidden, true);
    }
  }
  for (const options of [{ isComposing: true }, { repeat: true }, { ctrlKey: true },
    { altKey: true }, { metaKey: true }, { defaultPrevented: true }]) {
    const app = setup();
    app.key('c', options); app.key('Enter', options);
    assert.equal(app.get('chat-panel').hidden, true);
    assert.equal(app.events.length, 0);
    app.key('c'); app.flushTimers();
    app.key('c', options); app.key('Escape', options);
    assert.equal(app.get('chat-panel').hidden, false);
    assert.equal(app.document.activeElement, app.get('chat-input'));
  }
});

test('Enter inside chat retains native form submission, renders plain text and keeps focus and chat open', () => {
  const app = setup(); app.key('Enter'); app.flushTimers();
  app.get('chat-input').value = '  함께 걸어요 <img src=x onerror=alert(1)>  ';
  const key = app.key('Enter');
  assert.equal(key.defaultPrevented, false, 'chat Enter must reach the form submission default action');
  assert.equal(app.get('chat-form').emit('submit').defaultPrevented, true);
  const row = app.get('chat-messages').children[0];
  assert.equal(row.children[0].textContent, '숲 친구');
  assert.equal(row.children[1].textContent, '함께 걸어요 <img src=x onerror=alert(1)>');
  assert.equal(app.get('chat-input').value, '');
  assert.equal(app.get('chat-panel').hidden, false);
  assert.equal(app.document.activeElement, app.get('chat-input'));
  app.get('chat-input').value = ' \n '; app.get('chat-form').emit('submit');
  assert.equal(app.get('chat-messages').children.length, 1);
  for (let i = 0; i < 52; i++) {
    app.get('chat-input').value = `message ${i}`; app.get('chat-form').emit('submit');
  }
  assert.equal(app.get('chat-messages').children.length, 50);
  assert.equal(app.get('chat-messages').children[0].children[1].textContent, 'message 2');
  assert.equal(app.get('chat-messages').scrollTop, app.get('chat-messages').scrollHeight);
});

test('hiding the overall HUD closes chat and releases input focus; restoring HUD does not reopen it', () => {
  const app = setup(); app.key('c'); app.flushTimers();
  app.classes.add('forest-ui-hidden'); app.get('ui-toggle').emit('click');
  assert.equal(app.get('chat-panel').hidden, true);
  assert.equal(app.document.activeElement, app.get('phaser-world'));
  app.classes.delete('forest-ui-hidden'); app.get('ui-toggle').emit('click');
  assert.equal(app.get('chat-panel').hidden, true);
});
