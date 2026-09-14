// Run only against an isolated local demo server (disposable DB, no real accounts).
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:8023';
assert.ok(['localhost', '127.0.0.1'].includes(new URL(base).hostname));
assert.equal(process.env.QA_DISPOSABLE_DB, 'true', 'Explicit disposable DB acknowledgement required');
const output = process.env.QA_OUTPUT_DIR || path.resolve(__dirname, '../../../../../../tmp/challenge-v3-qa');

(async () => {
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ headless: true,
    ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}) });
  try {
    for (const width of (process.env.QA_AUTH_ONLY ? [] : [1440, 390])) {
      const page = await browser.newPage({ viewport: { width, height: 1000 } });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(base, { waitUntil: 'domcontentloaded' });
      await page.evaluate(async () => {
        state.token = 'local-demo-token'; state.capabilities.challenge = true;
        showStep(7); await loadChallenges();
      });
      assert.equal(await page.locator('.challenge-v3-card').count(), 3);
      await page.locator('#challenge-v3-difficulty').selectOption('advanced');
      await page.waitForFunction(() => !challengeV3.busy);
      await page.locator('#challenge-v3-focus').selectOption('diet');
      await page.waitForFunction(() => !challengeV3.busy);
      assert.deepEqual(await page.evaluate(() => state.challengeRecommendations.map(item => item.goal.target_minutes || item.goal.target_count)), [1, 3, 20]);
      await page.locator('#challenge-v3-focus').selectOption('activity');
      await page.waitForFunction(() => !challengeV3.busy);
      assert.deepEqual(await page.evaluate(() => state.challengeRecommendations.map(item => item.goal.target_minutes || item.goal.target_count)), [1, 2, 30]);
      for (let i = 0; i < 5; i++) {
        await page.locator('#challenge-v3-refresh').click();
        await page.waitForFunction(() => !challengeV3.busy);
        assert.equal(await page.locator('.challenge-v3-card').count(), 3);
      }
      assert.equal(await page.evaluate(() => state.cycle), null);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false);
      await page.screenshot({ path: path.join(output, `challenge-v3-${width}.png`), fullPage: true });
      assert.deepEqual(errors, []);
      console.log(`PASS ${width}px: 3 domains, preference goals, refresh, no cycle creation, no overflow or page errors`);
      await page.close();
    }
    const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base, { waitUntil: 'domcontentloaded' });
    await page.evaluate(async () => {
      const email = `v3-qa-${Date.now()}@example.com`;
      const password = 'QaFixtureOnly!123';
      await api('/auth/signup', { method: 'POST', body: JSON.stringify({ email, password, terms_agreed: true }) });
      const login = await api('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
      state.token = login.access_token;
      await api('/users/me/profile', { method: 'PATCH', body: JSON.stringify({ birthday: '1965-04-12', gender: 'FEMALE' }) });
      await api('/consents', { method: 'POST', body: JSON.stringify({ consent_item: 'health_data', version: '1.0', is_agreed: true }) });
      await api('/eligibility-checks', { method: 'POST', body: JSON.stringify({ birth_date: '1965-04-12', has_diabetes_diagnosis: false, has_urgent_warning_sign: false, population_in_scope: true }) });
      state.capabilities.challenge = true;
      showStep(7); await loadChallenges();
      const cycle = await api('/challenge-cycles', { method: 'POST', body: JSON.stringify({
        start_date: challengeDay(), challenge_ids: [...state.selectedChallengeIds],
        catalog_version: 'evidence-v3', focus: challengeV3.focus, difficulty: challengeV3.difficulty,
      }) });
      renderCycle(cycle); showStep(8); showWorkspace('challenge', { moveFocus: false }); await loadDailyRecords();
      openPhotoRecordModal(cycle.user_challenges.find(item => item.domain === 'fiber_diet'));
    });
    if (!await page.locator('#v3-photo-fields').isVisible()) {
      console.log(await page.evaluate(() => {
        const ancestors = []; let element = document.querySelector('#v3-photo-fields');
        while (element) { ancestors.push([element.tagName, element.id, element.className, element.hidden, getComputedStyle(element).display]); element = element.parentElement; }
        return { ancestors, recordDomain: state.recordTarget?.item?.domain, recordVersion: state.recordTarget?.item?.catalog_version, step: state.step };
      }));
    }
    assert.ok(await page.locator('#v3-photo-fields').isVisible());
    assert.equal(await page.locator('.record-fallback:visible').count(), 0);
    const synthetic = await page.screenshot({ clip: { x: 0, y: 0, width: 20, height: 20 } });
    await page.locator('#v3-photo-file').setInputFiles({ name: 'synthetic-qa.png', mimeType: 'image/png', buffer: synthetic });
    await page.locator('#v3-photo-value').fill('1');
    await page.locator('#confirm-photo-record').click();
    await page.waitForFunction(() => state.recordTarget?.saved === true);
    assert.equal(await page.evaluate(() => state.dailyCompleted.size), 1);
    await page.evaluate(async () => { closeRecordModal(); await loadDailyRecords(); });
    assert.equal(await page.evaluate(() => state.dailyCompleted.size), 1);
    await page.evaluate(() => openSimpleRecordModal(state.cycle.user_challenges.find(item => item.domain === 'hydration')));
    await page.locator('#confirm-simple-record').click();
    await page.waitForFunction(() => state.dailyCompleted.size === 2);
    await page.evaluate(async () => { await loadDailyRecords(); });
    assert.equal(await page.evaluate(() => state.dailyCompleted.size), 2);
    assert.deepEqual(errors, []);
    console.log('PASS real authenticated UI -> multipart type2 proof + hydration check -> persisted daily reload (isolated DB only)');
    await page.close();
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
