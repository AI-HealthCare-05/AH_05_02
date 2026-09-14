// Creates one synthetic local account; does not create health records or run models.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = 'http://127.0.0.1:8022';
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME_BIN });
  const email = `qa-db-recovery-${Date.now()}@example.com`;
  const password = `Qa-${require('node:crypto').randomBytes(16).toString('hex')}!9`;
  const responses = [];
  try {
    const page = await browser.newPage();
    page.on('response', r => {
      const u = new URL(r.url());
      if (u.pathname.startsWith('/api/')) responses.push({ path: u.pathname, status: r.status() });
    });
    await page.goto(base, { waitUntil: 'domcontentloaded' });
    assert.equal((await page.request.get(`${base}/api/health`)).status(), 200);
    await page.locator('#sidebar-signup').click();
    await page.locator('#email').fill(email);
    await page.locator('#password').fill(password);
    await page.locator('#signup-birth-date').fill('1966-04-12');
    await page.locator('#personal-consent').check();
    await page.locator('#health-consent').check();
    await page.locator('#signup-form button[type="submit"]').click();
    await page.locator('.screen[data-step="3"].active').waitFor({ timeout: 20000 });
    assert.ok(responses.some(r => r.path === '/api/v1/auth/signup' && r.status === 201));
    assert.ok(responses.some(r => r.path === '/api/v1/users/me/profile' && r.status < 300));
    assert.ok(responses.some(r => r.path === '/api/v1/consents' && r.status === 201));
    const fresh = await browser.newPage();
    await fresh.goto(base, { waitUntil: 'domcontentloaded' });
    await fresh.locator('#sidebar-login').click();
    await fresh.locator('#login-email').fill(email);
    await fresh.locator('#login-password').fill(password);
    await fresh.locator('#login-form button[type="submit"]').click();
    await fresh.locator('.screen[data-step="3"].active').waitFor({ timeout: 20000 });
    console.log('PASS: health 200; signup -> auto login -> profile/consent -> eligibility; fresh-page login -> eligibility');
    console.log(JSON.stringify(responses));
  } catch (error) {
    console.error('FAIL:', error.message);
    console.error(JSON.stringify(responses));
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
