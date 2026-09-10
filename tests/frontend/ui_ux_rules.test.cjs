const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../../src/frontend/app.js'), 'utf8');
function load(name, data = {}) {
  const context = vm.createContext(data);
  const fn = source.match(new RegExp(`^(?:async )?function ${name}\\([^]*?^}`, 'm'));
  assert.ok(fn);
  vm.runInContext(fn[0], context);
  return context[name];
}
test('medical continuation requires challenge permission and preserves every safety exclusion', () => {
  const state = { capabilities: { challenge: true }, eligibility: { reason_codes: [] }, medicalGuidanceRequired: false };
  const allowed = load('canContinueAfterMedicalGuidance', { state });
  assert.equal(allowed(), true);
  for (const code of ['URGENT_MEDICAL_ATTENTION', 'SAME_DAY_MEDICAL_ATTENTION', 'DIAGNOSED_DIABETES', 'UNDER_MINIMUM_SERVICE_AGE', 'CONSENT_REQUIRED']) {
    state.eligibility.reason_codes = [code];
    assert.equal(allowed(), false, code);
  }
  state.eligibility.reason_codes = [];
  state.capabilities.challenge = false;
  assert.equal(allowed(), false);
  state.capabilities.challenge = true;
  state.medicalGuidanceRequired = true;
  assert.equal(allowed(), false);
});
test('profile writes use current backend path, not GET-only /users/me', () => {
  assert.equal((source.match(/api\("\/users\/me\/profile", \{ method: "PATCH"/g) || []).length, 3);
  assert.doesNotMatch(source, /api\("\/users\/me", \{ method: "PATCH"/);
});
test('current-only allowed user reanalyses, medically restricted user does not', () => {
  const state = { currentHealthOnly: true, capabilities: { currentHealth: true }, medicalGuidanceRequired: false };
  const run = load('shouldRunPredictionAfterHealthEdit', { state });
  assert.equal(run(), true);
  state.medicalGuidanceRequired = true;
  assert.equal(run(), false);
  state.medicalGuidanceRequired = false;
  state.capabilities.currentHealth = false;
  assert.equal(run(), false);
});
test('missing or incomplete forecast stays hidden without throwing', () => {
  const allowed = load('forecastCurveDisplayAllowed');
  for (const forecast of [null, undefined, {}, { public_display_approved: true, risk_curve_status: 'available', points: [] }]) {
    assert.equal(allowed(forecast, true), false);
  }
});
test('error navigation follows field DOM instead of outdated field-name lists', () => {
  let panel, focused = false;
  const focus = load('focusHealthField', {
    document: { getElementById: () => ({ closest: () => ({ id: 'health-activity-panel' }), focus: () => { focused = true; } }) },
    showHealthInputPanel: value => { panel = value; },
  });
  focus('walking-days');
  assert.equal(panel, 'activity');
  assert.equal(focused, true);
});
test('missing snapshot endpoint is explicit and cannot reuse stale snapshot ID', async () => {
  const state = { checkupId: 3, currentScreeningInputId: 99 };
  const save = load('saveCurrentScreeningInputSnapshot', {
    state, detailHealthPayload: () => ({}), isLocalPreview: () => false,
    api: async () => { throw { status: 404 }; },
  });
  await save();
  assert.equal(state.currentScreeningInputSaveUnavailable, true);
  assert.equal(state.currentScreeningInputId, null);
});
