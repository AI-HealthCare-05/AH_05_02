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
      challenge_details: [{ title: '걷기', completed: 6, planned: 7 }],
    } }) }));
    await page.route('**/api/v1/weekly-reports/current/pdf*', route => {
      pdfCalls.push(route.request().url());
      return route.fulfill({ status: 503, contentType: 'application/json', body: '{}' });
    });
    await page.goto(base, { waitUntil: 'domcontentloaded' });
    await page.evaluate(async () => { state.token = 'qa-session'; showStep(8); showWorkspace('report', { moveFocus: false }); await loadWeeklyReport(); });
    assert.equal(await page.locator('#report-week-period').innerText(), '9/1~9/7');
    await page.evaluate(() => { state.dailyCompleted = new Set(['1']); updateDailyRecordSummary(); });
    assert.equal(await page.locator('#report-week-streak').innerText(), '최근 7일 기록 6회');
    console.log('PASS weekly totals are not replaced by today-only records');
    await page.locator('#report-period-all').click();
    assert.equal(await page.locator('#report-period-all').getAttribute('aria-selected'), 'true');
    assert.match(await page.locator('#report-panel-all').innerText(), /조회하지 않았/);
    await page.locator('#download-report').click();
    assert.ok(await page.locator('#download-report').isDisabled());
    assert.match(await page.locator('#report-pdf-status').innerText(), /연결 준비/);
    await page.locator('#report-pdf-options label').filter({ hasText: '지난 4주' }).click();
    assert.ok(await page.locator('#download-report').isDisabled());
    assert.equal(pdfCalls.length, 0);
    console.log('PASS unsupported PDF periods display preparation state and send no request');
    await page.locator('#report-pdf-options label').filter({ hasText: '이번 주' }).click();
    assert.ok(await page.locator('#download-report').isEnabled());
    await page.locator('#download-report').click();
    await page.waitForFunction(() => !document.querySelector('#download-report').disabled);
    assert.equal(pdfCalls.length, 1);
    assert.ok(pdfCalls[0].endsWith('/weekly-reports/current/pdf'));
    assert.match(await page.locator('#message').innerText(), /PDF를 만들지 못/);
    console.log('PASS supported weekly PDF failure is actionable and button recovers');
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
    assert.equal(overflow, false);
    assert.deepEqual(errors, []);
    console.log('PASS report period controls fit 380px without browser errors');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
