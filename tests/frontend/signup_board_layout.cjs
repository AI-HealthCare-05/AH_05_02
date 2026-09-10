// Read-only browser check; does not register accounts or submit health data.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: true,
  });
  try {
    for (const [width, height] of [[3066, 1662], [1440, 1000], [390, 844]]) {
      const page = await browser.newPage({ viewport: { width, height } });
      await page.goto(`${process.env.PREVIEW_URL || 'http://127.0.0.1:8023'}/?auth=signup`);
      await page.locator('#signup-form').waitFor({ state: 'visible' });
      const layout = await page.evaluate(() => {
        const rect = document.querySelector('.signup-house-board').getBoundingClientRect();
        return { width: rect.width, left: rect.left, right: rect.right, overflow: document.documentElement.scrollWidth > innerWidth };
      });
      assert.equal(layout.overflow, false);
      assert.ok(layout.left >= 0 && layout.right <= width);
      if (width === 3066) assert.equal(layout.width, 1360);
      await page.goto(`${process.env.PREVIEW_URL || 'http://127.0.0.1:8023'}/?auth=login`);
      await page.locator('#login-form').waitFor({ state: 'visible' });
      const login = await page.locator('.signup-house-board').boundingBox();
      assert.ok(login.x>=0 && login.x+login.width<=width);
      if(width>=1000)assert.equal(login.width,layout.width,'login and signup should share desktop width');
      if(width===3066){
        assert.equal(login.width,1360);
        await page.screenshot({path:'/tmp/login-board-large.png',fullPage:true});
      }
      await page.locator('#login-password').fill('LayoutCheckOnly!123');
      await page.locator('[data-password-target="login-password"]').click();
      assert.equal(await page.locator('#login-password').getAttribute('type'),'text');
      await page.locator('[data-password-target="login-password"]').click();
      assert.equal(await page.locator('#login-password').getAttribute('type'),'password');
      await page.goto(`${process.env.PREVIEW_URL || 'http://127.0.0.1:8023'}/?preview=eligibility-forest`);
      await page.locator('#eligibility-form').waitFor({ state: 'visible' });
      const eligibility = await page.locator('.eligibility-forest-board').boundingBox();
      assert.ok(eligibility.x >= 0 && eligibility.x + eligibility.width <= width);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      if (width === 3066) {
        assert.ok(eligibility.width > 1300);
        assert.ok(eligibility.x + eligibility.width < width / 2);
        assert.ok(eligibility.height >= height - 240);
        await page.screenshot({path: '/tmp/eligibility-large-desktop.png', fullPage: true});
      }
      await page.locator('#diagnosed-diabetes-no').check();
      assert.equal(await page.locator('#diagnosed-diabetes-no').isChecked(), true);
      await page.locator('#open-emergency-questionnaire').click();
      await page.locator('#emergency-questionnaire-modal').waitFor({state: 'visible'});
      await page.close();
    }
    console.log('Signup, login and eligibility: responsive sizes, password visibility and safety dialog passed.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
