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
test('unsupported periods and local fixtures never request a mislabeled weekly PDF', async () => {
  let calls = 0;
  const state = { token: 'qa-session' };
  const context = load(['reportPdfUnavailableReason', 'fetchWeeklyReportPdf'], {
    state, isLocalPreview: () => state.token === 'local-demo-token', fetch: async () => { calls++; },
  });
  for (const period of ['four-week', 'all', 'invalid']) await assert.rejects(context.fetchWeeklyReportPdf(period), /연결 준비/);
  state.token = 'local-demo-token';
  await assert.rejects(context.fetchWeeklyReportPdf('week'), /실제 계정/);
  state.token = null;
  await assert.rejects(context.fetchWeeklyReportPdf('week'), /실제 계정/);
  assert.equal(calls, 0);
});
test('weekly PDF uses supported endpoint and rejects failed or non-PDF responses', async () => {
  let mode = 'ok';
  const context = load(['reportPdfUnavailableReason', 'fetchWeeklyReportPdf'], {
    state: { token: 'qa-session' }, isLocalPreview: () => false,
    fetch: async url => {
      assert.equal(url, '/api/v1/weekly-reports/current/pdf');
      return { ok: mode !== 'failed', status: 503, headers: { get: () => mode === 'html' ? 'text/html' : 'application/pdf' }, blob: async () => 'pdf-response-fixture' };
    },
  });
  assert.equal(await context.fetchWeeklyReportPdf('week'), 'pdf-response-fixture');
  mode = 'html';
  await assert.rejects(context.fetchWeeklyReportPdf('week'), /올바른 PDF/);
  mode = 'failed';
  await assert.rejects(context.fetchWeeklyReportPdf('week'), /만들지 못/);
});
test('saving a daily completion cannot replace the weekly report with a one-day denominator', () => {
  const nodes = { '#dashboard-complete': {}, '#report-week-streak': { textContent: '최근 7일 기록' } };
  const context = load(['updateDailyRecordSummary'], {
    state: { dailyCompleted: new Set(['1']) }, $: key => nodes[key], renderTodayTaskStatus() {},
    renderWeeklyChallengeProgress() { throw new Error('Daily data must not render a weekly aggregate'); },
  });
  context.updateDailyRecordSummary();
  assert.equal(nodes['#dashboard-complete'].textContent, '1개');
  assert.equal(nodes['#report-week-streak'].textContent, '최근 7일 기록');
});
