const { test } = require('node:test');
const assert = require('node:assert/strict');
const { calculateBmi, challengeTopic, weeklyProgress, summaryContent, mount } = require('../../src/frontend/lifestyle-map.js');

test('BMI converts centimetres and rounds once; zero, missing and invalid inputs never produce a score', () => {
  assert.equal(calculateBmi(165, 64), '23.5');
  assert.equal(calculateBmi('170', '70'), '24.2');
  assert.equal(calculateBmi(165, 62), '22.8');
  for (const value of [null, undefined, '', ' ', false, 0, -1, Infinity, NaN, 'invalid']) {
    assert.equal(calculateBmi(value, 64), null);
    assert.equal(calculateBmi(165, value), null);
  }
});

test('challenge linking uses the mascot summary topics and preserves a separate body record', () => {
  assert.equal(challengeTopic({ title: '7~8시간 수면 기록', category: 'tracking' }), 'metabolic');
  assert.equal(challengeTopic({ title: '체중 추이 확인', category: 'tracking' }), 'body');
  assert.equal(challengeTopic({ title: '식후 10분 가볍게 움직이기' }), 'activity');
  assert.equal(challengeTopic({ title: '가볍게 걷기', category: 'activity' }), 'activity');
  assert.equal(challengeTopic({ title: '덜 달게 마시기' }), 'meals');
  assert.equal(challengeTopic({ challenge_id: 9, title: '새로운 목표' }, [{ challenge_id: 9, category: 'diet' }]), 'meals');
  assert.equal(challengeTopic({ title: '오늘도 금연', category: 'tracking' }), 'metabolic');
  assert.equal(challengeTopic({ title: '정기 검진 확인' }), 'checkup');
  assert.equal(challengeTopic({ title: '친구 초대하기' }), null);
});

test('weekly progress joins by user challenge ID, never title or invented date ticks', () => {
  const report = { challenge_details: [{ user_challenge_id: 2, completed: 0, planned: 7 }] };
  assert.deepEqual(weeklyProgress(report, { user_challenge_id: '2' }), { completed: 0, planned: 7 });
  assert.equal(weeklyProgress(report, { user_challenge_id: 1 }), null);
  for (const row of [{}, { completed: null, planned: 7 }, { completed: 2, planned: 0 }, { completed: 8, planned: 7 }]) {
    assert.equal(weeklyProgress({ challenge_details: [{ ...row, user_challenge_id: 2 }] }, { user_challenge_id: 2 }), null);
  }
});

