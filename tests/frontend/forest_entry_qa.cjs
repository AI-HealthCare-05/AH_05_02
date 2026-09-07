const assert = require('node:assert/strict');
const { mkdirSync } = require('node:fs');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:8022';
assert.ok(['localhost', '127.0.0.1'].includes(new URL(base).hostname));
(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}) });
  mkdirSync('tmp/ui-ux-qa', { recursive: true });
  try {
    for (const width of [1440, 380]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      await page.goto(base, { waitUntil: 'domcontentloaded' });
      await page.evaluate(() => { state.token = 'local-demo-token'; state.capabilities.challenge = true; showStep(8); showWorkspace('together'); });
      const link = page.getByRole('link', { name: '당근의 숲 게임 열기', exact: true });
      const img = link.locator('img');
      await img.evaluate(node => node.decode());
      assert.ok(await img.evaluate(n => Math.abs(n.clientWidth / n.clientHeight - n.naturalWidth / n.naturalHeight) < 0.02));
      assert.equal(await page.getByRole('link', { name: '숲 꾸미러 가기', exact: true }).count(), 0);
      assert.equal(await page.getByRole('link', { name: '아바타 꾸미기', exact: true }).count(), 0);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false);
      await link.screenshot({ path: `tmp/ui-ux-qa/forest-entry-${width}.png` });
      if (width === 1440) { await link.focus(); await page.keyboard.press('Enter'); }
      else await img.click();
      await page.waitForURL('**/forest');
      assert.equal((await page.request.get(`${base}/forest`)).status(), 200);
      console.log(`PASS ${width}px: full image without cropping, obsolete links removed, ${width === 1440 ? 'keyboard' : 'image click'} opens /forest`);
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
