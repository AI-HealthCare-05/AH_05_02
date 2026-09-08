// Explicit local E2E smoke. Creates ONE synthetic QA account in the local database.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:8022';
assert.ok(['localhost', '127.0.0.1'].includes(new URL(base).hostname));
const dir = path.resolve('tmp/ui-ux-qa');
fs.mkdirSync(dir, { recursive: true });
(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  let activePage = page;
  page.setDefaultTimeout(10000);
  const report = { scope: 'Real local HTTP calls; UI flow verification does not establish model approval or accuracy', stages: [], responses: [], errors: [] };
  const mark = name => { report.stages.push(name); console.log(`PASS ${name}`); };
  const email = `uiqa-${Date.now()}@example.com`;
  const password = 'LocalQa123!';
  page.on('response', async response => {
    const url = new URL(response.url());
    if (url.pathname.startsWith('/api/v1/')) report.responses.push({ path: url.pathname, status: response.status() });
    if (/\/prediction-jobs\/.+/.test(url.pathname) && response.ok()) {
      const body = await response.json().catch(() => ({}));
      const data = body.data || body;
      report.lastJobStatus = ['queued', 'running', 'succeeded', 'failed'].includes(data.status) ? data.status : 'unknown';
    }
  });
  page.on('pageerror', error => report.errors.push(error.message));
  try {
    await page.goto(base, { waitUntil: 'domcontentloaded' });
    await page.locator('#sidebar-signup').click();
    await page.locator('#email').fill(email);
    await page.locator('#password').fill(password);
    await page.locator('#signup-birth-date').fill('1966-04-12');
    await page.locator('#personal-consent').check();
    await page.locator('#health-consent').check();
    await page.locator('#signup-form button[type="submit"]').click();
    await page.locator('.screen[data-step="3"].active').waitFor();
    mark('signup -> automatic login -> profile/consent -> eligibility');
    // Verify returning account without health records using a fresh page, no shared app state.
    const returning = await browser.newPage();
    await returning.goto(base, { waitUntil: 'domcontentloaded' });
    await returning.locator('#sidebar-login').click();
    await returning.locator('#login-email').fill(email);
    await returning.locator('#login-password').fill(password);
    await returning.locator('#login-form button[type="submit"]').click();
    await returning.locator('.screen[data-step="3"].active').waitFor({ timeout: 10000 });
    mark('login without health history -> eligibility, not empty dashboard');
    await returning.close();
    await page.locator('label').filter({ has: page.locator('input[name="urgent-warning"][value="no"]') }).click();
    await page.locator('label').filter({ has: page.locator('input[name="diabetes-diagnosis"][value="no"]') }).click();
    await page.locator('#eligibility-form button[type="submit"]').click();
    await page.locator('.screen[data-step="4"].active').waitFor();
    mark('eligible adult -> health input');
    await page.locator('#height').fill('170');
    await page.locator('#weight').fill('70');
    await page.locator('#to-lifestyle-input').click();
    await page.setViewportSize({ width: 380, height: 844 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    await page.screenshot({ path: path.join(dir, 'lifestyle-mobile.png'), fullPage: true });
    await page.locator('#to-detail-input').click();
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    await page.locator('[data-health-tab="review"]').click();
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.screenshot({ path: path.join(dir, 'input-review-desktop.png'), fullPage: true });
    mark('basic -> lifestyle -> detail -> review; 380px input pages fit');
    await page.locator('#submit-analysis').click();
    await page.waitForFunction(() => state.step === 6 || (state.step === 5 && !document.querySelector('#retry-analysis').hidden), null, { timeout: 45000 });
    if (await page.evaluate(() => state.step) !== 6) throw new Error('Analysis did not succeed; retry state visible');
    report.models = await page.evaluate(() => Object.entries(state.analysisRun.models).map(([key, result]) => ({
      key, status: result.status, model_version: result.prediction?.model_version,
      display_allowed: result.prediction?.display_allowed,
      operational_model_activated: result.prediction?.operational_model_activated,
    })));
    assert.equal(report.models.length, 2);
    assert.ok(report.models.every(model => model.status === 'succeeded'));
    assert.ok(report.models.every(model => model.operational_model_activated !== true));
    mark('health save -> analysis -> result');
    await page.screenshot({ path: path.join(dir, 'result-desktop.png'), fullPage: true });
    await page.locator('#to-challenges').click();
    if (await page.locator('#medical-guidance-detail').isVisible()) {
      assert.ok(await page.locator('#medical-to-challenges').isVisible());
      mark('high signal -> medical guidance before challenge (no location permission required)');
      await page.locator('#medical-to-challenges').click();
    }
    await page.locator('.screen[data-step="7"].active').waitFor();
    if (await page.locator('#acknowledge-challenge-follow-up').isVisible()) {
      await page.locator('#acknowledge-challenge-follow-up').click();
      await page.locator('#challenge-follow-up').waitFor({ state: 'hidden' });
      mark('server follow-up acknowledgement retained');
    }
    await page.locator('[data-challenge-category="activity"]').click();
    await page.locator('.challenge-detail-option').first().click();
    await page.locator('#start-challenge').click();
    await page.locator('.screen[data-step="8"].active').waitFor();
    mark('result -> challenge selection -> cycle creation -> dashboard');
    await page.screenshot({ path: path.join(dir, 'dashboard-desktop.png'), fullPage: true });
    const saved = await browser.newPage();
    activePage = saved;
    saved.on('response', response => { const url = new URL(response.url()); if (url.pathname.startsWith('/api/v1/')) report.responses.push({ path: url.pathname, status: response.status() }); });
    saved.on('pageerror', error => report.errors.push(error.message));
    await saved.goto(base, { waitUntil: 'domcontentloaded' });
    await saved.locator('#sidebar-login').click();
    await saved.locator('#login-email').fill(email);
    await saved.locator('#login-password').fill(password);
    await saved.locator('#login-form button[type="submit"]').click();
    await saved.locator('.screen[data-step="8"].active').waitFor({ timeout: 10000 });
    mark('login with saved health history -> dashboard');
    await saved.locator('#today-record-action').click();
    await saved.locator('.daily-record-open').first().click();
    await saved.locator('#confirm-simple-record').click();
    await saved.locator('.daily-record-card.done').waitFor();
    mark('daily record saved through actual API');
    await saved.reload({ waitUntil: 'domcontentloaded' });
    await saved.locator('#sidebar-login').click();
    await saved.locator('#login-email').fill(email);
    await saved.locator('#login-password').fill(password);
    await saved.locator('#login-form button[type="submit"]').click();
    await saved.locator('.screen[data-step="8"].active').waitFor();
    await saved.locator('#today-record-action').click();
    const logRoute = /\/api\/v1\/user-challenges\/\d+\/logs\?/;
    await saved.route(logRoute, route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'QA-only temporary failure' }) }));
    await saved.evaluate(() => loadDailyRecords());
    assert.equal(await saved.locator('.daily-record-open').count(), 0);
    await saved.locator('.daily-record-retry').waitFor();
    await saved.unroute(logRoute);
    await saved.locator('.daily-record-retry').click();
    await saved.locator('.daily-record-card.done').waitFor();
    mark('controlled daily read failure -> retry -> actual saved completion restored');
    const restoredDailyCount = await saved.locator('.daily-record-card.done').count();
    await saved.locator('[data-top-workspace="home"]').click();
    await saved.locator('#open-health-management').click();
    await saved.locator('#dashboard-edit-health').click();
    const editHeight = await saved.locator('#height').inputValue();
    const editWeight = await saved.locator('#weight').inputValue();
    assert.deepEqual({ restoredDailyCount, editHeight, editWeight }, { restoredDailyCount: 1, editHeight: '170', editWeight: '70' });
    mark('reload/login restores daily completion and saved health values');
    const beforeId = await saved.evaluate(() => state.checkupId);
    await saved.locator('#weight').fill('72');
    await saved.locator('[data-health-tab="review"]').click();
    await saved.locator('#submit-analysis').click();
    await saved.waitForFunction(() => state.step === 6 || (state.step === 5 && !document.querySelector('#retry-analysis').hidden), null, { timeout: 45000 });
    assert.equal(await saved.evaluate(() => state.step), 6);
    const history = await saved.evaluate(() => state.healthCheckupHistory.map(item => ({ id: item.checkup_id, type: item.checkup_type, weight: item.weight_kg })));
    assert.equal(history.length, 2);
    assert.notEqual(history[0].id, beforeId);
    assert.equal(history[0].type, 'reassessment');
    assert.equal(history[0].weight, 72);
    assert.equal(history[1].weight, 70);
    mark('health edit -> reanalysis -> new history, original record preserved');
    assert.equal(await saved.locator('#risk-forecast-panel').count(), 0);
    assert.ok(!report.responses.some(response => response.path.includes('/research/models/')));
    const reportToken = await saved.evaluate(() => state.token);
    const pdf = await saved.request.get(`${base}/api/v1/weekly-reports/current/pdf`, { headers: { Authorization: `Bearer ${reportToken}` } });
    report.pdf = { status: pdf.status(), contentType: pdf.headers()['content-type'] };
    if (pdf.ok() && report.pdf.contentType?.includes('application/pdf')) {
      const pdfDir = path.resolve('tmp/pdfs');
      fs.mkdirSync(pdfDir, { recursive: true });
      fs.writeFileSync(path.join(pdfDir, 'weekly-report-live-20260907.pdf'), await pdf.body());
      mark('actual weekly PDF downloaded for visual review');
    } else console.log(`PDF_PENDING HTTP ${pdf.status()}`);
    await saved.close();
    assert.deepEqual(report.errors, []);
  } catch (error) {
    report.blocker = error.message;
    report.screen = await activePage.locator('.screen.active').innerText().catch(() => 'unavailable');
    await activePage.screenshot({ path: path.join(dir, 'flow-blocker.png'), fullPage: true });
    console.error(`BLOCKED ${error.message}`);
    process.exitCode = 1;
  } finally {
    fs.writeFileSync(path.join(dir, 'live-flow.json'), JSON.stringify(report, null, 2));
    await browser.close();
  }
})();
