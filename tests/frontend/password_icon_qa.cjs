const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:8022';
assert.ok(['localhost', '127.0.0.1'].includes(new URL(base).hostname));
(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}) });
  try {
    for (const width of [1440, 380]) {
      for (const mode of ['login', 'signup']) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      await page.goto(base, { waitUntil: 'domcontentloaded' });
      await page.evaluate(mode => { showStep(2); showAuthMode(mode); }, mode);
      const target = mode === 'login' ? 'login-password' : 'password';
      const input = page.locator(`#${target}`);
      const toggle = page.locator(`[data-password-target="${target}"]`);
      await input.fill('Example-only-123!');
      assert.equal(await toggle.innerText(), '');
      assert.ok(await toggle.locator('.eye-open').isVisible());
      await toggle.click();
      assert.equal(await input.getAttribute('type'), 'text');
      assert.equal(await toggle.getAttribute('aria-label'), '비밀번호 숨기기');
      assert.ok(await toggle.locator('.eye-closed').isVisible());
      await toggle.focus();
      await page.keyboard.press('Space');
      assert.equal(await input.getAttribute('type'), 'password');
      assert.equal(await toggle.getAttribute('aria-label'), '비밀번호 보기');
      assert.equal(await input.inputValue(), 'Example-only-123!');
      await page.locator('#font-toggle').click();
      const box = await toggle.boundingBox();
      const field = await input.boundingBox();
      assert.ok(box.width >= 44 && box.height >= 44);
      assert.ok(box.x >= field.x && box.x + box.width <= field.x + field.width);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false);
      console.log(`PASS ${mode} ${width}px: eye icons, click/keyboard toggle, accessible labels, large-text layout`);
      await page.close();
      }
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
