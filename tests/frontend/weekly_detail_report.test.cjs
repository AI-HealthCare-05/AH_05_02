const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../src/frontend/app.js'), 'utf8');
const start = source.indexOf('const reportDayState =');
const end = source.indexOf('function renderWeeklyChallengeProgress', start);
assert.ok(start >= 0 && end > start, 'weekly detail helpers must exist');
const helpers = source.slice(start, end);

function context(overrides = {}) {
  const sandbox = {
    Date,
    state: { token: 'qa-token', cycle: { start_date: '2026-09-08' } },
    isLocalPreview: () => false,
    api: async () => ({ items: [] }),
    ...overrides,
  };
  vm.runInContext(helpers, vm.createContext(sandbox));
  return sandbox;
}

test('weekly detail follows the challenge start weekday and distinguishes all day states', () => {
  const h = context();
  const records = vm.runInContext(`reportWeekRecords({
    detail_status: 'ready',
    daily_records: [
      { log_date: '2026-09-08', is_completed: true },
      { log_date: '2026-09-09', is_completed: false }
    ]
  }, { period: { end_date: '2026-09-10' } })`, h);
  assert.deepEqual(Array.from(records, item => item.date), [
    '2026-09-08', '2026-09-09', '2026-09-10', '2026-09-11', '2026-09-12', '2026-09-13', '2026-09-14',
  ]);
  assert.deepEqual(Array.from(records, item => item.status), [
    'completed', 'not_completed', 'pending', 'future', 'future', 'future', 'future',
  ]);
});

test('weekly detail composes the existing per-challenge log API without waiting for a new report endpoint', async () => {
  const calls = [];
  const cycle = { start_date: '2026-09-08' };
  const h = context({
    state: { token: 'qa-token', cycle },
    api: async url => {
      calls.push(url);
      return { items: [{ log_date: '2026-09-08', is_completed: true }] };
    },
  });
  h.report = { period: { end_date: '2026-09-10' }, challenge_details: [{ user_challenge_id: 31, title: '걷기', completed: 1, planned: 3 }] };
  h.cycle = cycle;
  const enriched = await vm.runInContext('enrichWeeklyReportDetails(report, "qa-token", cycle)', h);
  assert.deepEqual(calls, ['/user-challenges/31/logs?start_date=2026-09-08&end_date=2026-09-14']);
  assert.equal(enriched.challenge_details[0].detail_status, 'ready');
  assert.equal(enriched.challenge_details[0].daily_records[0].is_completed, true);
});

test('a failed detail request is shown as unavailable instead of fabricated completion', async () => {
  const cycle = { start_date: '2026-09-08' };
  const h = context({ state: { token: 'qa-token', cycle }, api: async () => { throw new Error('offline'); } });
  h.report = { period: { end_date: '2026-09-10' }, challenge_details: [{ user_challenge_id: 31, title: '걷기' }] };
  h.cycle = cycle;
  const enriched = await vm.runInContext('enrichWeeklyReportDetails(report, "qa-token", cycle)', h);
  assert.equal(enriched.challenge_details[0].detail_status, 'error');
  h.item = enriched.challenge_details[0];
  const records = vm.runInContext('reportWeekRecords(item, report)', h);
  assert.deepEqual(Array.from(records, item => item.status), [
    'unavailable', 'unavailable', 'pending', 'future', 'future', 'future', 'future',
  ]);
});
