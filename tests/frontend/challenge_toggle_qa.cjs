const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:8022';
assert.ok(['localhost', '127.0.0.1'].includes(new URL(base).hostname));
(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}) });
  try {
    for (const width of [1440, 380]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(base, { waitUntil: 'domcontentloaded' });
      await page.evaluate(async () => { state.token = 'local-demo-token'; state.capabilities.challenge = true; showStep(7); await loadChallenges(); });
      assert.ok(await page.locator('#challenge-category-panel').isHidden());
      assert.ok(await page.locator('#rag-challenge-generator').isHidden());
      for (const category of ['activity', 'diet', 'tracking']) {
        const button = page.locator(`[data-challenge-category="${category}"]`);
        await button.click();
        assert.equal(await button.getAttribute('aria-expanded'), 'true');
        await page.locator('.challenge-detail-option').first().click();
        await button.click();
        assert.ok(await page.locator('#challenge-category-panel').isHidden());
        assert.ok(await page.locator('#walking-level-picker').isHidden());
        assert.equal(await button.getAttribute('aria-expanded'), 'false');
        await button.click();
        assert.ok(await page.locator('.challenge-detail-option input').first().isChecked());
        await button.click();
      }
      assert.equal(await page.locator('#challenge-selection-count').innerText(), '3/3 선택');
      await page.locator('[data-challenge-category="activity"]').click();
      await page.locator('#open-rag-challenge').click();
      assert.ok(await page.locator('#challenge-category-panel').isHidden());
      assert.equal(await page.locator('[data-challenge-category="activity"]').getAttribute('aria-expanded'), 'false');
      await page.locator('#rag-challenge-preference').selectOption('diet');
      await page.locator('#open-rag-challenge').click();
      assert.ok(await page.locator('#rag-challenge-generator').isHidden());
      await page.locator('#open-rag-challenge').click();
      assert.equal(await page.locator('#rag-challenge-preference').inputValue(), 'diet');
      await page.locator('[data-challenge-category="tracking"]').click();
      assert.ok(await page.locator('#rag-challenge-generator').isHidden());
      assert.ok(await page.locator('#challenge-category-panel').isVisible());
      await page.locator('[data-challenge-category="tracking"]').focus();
      await page.keyboard.press('Space');
      assert.ok(await page.locator('#challenge-category-panel').isHidden());
      await page.keyboard.press('Enter');
      assert.ok(await page.locator('#challenge-category-panel').isVisible());
      // The existing custom choice keeps selection; its edit trigger also toggles.
      await page.evaluate(() => { state.customChallenge = { title: '테스트 맞춤 목표', goal: '기록', recordLabel: '간편 체크' }; state.customChallengeSelected = false; renderChallengeChoices(); });
      await page.locator('.edit-rag-challenge').click();
      assert.ok(await page.locator('#rag-challenge-generator').isVisible());
      await page.locator('.edit-rag-challenge').click();
      assert.ok(await page.locator('#rag-challenge-generator').isHidden());
      assert.equal(await page.locator('#challenge-selection-count').innerText(), '3/3 선택');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false);
      assert.deepEqual(errors, []);
      console.log(`PASS ${width}px: four category toggles, exclusive panels, retained selections and custom preference, keyboard, no overflow/errors`);
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
