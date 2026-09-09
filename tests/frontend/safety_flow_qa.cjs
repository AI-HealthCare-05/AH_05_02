// Controlled API responses only: never creates users or changes backend records.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:8022';
assert.ok(['127.0.0.1', 'localhost'].includes(new URL(base).hostname));
(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}) });
  try {
    for (const scenario of ['underage', 'consent', 'urgent', 'same-day', 'diagnosed', 'model-age']) {
      const page = await browser.newPage({ viewport: { width: 380, height: 844 } });
      const requests = [], errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.route('**/api/v1/**', route => {
        const url = new URL(route.request().url());
        requests.push({ path: url.pathname, method: route.request().method() });
        let data = {};
        if (url.pathname.endsWith('/eligibility-checks')) data = {
          age: scenario === 'model-age' ? 35 : 60, model_eligible: false,
          challenge_eligible: scenario === 'model-age',
          current_health_check_eligible: scenario === 'model-age', future_prediction_eligible: false,
          reason_codes: [scenario === 'diagnosed' ? 'DIAGNOSED_DIABETES' : 'MODEL_AGE_OUT_OF_RANGE'],
        };
        return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ data }) });
      });
      await page.goto(base, { waitUntil: 'domcontentloaded' });
      if (['underage', 'consent'].includes(scenario)) {
        await page.locator('#sidebar-signup').click();
        await page.locator('#signup-nickname').fill('안전집주인');
        await page.locator('#email').fill('safety-fixture@example.com');
        await page.locator('#password').fill('LocalQa123!');
        await page.locator('#signup-birth-date').fill(scenario === 'underage' ? '2020-01-01' : '1966-04-12');
        await page.locator('#personal-consent').check();
        if (scenario === 'underage') await page.locator('#health-consent').check();
        await page.locator('#signup-form button[type="submit"]').click();
      } else {
        await page.evaluate(() => { state.token = 'fixture-only'; showStep(3); });
        await page.locator('#eligibility-birth-date').fill(scenario === 'model-age' ? '1991-04-12' : '1966-04-12');
        await page.locator('label').filter({ has: page.locator(`input[name="urgent-warning"][value="${scenario === 'urgent' ? 'yes' : 'no'}"]`) }).click();
        await page.locator('label').filter({ has: page.locator(`input[name="diabetes-diagnosis"][value="${scenario === 'diagnosed' ? 'yes' : 'no'}"]`) }).click();
        if (scenario === 'same-day') await page.evaluate(() => { document.querySelector('input[name="same-day-summary"][value="yes"]').checked = true; });
        await page.locator('#eligibility-form button[type="submit"]').click();
      }
      const panel = page.locator('#eligibility-guidance');
      await panel.waitFor({ state: 'visible' });
      const expected = { underage: /14세 미만/, consent: /동의가 필요/, urgent: /즉시 도움/, 'same-day': /오늘 의료기관/, diagnosed: /이미 당뇨병/, 'model-age': /현재 건강 신호/ };
      assert.match(await page.locator('#eligibility-guidance-title').innerText(), expected[scenario]);
      assert.equal(await page.evaluate(() => document.activeElement.id), 'eligibility-guidance');
      assert.ok(!requests.some(item => /auth\/signup|health-checkups|prediction-jobs|challenge-cycles/.test(item.path)));
      if (['urgent', 'same-day'].includes(scenario)) assert.equal(await panel.locator('a[href="tel:119"]:visible').count(), 1);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      await page.keyboard.press('Shift+Tab');
      assert.ok(await page.evaluate(() => document.querySelector('#eligibility-guidance').contains(document.activeElement)));
      await page.keyboard.press('Tab');
      assert.ok(await page.evaluate(() => document.activeElement === safetyDialogControls(document.querySelector('#eligibility-guidance'))[0]));
      await page.keyboard.press('Shift+Tab');
      assert.ok(await page.evaluate(() => document.activeElement === safetyDialogControls(document.querySelector('#eligibility-guidance')).at(-1)));
      await page.keyboard.press('Escape');
      assert.ok(await panel.isHidden());
      assert.ok(await page.evaluate(() => document.activeElement.getClientRects().length > 0));
      if (['underage', 'consent'].includes(scenario)) {
        await page.waitForFunction(id => document.activeElement.id === id, scenario === 'underage' ? 'signup-birth-date' : 'health-consent');
      }
      assert.deepEqual(errors, []);
      console.log(`PASS ${scenario}: guidance, focus entry, 380px, no prediction/save/start request, close`);
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
