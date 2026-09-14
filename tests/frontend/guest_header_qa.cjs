// Read-only local browser QA: no account creation, API writes, or model calls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:8022';
assert.ok(['localhost', '127.0.0.1'].includes(new URL(base).hostname));
(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}) });
  try {
    const page = await browser.newPage({ reducedMotion: 'reduce' });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    fs.mkdirSync('tmp/guest-header-qa', { recursive: true });
    for (const width of [1440, 1024, 760, 380, 320]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(base, { waitUntil: 'domcontentloaded' });
      const geometry = await page.evaluate(() => {
        const rect = selector => { const r = document.querySelector(selector).getBoundingClientRect(); return { x: r.x, right: r.right, y: r.y, height: r.height }; };
        return { login: rect('#sidebar-login'), signup: rect('#sidebar-signup'), logo: rect('#brand-home'), font: rect('#font-toggle'), width: innerWidth, scroll: document.documentElement.scrollWidth };
      });
      assert.ok(geometry.scroll <= width + 1, `overflow at ${width}`);
      assert.ok(geometry.login.right <= geometry.signup.x + 1, 'login before signup, no overlap');
      assert.ok(geometry.signup.right <= width, 'signup is inside viewport');
      assert.ok(geometry.signup.x > width / 2, `signup is right-aligned at ${width}`);
      assert.ok(geometry.login.height >= 48 && geometry.signup.height >= 48);
      if (width > 760) {
        assert.ok(geometry.login.x > width / 2, 'desktop auth group is right-aligned');
        assert.ok(Math.abs(geometry.login.y - geometry.font.y) < 10, 'same desktop header row');
      }
      if ([1440, 380].includes(width)) await page.locator('.topbar').screenshot({ path: `tmp/guest-header-qa/header-${width}.png` });
      await page.locator('#sidebar-login').click();
      assert.ok(await page.locator('#login-form').isVisible());
      await page.locator('#sidebar-signup').click();
      assert.ok(await page.locator('#signup-form').isVisible());
      await page.locator('#font-toggle').click();
      assert.ok(await page.locator('body').evaluate(el => el.classList.contains('large-text')));
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      console.log(`PASS ${width}px: right-aligned auth, 48px targets, working forms, large text, no overflow`);
    }
    await page.evaluate(() => { state.token = 'header-qa-only'; state.checkupId = 1; showStep(8); });
    assert.ok(await page.locator('#guest-flow-panel').isHidden());
    assert.ok(await page.locator('#workspace-top-nav').isVisible());
    assert.equal(await page.locator('#workspace-top-nav button').count(), 5);
    assert.deepEqual(errors, []);
    console.log('PASS signed-in five-tab navigation preserved; no JavaScript errors');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