test('calculator draft persists across topic refresh, never writes saved health, and resets across accounts', () => {
  const nodes = new Map(), handlers = {};
  const element = {
    querySelector(key) {
      if (!nodes.has(key)) nodes.set(key, {
        value: '', textContent: '', innerHTML: '', hidden: false, attrs: {}, style: {}, scrollHeight: 320,
        focus() { this.focused = true; },
        addEventListener(type, fn) { (this.events ||= {})[type] = fn; },
        showModal() { this.open = true; }, close() { this.open = false; this.events.close(); }, classList: { toggle() {} }, setAttribute(name, value) { this.attrs[name] = value; },
        querySelector() { return this.arrow || (this.arrow = { textContent: '' }); },
        getBoundingClientRect() { return { height: this.style.height === '0px' ? 0 : 320 }; },
        appendChild(child) { child.parentNode = this; },
      });
      return nodes.get(key);
    },
    addEventListener(type, fn) { handlers[type] = fn; },
  };
  let snapshot = { owner: 'account-one', health: { checkup_id: 1, height_cm: 165, weight_kg: 64 }, challenges: [], completed: new Set() };
  let carouselOptions, carouselClosed = 0;
  const view = mount(element, { getData: () => snapshot, mountCarousel(root, options) { carouselOptions = options; return { close() { carouselClosed++; } }; } });
  const get = key => element.querySelector(key);
  assert.equal(get('#map-bmi-value').textContent, '23.5');
  for (const label of ['식사', '활동', '생활습관', '정기 점검', '체형 기록']) assert.match(get('#habit-map-topics').innerHTML, new RegExp(label));
  carouselOptions.onOpen('activity');
  assert.equal(get('#habit-detail-metric').textContent, '운동 습관 기록이 필요합니다.');
  snapshot = { ...snapshot, health: { ...snapshot.health, regular_exercise: false } };
  view.refresh();
  assert.equal(get('#habit-detail-metric').textContent, '규칙적인 운동을 하지 않는다고 기록했어요.');
  snapshot = { ...snapshot, dailyStatus: 'ready', completed: new Set(['101', '102']), challenges: [
    { user_challenge_id: 101, title: '식후 10분 천천히 걷기' },
    { user_challenge_id: 102, title: '균형·유연성 운동 주 2회' },
  ], report: { period: { start_date: '2026-09-04', end_date: '2026-09-08' }, challenge_details: [
    { user_challenge_id: 101, completed: 1, planned: 5 },
    { user_challenge_id: 102, completed: 1, planned: 5 },
  ] } };
  view.refresh();
  assert.equal((get('#habit-map-challenges').innerHTML.match(/<progress /g) || []).length, 2);
  assert.equal((get('#habit-map-challenges').innerHTML.match(/1 \/ 5회/g) || []).length, 2);
  snapshot = { ...snapshot, health: { ...snapshot.health, meal_count_yesterday: 3, waist_cm: 91 } };
  view.select('meals');
  assert.equal(get('#habit-detail-metric').textContent, '어제 식사 횟수는 3회로 기록했어요.');
  view.select('body');
  assert.equal(get('#habit-body-panel').hidden, false);
  assert.equal(get('#map-waist').textContent, '저장된 허리둘레 91cm');
  get('#map-weight').value = '70';
  handlers.input({ target: { id: 'map-weight' } });
  assert.equal(get('#map-bmi-value').textContent, '25.7');
  assert.equal(snapshot.health.weight_kg, 64);
  view.select('activity'); view.select('body');
  assert.equal(get('#map-weight').value, '70');
  assert.equal(get('#habit-map-dialog').open, true);
  get('#habit-map-dialog').close();
  assert.equal(get('#habit-map-dialog').hidden, true);
  view.select('body');
  assert.equal(get('#habit-map-dialog').open, true);
  assert.equal(get('#map-weight').value, '70');
  get('#habit-map-dialog').close();
  carouselOptions.onOpen('help');
  assert.ok(carouselClosed > 0);
  assert.equal(carouselOptions.itemLabel, '생활습관');
  assert.equal(get('#habit-map-dialog').open, true);
  assert.equal(get('#lifestyle-help').hidden, false);
  assert.equal(get('#habit-body-panel').hidden, true);
  assert.equal(get('#habit-dialog-title').textContent, '체형 기록 · 도움말');
  handlers.click({ target: { closest: () => ({ id: 'habit-help-back', dataset: {} }) } });
  assert.equal(get('#habit-body-panel').hidden, false);
  assert.equal(get('#map-weight').value, '70');
  get('#map-height').value = '';
  handlers.input({ target: { id: 'map-height' } });
  assert.equal(get('#map-bmi-value').textContent, '—');
  snapshot = { ...snapshot, owner: 'account-two', health: {} };
  view.refresh();
  assert.equal(get('#map-weight').value, '');
  assert.equal(get('#map-bmi-value').textContent, '—');
});

test('mascot summary preserves missing records and distinguishes past smoking and medical follow-up', () => {
  assert.match(summaryContent().metabolic.value, /아직 저장된/);
  assert.match(summaryContent().activity.value, /기록이 필요/);
  assert.match(summaryContent({ meal_count_yesterday: 0 }).meals.value, /0회/);
  assert.match(summaryContent({ smoking_status: 'former' }).metabolic.value, /과거 흡연/);
  assert.match(summaryContent({ current_drinker: true }).metabolic.value, /흡연·음주/);
  assert.match(summaryContent({}, true).checkup.action, /상담 안내를 먼저/);
  assert.equal(calculateBmi(160, 67.5), '26.4');
});
