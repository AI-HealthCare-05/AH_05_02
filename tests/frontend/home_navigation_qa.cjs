const assert = require('node:assert/strict');
const { mkdirSync } = require('node:fs');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:8022';
assert.ok(['localhost', '127.0.0.1'].includes(new URL(base).hostname));
(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}) });
  mkdirSync('tmp/ui-ux-qa', { recursive: true });
  try {
    for (const width of [1440, 768, 380]) {
      const page = await browser.newPage({ viewport: { width, height: 1000 } });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(base, { waitUntil: 'domcontentloaded' });
      assert.ok(await page.locator('#header-my-page').isHidden());
      await page.evaluate(() => {
        state.token = 'local-demo-token'; state.capabilities.challenge = true;
        state.userProfile = { birthday: '1966-04-12', gender: 'FEMALE' };
        showStep(8); showWorkspace('home');
      });
      await page.locator('#header-my-page-toggle').click();
      await page.locator('#profile-edit').click();
      assert.equal(await page.locator('#profile-birthday').inputValue(), '1966-04-12');
      assert.ok(await page.locator('#profile-gender').isVisible());
      await page.locator('#profile-editor-cancel').click();
      assert.equal(await page.evaluate(() => document.activeElement.id), 'header-my-page-toggle');
      await page.locator('.profile-menu > summary').click();
      assert.equal(await page.locator('.profile-menu-panel button').count(), 1);
      assert.ok(await page.locator('#profile-notification-settings').isVisible());
      await page.locator('.profile-menu > summary').click();
      const cards = page.locator('.home-feature-card');
      assert.equal(await cards.count(), 4);
      const boxes = await cards.evaluateAll(nodes => nodes.map(n => ({ y: n.getBoundingClientRect().y, width: n.getBoundingClientRect().width })));
      if (width === 1440) assert.equal(new Set(boxes.map(b => Math.round(b.y))).size, 1);
      if (width === 768) assert.equal(new Set(boxes.map(b => Math.round(b.y))).size, 2);
      if (width === 380) assert.equal(new Set(boxes.map(b => Math.round(b.y))).size, 4);
      assert.ok(await cards.locator('img').evaluateAll(nodes => nodes.every(n => n.complete && n.naturalWidth > 0)));
      await page.screenshot({ path: `tmp/ui-ux-qa/home-navigation-${width}.png`, fullPage: true });
      for (const target of ['report', 'together', 'tools']) {
        await page.locator(`.home-feature-card[data-workspace="${target}"]`).click();
        assert.ok(await page.locator(`#workspace-panel-${target}`).isVisible());
        await page.evaluate(() => showWorkspace('home'));
      }
      await page.evaluate(() => document.querySelector('#home-health-management').open = false);
      await page.locator('#open-health-management').click();
      assert.ok(await page.locator('#home-health-management').getAttribute('open') !== null);
      await page.locator('#today-record-action').click();
      assert.equal(await page.getByRole('heading', { name: '챌린지 기록', exact: true }).count(), 1);
      await page.evaluate(() => showWorkspace('home'));
      await page.locator('#font-toggle').click();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false);
      assert.deepEqual(errors, []);
      console.log(`PASS ${width}px: profile menu, notification isolation, four shortcuts, single record heading, large text without overflow`);
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
