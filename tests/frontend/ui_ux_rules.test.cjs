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
function loadMany(names, data = {}) {
  const context = vm.createContext(data);
  for (const name of names) {
    const fn = source.match(new RegExp(`^(?:async )?function ${name}\\([^]*?^}`, 'm'));
    assert.ok(fn, name);
    vm.runInContext(fn[0], context);
  }
  return context;
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
test('XAI explanation cards show only approved returned factors with safe labels', () => {
  const nodes = {
    '#current-factor-list': { innerHTML: '' },
    '#factor-list': { innerHTML: '' },
  };
  const state = { currentScreeningPrediction: { screening_signal_detected: false }, prediction: { risk_category: 'low' } };
  const context = loadMany(['normalizeRiskKey', 'factorDirectionLabel', 'factorModifiableLabel', 'renderFactorItems', 'selectXaiFactors', 'renderXaiExplanationLists'], {
    state,
    $: selector => nodes[selector] || null,
    escapeHtml: value => String(value).replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]),
  });
  const render = context.renderXaiExplanationLists;
  const approvedFactors = { status: 'approved', shap_claimed: true, display_allowed: true, items: [{ display_name: '걷기 시간', direction: 'decrease', modifiable: true, message: '모델 점수를 낮춘 방향입니다.' }] };
  render(approvedFactors, { approved: true, currentFactors: approvedFactors, currentApproved: true });
  assert.match(nodes['#current-factor-list'].innerHTML, /걷기 시간/);
  assert.match(nodes['#factor-list'].innerHTML, /걷기 시간/);
  assert.match(nodes['#factor-list'].innerHTML, /긍정 요인 · 점수를 낮춘 방향 · 바꿀 수 있는 요인/);
  render({ ...approvedFactors, display_allowed: false }, { approved: true });
  assert.doesNotMatch(nodes['#factor-list'].innerHTML, /걷기 시간/);
  render({ items: [{ display_name: '임의 표시 금지' }] }, { approved: false });
  assert.doesNotMatch(nodes['#factor-list'].innerHTML, /임의 표시 금지/);
  assert.match(nodes['#factor-list'].innerHTML, /미래 위험 XAI 연결 대기/);
});
test('XAI picks directional 2+1 without padding and hides unknown result states', () => {
  const context = loadMany(['factorDirectionLabel', 'selectXaiFactors']);
  const items = [-0.1, 0.4, -0.3, 0.2, 0, NaN].map((value, index) => ({
    feature: String(index), contribution: value, direction: value > 0 ? 'increase' : 'decrease',
  }));
  const select = context.selectXaiFactors;
  assert.deepEqual(Array.from(select(items, false), i => i.contribution), [-0.3, -0.1, 0.4]);
  assert.deepEqual(Array.from(select(items, true), i => i.contribution), [0.4, 0.2, -0.3]);
  assert.equal(select(items, null).length, 0);
  assert.equal(select(items.filter(i => i.contribution > 0), false).length, 1);
});
test('model conflict guidance prioritizes current signal and never treats failure as low risk', () => {
  const context = loadMany(['normalizeRiskKey', 'isPublicRiskDisplayAllowed', 'modelComparisonGuidance']);
  const approved = risk => ({
    risk_category: risk,
    result_status: 'approved',
    promotion_status: 'approved',
    display_allowed: true,
  });
  const current = { status: 'succeeded', prediction: approved('high') };
  const future = { status: 'succeeded', prediction: approved('low') };
  assert.equal(context.modelComparisonGuidance(current, future).code, 'CURRENT_SIGNAL_FUTURE_LOW');
  assert.match(context.modelComparisonGuidance(current, future).message, /현재 신호 확인을 우선/);
  const incomplete = context.modelComparisonGuidance(current, { status: 'failed' });
  assert.equal(incomplete.code, 'MODEL_RESULT_INCOMPLETE');
  assert.match(incomplete.message, /낮은 위험을 의미하지 않습니다/);
});

test('unapproved model outputs cannot create a public conflict explanation', () => {
  const context = loadMany(['normalizeRiskKey', 'isPublicRiskDisplayAllowed', 'modelComparisonGuidance']);
  const research = { status: 'succeeded', prediction: { risk_category: 'high', display_allowed: false } };
  const result = context.modelComparisonGuidance(research, research);
  assert.equal(result.code, 'MODEL_RESULT_NOT_PUBLIC');
  assert.equal(result.display, false);
});
