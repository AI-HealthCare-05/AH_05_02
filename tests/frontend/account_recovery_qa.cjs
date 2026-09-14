// Controlled local HTTP responses: no real accounts or consent records are created.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:8022';
assert.ok(['localhost', '127.0.0.1'].includes(new URL(base).hostname));
const dir = path.resolve('tmp/ui-ux-qa');
fs.mkdirSync(dir, { recursive: true });
(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}) });
  const checks = [];
  try {
    for (const scenario of ['profile', 'consent', 'lost-consent-response', 'login', 'reload', 'expired', 'read-failure']) {
      const page = await browser.newPage({ viewport: { width: 380, height: 844 } });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      const calls = [];
      let profile = {};
      let consent = false;
      let failed = false;
      let loginCount = 0;
      await page.route('**/api/v1/**', async route => {
        const endpoint = new URL(route.request().url()).pathname.replace('/api/v1', '');
        const method = route.request().method();
        calls.push(`${method} ${endpoint}`);
        const ok = data => route.fulfill({ contentType: 'application/json', body: JSON.stringify({ data }) });
        const fail = status => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify({ detail: 'Controlled QA failure' }) });
        if (endpoint === '/auth/signup') {
          assert.equal(route.request().postDataJSON().terms_agreed, true);
          return ok({ user_id: 1 });
        }
        if (endpoint === '/auth/login') {
          loginCount++;
          if (scenario === 'login' && loginCount === 1) return fail(503);
          return ok({ access_token: 'controlled-qa-session' });
        }
        if (endpoint === '/users/me/profile') {
          if (!failed && ['profile', 'reload', 'expired'].includes(scenario)) { failed = true; return fail(scenario === 'expired' ? 401 : 503); }
          profile = route.request().postDataJSON();
          return ok(profile);
        }
        if (endpoint === '/users/me') {
          if (scenario === 'read-failure' && !failed) { failed = true; return fail(503); }
          return ok(profile);
        }
        if (endpoint === '/consents' && method === 'GET') return ok({ items: consent
          ? [{ consent_item: 'health_data', version: '1.0', is_agreed: true, withdrawn_at: null }]
          : [{ consent_item: 'analytics', version: '1.0', is_agreed: true }] });
        if (endpoint === '/consents' && method === 'POST') {
          assert.equal(route.request().postDataJSON().is_agreed, true);
          if (!failed && ['consent', 'lost-consent-response'].includes(scenario)) {
            failed = true;
            consent = scenario === 'lost-consent-response';
            return fail(503);
          }
          consent = true;
          return ok({ consent_id: 1 });
        }
        if (endpoint === '/health-checkups') return ok({ items: [] });
        return fail(404);
      });
      const login = async () => {
        await page.locator('#login-email').fill('recovery-qa@example.com');
        await page.locator('#login-password').fill('Example123!');
        await page.locator('#login-form button[type="submit"]').click();
      };
      await page.goto(base, { waitUntil: 'domcontentloaded' });
      if (scenario === 'read-failure') {
        await page.locator('#sidebar-login').click();
        await login();
      } else {
        await page.locator('#sidebar-signup').click();
        await page.locator('#email').fill('recovery-qa@example.com');
        await page.locator('#password').fill('Example123!');
        await page.locator('#signup-birth-date').fill('1974-04-12');
        await page.locator('#personal-consent').check();
        await page.locator('#health-consent').check();
        await page.locator('#signup-form button[type="submit"]').click();
      }
      await page.locator('#account-recovery-form').waitFor({ state: 'visible' });
      assert.ok(await page.locator('#signup-form').isHidden());
      await page.waitForFunction(() => document.activeElement.id === 'account-recovery-message');
      if (scenario === 'reload') {
        await page.reload();
        await page.locator('#sidebar-login').click();
        await login();
        await page.locator('#account-recovery-form').waitFor();
      }
      if (['login', 'expired'].includes(scenario)) {
        assert.ok(await page.locator('#recovery-submit').isHidden());
        await page.locator('#recovery-login').click();
        await login();
        await page.locator('#account-recovery-form').waitFor();
      }
      if (scenario === 'read-failure') {
        assert.equal(await page.locator('#recovery-submit').innerText(), '저장 상태 다시 확인하기');
        await page.locator('#recovery-submit').click();
        await page.locator('#recovery-birthday').waitFor({ state: 'visible' });
        await page.waitForFunction(() => !document.querySelector('#recovery-birthday').disabled);
      }
      if (!(await page.locator('#recovery-birthday').isDisabled())) {
        await page.locator('#recovery-birthday').fill('1974-04-12');
        await page.locator('#recovery-gender').selectOption('FEMALE');
      }
      // Unchecked consent is never silently granted, nor does it send any write.
      await page.locator('#recovery-health-consent').uncheck();
      const before = calls.length;
      await page.locator('#recovery-submit').click();
      await page.waitForFunction(() => document.activeElement.id === 'recovery-health-consent');
      assert.equal(calls.length, before);
      await page.locator('#recovery-health-consent').check();
      const dimensions = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth }));
      assert.ok(dimensions.scroll <= dimensions.width + 1);
      if (scenario === 'consent') {
        await page.evaluate(() => showStep(4));
        assert.equal(await page.evaluate(() => state.step), 2);
        assert.ok(await page.locator('#onboarding-top-nav').isHidden());
        await page.locator('#recovery-health-consent').check();
        await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
        await page.screenshot({ path: path.join(dir, 'account-recovery-mobile.png'), fullPage: true });
      }
      await page.locator('#recovery-submit').click();
      await page.locator('.screen[data-step="3"].active').waitFor();
      assert.equal(calls.filter(call => call === 'POST /auth/signup').length, scenario === 'read-failure' ? 0 : 1);
      if (['consent', 'lost-consent-response'].includes(scenario)) assert.equal(calls.filter(call => call === 'PATCH /users/me/profile').length, 1);
      if (scenario === 'lost-consent-response') assert.equal(calls.filter(call => call === 'POST /consents').length, 1);
      assert.equal(consent, true);
      assert.deepEqual(errors, []);
      checks.push(scenario);
      console.log(`PASS account recovery: ${scenario}`);
      await page.close();
    }
    fs.writeFileSync(path.join(dir, 'account-recovery-results.json'), JSON.stringify({ controlledResponseTests: checks }, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
