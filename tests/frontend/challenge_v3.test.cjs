const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../src/frontend/app.js'), 'utf8');
function load(names, data) {
  const context = vm.createContext(data);
  for (const name of names) {
    const fn = source.match(new RegExp(`^(?:async )?function ${name}\\([^]*?^}`, 'm'));
    assert.ok(fn, name);
    vm.runInContext(fn[0], context);
  }
  return context;
}
test('preview keeps three domains and bounded non-preferred difficulty without fake AI proof', () => {
  const catalog = ['v3_hydration_choice', ...['easy', 'moderate', 'advanced'].flatMap(level =>
    ['wholegrain', 'walk', 'indoor_aerobic'].map(kind => `v3_${kind}_${level}`))].map(code => ({ code }));
  const context = load(['previewV3Recommendations'], {});
  for (const [focus, expected] of [['diet', ['advanced', 'moderate']], ['activity', ['moderate', 'advanced']], ['balanced', ['advanced', 'advanced']]]) {
    for (let rotation = 0; rotation < 8; rotation++) {
      const result = context.previewV3Recommendations(catalog, focus, 'advanced', rotation);
      assert.equal(result.items.length, 3);
      assert.equal(result.items[0].code, 'v3_hydration_choice');
      assert.ok(result.items[1].code.endsWith(expected[0]));
      assert.ok(result.items[2].code.endsWith(expected[1]));
      assert.equal(result.photo_review_available, false);
    }
  }
});
function recommendationHarness(api) {
  const nodes = {};
  const $ = key => nodes[key] ||= { value: key.includes('difficulty') ? 'easy' : 'balanced', hidden: true, disabled: false, replaceChildren() {} };
  const state = { token: 'session-A' };
  const challengeV3 = { active: false, busy: false, owner: null, request: 0, rotation: 0, focus: 'balanced', difficulty: 'easy' };
  let renders = 0;
  const context = load(['loadChallenges'], {
    $, state, challengeV3, api, URLSearchParams, isLocalPreview: () => false,
    showChallengeSelectionView() {}, updateChallengeStartState() {},
    closeRagChallengeGenerator() {}, renderChallengeChoices() { renders++; }, showMessage() {},
  });
  return { ...context, $, state, challengeV3, renders: () => renders };
}
const result = () => ({ items: [1, 2, 3].map(challenge_id => ({ challenge_id, catalog_version: 'evidence-v3' })), policy: {} });
test('late follow-up response cannot expose previous session identifiers', async () => {
  let resolveActions;
  const harness = recommendationHarness(async url => url.startsWith('/challenge-recommendations')
    ? { ...result(), medical_guidance_required_first: true }
    : new Promise(resolve => { resolveActions = resolve; }));
  const pending = harness.loadChallenges();
  await new Promise(resolve => setImmediate(resolve));
  harness.state.token = 'session-B';
  resolveActions({ items: [{ action_id: 123 }] });
  await pending;
  assert.deepEqual([...harness.state.openFollowUpActionIds], []);
  assert.equal(harness.renders(), 0);
  assert.equal(harness.$('#start-challenge').disabled, true);
});
test('new account request is not blocked by previous request and old finalizer cannot alter it', async () => {
  const pendingResults = [];
  const harness = recommendationHarness(() => new Promise(resolve => pendingResults.push(resolve)));
  const first = harness.loadChallenges();
  harness.state.token = 'session-B';
  const second = harness.loadChallenges();
  pendingResults[0](result());
  await first;
  assert.equal(harness.challengeV3.busy, true);
  assert.equal(harness.$('#start-challenge').disabled, true);
  pendingResults[1](result());
  await second;
  assert.equal(harness.challengeV3.owner, 'session-B');
  assert.equal(harness.challengeV3.busy, false);
  assert.equal(harness.renders(), 1);
});
test('daily log lookup uses Korean date around UTC previous day', async () => {
  const state = { token: 'test', cycle: { user_challenges: [{ user_challenge_id: 2 }] } };
  const context = load(['isServerChallengeId', 'clearCurrentChallengeCycle', 'loadDailyRecords'], {
    hasCurrentChallengeCycle: () => true, state, challengeDay: () => '2026-09-09', isLocalPreview: () => false,
    renderDailyRecordList() {}, renderTodayTaskStatus() {},
    $: () => ({ innerHTML: '' }),
    api: async url => {
      assert.ok(url.endsWith('start_date=2026-09-09&end_date=2026-09-09'));
      return { items: [{ log_date: '2026-09-09', is_completed: true }] };
    },
  });
  await context.loadDailyRecords();
  assert.deepEqual([...state.dailyCompleted], ['2']);
});
test('V3 photo card states proof scope, not simple-check fallback', () => {
  const list = { innerHTML: '', closest() { return this; } };
  const context = load(['renderDailyRecordList'], {
    hasCurrentChallengeCycle: () => true, $: () => list, state: { dailyCompleted: new Set(), cycle: { user_challenges: [{
      user_challenge_id: 1, title: '걷기', catalog_version: 'evidence-v3', verification_type: 2,
      daily_goal: '누적 20분', verification_scope: '사진 제출만 확인',
    }] } }, challengeRecordType: () => 'photo', habitRecordIcon: () => '',
    challengeProofLabel: type => `유형 ${type}`, escapeHtml: value => value,
    recordActionLabel: () => '사진 제출',
  });
  context.renderDailyRecordList();
  assert.match(list.innerHTML, /누적 20분/);
  assert.match(list.innerHTML, /사진 제출만 확인/);
  assert.match(list.innerHTML, /^<button class="daily-record-card daily-record-open/);
  assert.doesNotMatch(list.innerHTML, /record-type-badge/);
  assert.doesNotMatch(list.innerHTML, /간편 체크/);
});

function photoHarness(response) {
  const target = { id: '9', item: { catalog_version: 'evidence-v3', verification_type: 2, goal: { target_minutes: 20 } } };
  const state = { token: 'session-A', cycle: { cycle_id: 1 }, recordTarget: target, dailyCompleted: new Set() };
  const nodes = { '#v3-photo-file': { files: [{ size: 1200 }] }, '#v3-photo-value': { value: '20' } };
  const $ = key => nodes[key] ||= {};
  let calls = 0;
  let photoState;
  const formFields = {};
  const context = load(['submitV3Photo'], {
    $, state, isLocalPreview: () => false, challengeDay: () => '2026-09-09',
    FormData: class { append(key, value) { formFields[key] = value; } },
    setButtonBusy: () => () => {}, showPhotoRecordState(value) { photoState = value; },
    api: async (url, options) => { calls++; assert.match(url, /\/9\/photo-verifications$/); assert.equal(options.method, 'POST'); return await response(); },
    renderDailyRecordList() {}, updateDailyRecordSummary() {}, showMessage() {}, loadWeeklyReport: async () => {},
  });
  return { ...context, $, state, target, fields: formFields, calls: () => calls, photoState: () => photoState };
}
test('HTTP success without accepted completion never marks a photo challenge done', async () => {
  for (const response of [
    { challenge_completed: false, review_status: 'needs_review' },
    { challenge_completed: true, review_status: 'needs_review' },
    { challenge_completed: 'true', review_status: 'accepted' },
  ]) {
    const h = photoHarness(async () => response);
    await h.submitV3Photo();
    assert.equal(h.state.dailyCompleted.size, 0);
    assert.equal(h.photoState(), 'photo-state-fail');
    assert.equal(h.target.submitting, false);
  }
});
test('accepted photo uses self-reported amount and Korean date, and cannot submit twice', async () => {
  const h = photoHarness(async () => ({ challenge_completed: true, review_status: 'accepted' }));
  await h.submitV3Photo();
  await h.submitV3Photo();
  assert.equal(h.calls(), 1);
  assert.equal(h.fields.actual_value, '20');
  assert.equal(h.fields.verification_date, '2026-09-09');
  assert.ok(h.state.dailyCompleted.has('9'));
  assert.equal(h.photoState(), 'photo-state-success');
});
test('late photo responses cannot mark a new account or a new cycle done', async () => {
  for (const change of ['token', 'cycle']) {
    let resolve;
    const h = photoHarness(() => new Promise(r => { resolve = r; }));
    const pending = h.submitV3Photo();
    await h.submitV3Photo();
    assert.equal(h.calls(), 1);
    if (change === 'token') h.state.token = 'session-B';
    else h.state.cycle = { cycle_id: 2 };
    resolve({ challenge_completed: true, review_status: 'accepted' });
    await pending;
    assert.equal(h.state.dailyCompleted.size, 0);
  }
});
test('missing, insufficient and out-of-contract amounts send no photo request', async () => {
  for (const amount of ['', '0', '19', '721', 'Infinity']) {
    const h = photoHarness(async () => { throw new Error('must not submit'); });
    h.$('#v3-photo-value').value = amount;
    await h.submitV3Photo();
    assert.equal(h.calls(), 0);
  }
});
