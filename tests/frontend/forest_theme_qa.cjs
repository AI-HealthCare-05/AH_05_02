// Isolated UI fixtures: no real accounts, model requests or database writes.
// PLAYWRIGHT_MODULE and CHROME_BIN may point to existing local installations.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve('src/frontend');
const artifacts = path.resolve('tmp/forest-theme-qa');
const mime = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml' };
const server = http.createServer((req, res) => {
  const pathname = new URL(req.url, 'http://localhost').pathname;
  const file = path.resolve(root, pathname === '/' ? 'index.html' : pathname.replace(/^\/static\//, ''));
  if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
    res.writeHead(404); res.end(); return;
  }
  res.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
});
(async () => {
  fs.mkdirSync(artifacts, { recursive: true });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    const base = `http://127.0.0.1:${server.address().port}`;
    browser = await chromium.launch({ headless: true, ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}) });
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    page.setDefaultTimeout(6000);
    const errors = [], missing = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('response', response => {
      if (response.url().includes('/static/') && response.status() >= 400) missing.push(response.url());
    });
    await page.route('**/*', route => {
      const url = new URL(route.request().url());
      if (url.origin !== base) return route.abort();
      if (url.pathname.startsWith('/api/')) return route.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":"UI fixture: backend unavailable"}' });
      return route.continue();
    });
    await page.goto(base);
    await page.waitForURL('**/static/intro-retro.html?*');
    await page.locator('#sidebar-signup').click();
    await page.waitForURL('**/?auth=signup*');
    await page.locator('#signup-nickname').fill('우리집주인');
    assert.equal(await page.locator('#signup-nickname').inputValue(), '우리집주인');
    assert.equal(await page.locator('#signup-title').innerText(), '새로운 집주인을 등록해요');
    console.log('PASS intro -> themed signup, nickname input');

    for (const width of [1440, 380]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.goto(base + '/?preview=health-room');
      await page.locator('#height').fill('173');
      const panels = ['health-metrics-panel', 'health-vitals-panel', 'lifestyle-input-panel', 'health-habits-panel', 'health-activity-panel', 'detail-health-panel', 'health-nutrition-panel', 'health-socioeconomic-panel'];
      assert.equal(await page.locator('[data-health-tab]').count(), 8);
      for (let i = 0; i < panels.length; i++) {
        const panel = page.locator('#' + panels[i]);
        await panel.waitFor({ state: 'visible' });
        const size = await page.evaluate(() => ({ viewport: innerWidth, content: document.documentElement.scrollWidth }));
        assert.ok(size.content <= size.viewport + 1, `${panels[i]} overflow: ${JSON.stringify(size)}`);
        await panel.locator('.actions button.primary').click();
      }
      await page.locator('#health-review-panel').waitFor({ state: 'visible' });
      assert.match(await page.locator('#review-health').innerText(), /173 cm/);
      assert.equal(await page.locator('#submit-analysis').innerText(), '분석하기');
      await page.screenshot({ path: path.join(artifacts, `review-${width}.png`), fullPage: true });
      console.log(`PASS ${width}px: eight input steps -> review preserves height`);
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
    const statusSizes = [];
    for (const status of ['queued', 'running', 'succeeded', 'failed']) {
      await page.goto(base + '/?preview=analysis-status&status=' + status);
      await page.locator('.screen[data-step="5"].active').waitFor();
      statusSizes.push(await page.locator('#prediction-status-card').boundingBox());
    }
    assert.ok(statusSizes.every(size => size && Math.abs(size.width - statusSizes[0].width) < 1 && Math.abs(size.height - statusSizes[0].height) < 1), JSON.stringify(statusSizes));
    console.log('PASS analysis states keep the same card dimensions');
    for (const preview of ['results', 'challenge-forest', 'challenge-record', 'report-forest', 'dashboard-home', 'health-tools']) {
      await page.goto(base + '/?preview=' + preview);
      await page.locator('.screen.active').waitFor();
      await page.screenshot({ path: path.join(artifacts, `${preview}.png`), fullPage: true });
    }
    assert.deepEqual(missing, [], 'Local assets must exist');
    assert.deepEqual(errors, [], 'No browser JavaScript errors');
    console.log('PASS result/challenge/report/home/tools previews and asset loading');
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
