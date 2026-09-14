// Controlled requests only. No account, password log, or credential file access.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME_BIN });
  try {
    for (const width of [1440, 380]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      let calls = 0;
      await page.route('**/api/v1/**', route => {
        calls++;
        return route.fulfill({ status: 422, contentType: 'application/json', body: JSON.stringify({ detail: [{ loc: ['body', 'password'], type: 'value_error', msg: 'controlled password validation' }] }) });
      });
      await page.goto('http://127.0.0.1:8022/');
      await page.locator('#sidebar-signup').click();
      await page.locator('#email').fill('validation-qa@example.com');
      await page.locator('#signup-birth-date').fill('1966-04-12');
      await page.locator('#personal-consent').check();
      await page.locator('#health-consent').check();
      const before = calls;
      for (const [value, text] of [['abcdef12!', '대문자'], ['ABCDEF12!', '소문자'], ['Abcdefgh!', '숫자'], ['Abcdef123', '특수문자']]) {
        await page.locator('#password').fill(value);
        await page.locator('#signup-form button[type="submit"]').click();
        assert.match(await page.locator('#password-error').innerText(), new RegExp(text));
        assert.equal(await page.locator('#password').getAttribute('aria-invalid'), 'true');
        assert.equal(await page.evaluate(() => document.activeElement.id), 'password');
        assert.equal(calls, before);
      }
      await page.locator('#password').fill('ValidQa123!');
      assert.ok(await page.locator('#password-error').isHidden());
      await page.locator('#signup-form button[type="submit"]').click();
      await page.waitForFunction(() => !document.querySelector('#signup-form .auth-error-summary').hidden);
      assert.equal(calls, before + 1);
      assert.equal(await page.evaluate(() => document.activeElement.id), 'password');
      assert.match(await page.locator('#password-error').innerText(), /서버/);
      await page.locator('#font-toggle').click();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false);
      console.log(`PASS ${width}px: individual password hints, no invalid request, clearing, server fallback, focus and large text`);
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(() => { console.error('FAIL signup validation browser QA'); process.exitCode = 1; });
