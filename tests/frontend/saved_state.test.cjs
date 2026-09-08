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

test('saved health restores nullable values, radio choices and exercise; reopening keeps draft', () => {
  const state = { healthCheckupHistory: [{ checkup_id: 4, height_cm: 170, weight_kg: 70, waist_cm: null,
    smoking_status: 'former', current_drinker: false, regular_exercise: true,
    exercise_days_per_week: 5, exercise_minutes: 45, meal_count_yesterday: 0 }] };
  const nodes = {};
  const $ = key => nodes[key] ||= { value: 'default', dataset: {}, disabled: true, classList: { toggle() {} } };
  const radios = Object.fromEntries(['smoking-status', 'current-drinker', 'regular-exercise'].map(name =>
    [name, (name === 'smoking-status' ? ['never', 'former', 'current'] : ['true', 'false']).map(value => ({ value, checked: false }))]));
  const context = load(['hydrateSavedHealthForm', 'syncExerciseDetails'], {
    state, $, $$: selector => radios[selector.match(/name="([^"]+)"/)[1]],
    selectedRadioValue: name => radios[name].find(input => input.checked)?.value,
    syncAlcoholFrequencyDetails() {}, syncLifestyleAvatar() {},
  });
  context.hydrateSavedHealthForm();
  assert.equal($('#height').value, 170);
  assert.equal($('#waist').value, '');
  assert.equal($('#meal-count').value, 0);
  assert.equal($('#exercise-days').value, 5);
  assert.equal($('#exercise-minutes').value, 45);
  assert.equal($('#exercise-days').disabled, false);
  assert.equal(radios['smoking-status'][1].checked, true);
  assert.equal(radios['current-drinker'][1].checked, true);
  $('#weight').value = '72';
  context.hydrateSavedHealthForm();
  assert.equal($('#weight').value, '72');
  state.healthCheckupHistory[0] = { checkup_id: 5, weight_kg: 74, regular_exercise: false };
  context.hydrateSavedHealthForm();
  assert.equal($('#weight').value, 74);
  assert.equal($('#exercise-days').disabled, true);
  state.healthCheckupHistory[0] = { checkup_id: 6, regular_exercise: true };
  context.hydrateSavedHealthForm();
  assert.equal($('#exercise-days').value, '');
  assert.equal($('#exercise-minutes').value, '');
});

function dailyHarness(api) {
  const state = { token: 'test-only', cycle: { user_challenges: [{ user_challenge_id: 1 }, { user_challenge_id: 2 }] }, dailyCompleted: new Set(['old']) };
  const context = load(['loadDailyRecords'], {
    state, api, isLocalPreview: () => false,
    challengeDay: () => new Date().toISOString().slice(0, 10),
    renderDailyRecordList() {}, renderTodayTaskStatus() {},
  });
  return { state, read: context.loadDailyRecords };
}
test('today logs restore only completed records, and successful empty logs clear prior state', async () => {
  const today = new Date().toISOString().slice(0, 10);
  let empty = false;
  const { state, read } = dailyHarness(async url => {
    assert.ok(url.includes(`start_date=${today}&end_date=${today}`));
    return { items: empty ? [] : [{ log_date: today, is_completed: url.includes('/1/') }, { log_date: '2000-01-01', is_completed: true }] };
  });
  await read();
  assert.deepEqual([...state.dailyCompleted], ['1']);
  assert.equal(state.dailyRecordsStatus, 'ready');
  empty = true;
  await read();
  assert.equal(state.dailyCompleted.size, 0);
});
test('failed or malformed read preserves records and exposes retry; retry recovers', async () => {
  let mode = 'fail';
  const { state, read } = dailyHarness(async () => {
    if (mode === 'fail') throw new Error('503');
    return mode === 'malformed' ? {} : { items: [] };
  });
  for (mode of ['fail', 'malformed']) {
    await read();
    assert.equal(state.dailyRecordsStatus, 'error');
    assert.deepEqual([...state.dailyCompleted], ['old']);
  }
  mode = 'ready';
  await read();
  assert.equal(state.dailyRecordsStatus, 'ready');
});
test('an old cycle response cannot replace the new cycle or login state', async () => {
  const resolvers = [];
  const { state, read } = dailyHarness(() => new Promise(resolve => resolvers.push(resolve)));
  const pending = read();
  state.cycle = { user_challenges: [] };
  state.token = 'different-test-session';
  state.dailyCompleted = new Set(['new']);
  resolvers.forEach(resolve => resolve({ items: [] }));
  await pending;
  assert.deepEqual([...state.dailyCompleted], ['new']);
});
