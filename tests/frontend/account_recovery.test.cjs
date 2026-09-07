const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../src/frontend/app.js'), 'utf8');
function harness(api = async () => ({})) {
  const state = { token: 'session' };
  const nodes = {};
  const context = vm.createContext({ state, api, $: key => nodes[key] ||= {}, getAgeFromBirth: () => 52,
    resetEligibilityAnswers() {}, syncLifestyleAvatar() {}, showStep: step => { state.step = step; } });
  for (const name of ['hasHealthDataConsent', 'saveAccountSetup']) {
    const fn = source.match(new RegExp(`^(?:async )?function ${name}\\([^]*?^}`, 'm'));
    assert.ok(fn, name);
    vm.runInContext(fn[0], context);
  }
  const recovery = { token: 'session', birthday: '1974-04-12', gender: 'FEMALE', healthAgreed: true };
  return { state, context, recovery };
}
test('only active health-data consent of the current contract permits continuation', () => {
  const { context } = harness();
  const active = { consent_item: 'health_data', version: '1.0', is_agreed: true };
  assert.equal(context.hasHealthDataConsent({ items: [active] }), true);
  for (const patch of [{ consent_item: 'analytics' }, { version: '0.9' }, { is_agreed: false }, { withdrawn_at: '2026-09-07' }]) {
    assert.equal(context.hasHealthDataConsent({ items: [{ ...active, ...patch }] }), false);
  }
  assert.equal(context.hasHealthDataConsent({}), false);
});
test('unchecked consent causes no request and never advances', async () => {
  const calls = [];
  const { context, recovery, state } = harness(async url => { calls.push(url); });
  recovery.healthAgreed = false;
  await assert.rejects(context.saveAccountSetup(recovery), /동의/);
  assert.equal(calls.length, 0);
  assert.equal(state.step, undefined);
});
test('retry with uncertain consent read fails closed, without duplicate writes', async () => {
  const calls = [];
  const { context, recovery, state } = harness(async url => { calls.push(url); return {}; });
  recovery.profileSaved = true;
  recovery.reconcileConsent = true;
  await assert.rejects(context.saveAccountSetup(recovery), /저장 상태/);
  assert.deepEqual(calls, ['/consents']);
  assert.equal(state.step, undefined);
});
test('account change during profile save cannot send consent under the new session', async () => {
  const calls = [];
  let resolve;
  const { context, recovery, state } = harness(url => { calls.push(url); return new Promise(done => { resolve = done; }); });
  const pending = context.saveAccountSetup(recovery);
  state.token = 'different-session';
  resolve({});
  await assert.rejects(pending, error => error.code === 'SESSION_CHANGED');
  assert.deepEqual(calls, ['/users/me/profile']);
  assert.equal(state.step, undefined);
});
