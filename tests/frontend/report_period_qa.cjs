const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:8022';
assert.ok(['localhost', '127.0.0.1'].includes(new URL(base).hostname));
(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}) });
  try {
    const page = await browser.newPage({ viewport: { width: 380, height: 844 } });
    const errors = [];
    const pdfCalls = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/api/v1/weekly-reports/current', route => route.fulfill({ contentType: 'application/json', body: JSON.stringify({ data: {
      status: 'ready', period: { start_date: '2026-09-01', end_date: '2026-09-07' }, record_summary: '최근 7일 기록 6회',
      challenge_details: [{ user_challenge_id: 31, title: '걷기', completed: 6, planned: 7 }],
    } }) }));
    await page.route('**/api/v1/user-challenges/31/logs?*', route => route.fulfill({ contentType: 'application/json', body: JSON.stringify({ data: {
      items: [
        { log_date: '2026-09-01', is_completed: true },
        { log_date: '2026-09-02', is_completed: false },
      ],
    } }) }));
    await page.route('**/api/v1/weekly-reports/current/pdf*', route => {
      pdfCalls.push(route.request().url());
      return route.fulfill({ status: 503, contentType: 'application/json', body: '{}' });
    });
    await page.route('**/api/v1/reports?period=*', route => {
      const period = new URL(route.request().url()).searchParams.get('period');
      const shared = {
        status: 'ready', report_id: `rpt-${period}-qa`, headline: period === 'all' ? '차곡차곡 쌓인 기록이에요.' : '지난 4주 달성률은 62.5%예요.',
        period: { start_date: '2026-08-04', end_date: '2026-08-31', is_partial: false },
        summary: { practiced_days: 12, completed_count: 14, completion_rate: 62.5, completed_cycles_count: 2 },
        disclaimer: '기록 변화와 수행률은 진단 또는 치료 효과를 의미하지 않습니다.',
      };
      const data = period === 'all'
        ? { ...shared, cycles: { items: [{ cycle_id: '2', cycle_number: 2, start_date: '2026-08-04', end_date: '2026-08-31', status: 'completed', selected_challenges: [{ title: '빠르게 걷기' }], practiced_days: 12, completed_count: 14, completion_rate: 62.5 }], next_cursor: '1' } }
        : { ...shared, trend: { unit: 'week', buckets: [{ start_date: '2026-08-04', end_date: '2026-08-10', participation_days: 7, practiced_days: 4 }] }, challenges: [{ title: '빠르게 걷기', frequency: 'unconfirmed', record_count: 4, completion_rate: null }] };
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ data }) });
    });
    await page.route('**/api/v1/reports/rpt-all-qa/cycles?cursor=1', route => route.fulfill({ contentType: 'application/json', body: JSON.stringify({ data: {
      items: [{ cycle_id: '1', cycle_number: 1, start_date: '2026-07-07', end_date: '2026-08-03', status: 'completed', selected_challenges: [{ title: '물 마시기' }], practiced_days: 10, completed_count: 11, completion_rate: 55 }],
      next_cursor: null,
    } }) }));
    await page.goto(base, { waitUntil: 'domcontentloaded' });
    await page.evaluate(async () => { state.token = 'qa-session'; showStep(8); showWorkspace('report', { moveFocus: false }); await loadWeeklyReport(); });
    assert.equal(await page.locator('#report-week-period').innerText(), '9/1~9/7');
    assert.equal(await page.locator('.report-progress-detailed').count(), 1);
    assert.equal(await page.locator('.report-progress-detailed .report-day').count(), 7);
    assert.equal(await page.locator('.report-progress-detailed .report-day i.completed').count(), 1);
    assert.equal(await page.locator('.report-progress-detailed .report-day i.not_completed').count(), 1);
    assert.equal(await page.locator('.report-progress-detailed .report-day i.unrecorded').count(), 4);
    assert.equal(await page.locator('.report-progress-detailed .report-day i.pending').count(), 1);
    console.log('PASS weekly report renders selected challenge from its start weekday with daily states');
    await page.evaluate(() => { state.dailyCompleted = new Set(['1']); updateDailyRecordSummary(); });
    assert.equal(await page.locator('#report-week-streak').innerText(), '최근 7일 기록 6회');
    console.log('PASS weekly totals are not replaced by today-only records');
    await page.locator('#report-period-four-week').click();
    await page.locator('#report-four-week-status').filter({ hasText: '조회 완료' }).waitFor();
    assert.match(await page.locator('#report-panel-four-week').innerText(), /4\/7일/);
    assert.match(await page.locator('#report-panel-four-week').innerText(), /목표 달성률은 표시하지 않음/);
    console.log('PASS four-week report uses participation days and preserves unconfirmed goals');
    await page.locator('#report-period-all').click();
    assert.equal(await page.locator('#report-period-all').getAttribute('aria-selected'), 'true');
    await page.locator('#report-all-status').filter({ hasText: '조회 완료' }).waitFor();
    assert.equal(await page.locator('.report-cycle-card').count(), 1);
    await page.locator('.report-load-more').click();
    await page.waitForFunction(() => document.querySelectorAll('.report-cycle-card').length === 2);
    assert.equal(await page.locator('.report-cycle-card').count(), 2);
    console.log('PASS all-period report appends cursor-paginated cycles');
    await page.evaluate(() => {
      window.__printCalls = 0;
      window.print = () => { window.__printCalls += 1; };
    });
    await page.locator('#download-report').click();
    assert.equal(await page.locator('#report-pdf-options').evaluate(node => getComputedStyle(node).position), 'absolute');
    assert.ok((await page.locator('#report-pdf-options').boundingBox()).width <= 300);
    assert.match(await page.locator('#report-pdf-status').innerText(), /현재 선택한 리포트 화면/);
    await page.locator('#report-pdf-options label').filter({ hasText: '지난 4주' }).click();
    assert.equal(await page.locator('#report-period-four-week').getAttribute('aria-selected'), 'true');
    await page.waitForFunction(() => !document.querySelector('#download-report').disabled);
    assert.ok(await page.locator('#download-report').isEnabled());
    await page.locator('#download-report').click();
    await page.waitForFunction(() => window.__printCalls === 1);
    assert.equal(pdfCalls.length, 0);
    assert.match(await page.locator('#message').innerText(), /지난 4주 리포트 PDF 저장 화면/);
    console.log('PASS report PDF export opens print flow for the selected screen without backend relabeling');
    await page.keyboard.press('Escape');
    assert.ok(await page.locator('#report-pdf-options').isHidden());
    assert.equal(await page.locator('#download-report').getAttribute('aria-expanded'), 'false');
    console.log('PASS PDF period choices open as a compact popup and close with Escape');
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
    assert.equal(overflow, false);
    assert.deepEqual(errors, []);
    console.log('PASS report period controls fit 380px without browser errors');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
