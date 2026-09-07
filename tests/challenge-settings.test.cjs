const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../src/frontend/challenge-v2.js'), 'utf8');
const app = fs.readFileSync(path.join(__dirname, '../src/frontend/app.js'), 'utf8');
const settled = () => new Promise(resolve => setImmediate(resolve));

async function widget({ authenticated = true, enrolled = true, hash = '' } = {}) {
  const handlers = {}, requests = [], message = {}, section = { hidden: true };
  const root = {
    hidden: true, innerHTML: '', parentElement: { matches: () => false },
    addEventListener: (type, listener) => { handlers[type] = listener; },
    querySelector: selector => selector === '[data-message]' ? message : selector === '[data-settings]' ? section : { focus() {} },
  };
  const document = { querySelector: () => root, addEventListener() {}, documentElement: { classList: { add() {} } } };
  const window = { addEventListener() {}, dispatchEvent() {} };
  vm.runInNewContext(source, {
    document, window, location: { hash }, FormData: class {}, CustomEvent: class {},
    fetch: async url => {
      requests.push(url);
      if (url.includes('capabilities')) return { json: async () => ({ data: { enabled: true } }) };
      if (url.includes('refresh')) return { ok: authenticated, json: async () => ({ access_token: 'synthetic' }) };
      return { ok: true, json: async () => ({ data: { enrolled, items: [], preferences: {} } }) };
    },
  });
  await settled();
  return { root, handlers, requests, message, section };
}

test('signed-out users get a return-aware login link, not an unsavable settings form', async () => {
  const { root, message, requests } = await widget({ authenticated: false });
  assert.match(root.innerHTML, /href="\/\?returnTo=forest-challenges"/);
  assert.doesNotMatch(root.innerHTML, /data-preferences/);
  assert.match(message.textContent, /로그인/);
  assert.equal(requests.some(url => url.endsWith('/today')), false);
});

test('settings open button toggles existing form without discarding edits', async () => {
  const { root, handlers, section } = await widget();
  assert.match(root.innerHTML, /aria-expanded="false"/);
  const before = root.innerHTML;
  const button = { setAttribute(key, value) { this[key] = value; } };
  const event = { target: { closest: selector => selector === '[data-open-settings]' ? button : null } };
  await handlers.click(event);
  assert.equal(section.hidden, false);
  assert.equal(button['aria-expanded'], 'true');
  assert.equal(button.textContent, '설정 닫기');
  assert.equal(root.innerHTML, before);
  await handlers.click(event);
  assert.equal(section.hidden, true);
});

test('first setup and a return from login open settings immediately', async () => {
  for (const options of [{ enrolled: false }, { hash: '#daily-settings' }]) {
    const { root } = await widget(options);
    assert.match(root.innerHTML, /aria-expanded="true"/);
    assert.match(root.innerHTML, /data-preferences/);
    assert.doesNotMatch(root.innerHTML, /data-settings hidden/);
  }
});

test('plain-language copy retains privacy, optional photos and medical boundaries', async () => {
  const { root } = await widget({ enrolled: false });
  assert.doesNotMatch(root.innerHTML, /\b(?:AI|V2|T1|T2|T3)\b/);
  for (const text of ['최대 7일', '선택', '보관한 사진을 삭제', '외부 자동 분석 서비스로 보내지', '진단·처방']) {
    assert.ok(root.innerHTML.includes(text), text);
  }
});

test('forest return accepts only the fixed destination and keeps safety exclusions', () => {
  const fn = app.slice(app.indexOf('function returnToForestSettings'), app.indexOf('const $ ='));
  const destinations = [];
  const context = { returningToForest: true, window: { location: { assign: value => destinations.push(value) } } };
  vm.createContext(context);
  vm.runInContext(fn, context);
  for (const reason of ['DIAGNOSED_DIABETES', 'URGENT_MEDICAL_ATTENTION', 'CONSENT_REQUIRED', 'UNDER_MINIMUM_SERVICE_AGE']) {
    assert.equal(context.returnToForestSettings({ service_eligible: true, reason_codes: [reason] }), false);
  }
  assert.equal(context.returnToForestSettings({ service_eligible: false }), false);
  assert.equal(destinations.length, 0);
  assert.equal(context.returnToForestSettings({ service_eligible: true, reason_codes: [] }), true);
  assert.deepEqual(destinations, ['/forest?challenge=settings-v139#daily-settings']);
  context.returningToForest = false;
  assert.equal(context.returnToForestSettings({ service_eligible: true }), false);
});
