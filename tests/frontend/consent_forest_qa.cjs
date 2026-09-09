const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const base = process.env.QA_BASE_URL || 'http://127.0.0.1:8022';
assert.ok(['localhost', '127.0.0.1'].includes(new URL(base).hostname));

const envelope = data => ({ contentType: 'application/json', body: JSON.stringify({ data }) });
const forestHome = {
  forest_space_id: 3, group_id: 7, name: '우리 당근의 숲',
  today: { completed: 1, target: 3, group_reward_ready: false, group_reward_claimed: false },
  me: { display_name: '수인', hair_code: 'midnight_short', outfit_code: 'garden_overall', accessory_code: 'none', carrot_balance: 100 },
  members: [{ user_id: 42, display_name: '수인', today_completed: 1, today_target: 3, avatar: {} }],
  inventory: [], objects: [], sharing_scope: ['challenge_status', 'avatar', 'forest_objects'],
  privacy_notice: '건강정보와 예측 결과는 공유하지 않습니다.',
};

(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}) });
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    const calls = [];
    let consentActive = true;
    await page.route('**/api/v1/**', async route => {
      const request = route.request();
      const path = new URL(request.url()).pathname.replace('/api/v1', '');
      calls.push(`${request.method()} ${path}`);
      if (path === '/consents' && request.method() === 'GET') return route.fulfill(envelope({ items: [{ consent_id: consentActive ? 11 : 10, consent_item: 'health_data', version: '1.0', is_agreed: consentActive, withdrawn_at: consentActive ? null : '2026-09-08T01:00:00Z' }] }));
      if (path === '/consents/11/withdraw') { consentActive = false; return route.fulfill(envelope({ consent_id: 11, is_agreed: false, withdrawn_at: '2026-09-08T01:00:00Z' })); }
      if (path === '/consents' && request.method() === 'POST') { consentActive = true; return route.fulfill({ status: 201, ...envelope({ consent_id: 12, consent_item: 'health_data', version: '1.0', is_agreed: true }) }); }
      if (path === '/eligibility-checks/latest') return route.fulfill(envelope({ age: 52, challenge_eligible: true, current_health_check_eligible: true, future_prediction_eligible: true, reason_codes: [] }));
      if (path === '/shared-challenge-groups') return route.fulfill(envelope({ items: [{ group_id: 7, title: '가족 숲', common_goal: '하루 한 번 기록', status: 'active', members: [{ user_id: 42, is_me: true, status: 'active', completed_days: 1 }] }] }));
      if (path === '/forest/spaces/7') return route.fulfill(envelope(forestHome));
      if (path === '/forest/catalog') return route.fulfill(envelope({ hair: [], outfits: [], accessories: [], objects: [{ code: 'bench', name: '나무 벤치', cost: 35 }] }));
      if (path === '/wallet') return route.fulfill(envelope({ carrot_balance: 100 }));
      if (path === '/inventory-items') return route.fulfill(envelope({ items: [{ item_id: 1, code: 'sprout_hat', name: '새싹 모자', category: 'hat', price_carrots: 0 }] }));
      if (path === '/inventory') return route.fulfill(envelope({ items: [] }));
      if (path === '/avatar') return route.fulfill(envelope({ equipped_item_ids: [], version: 1 }));
      if (path === '/challenge-cycles/current') return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: '진행 중인 챌린지가 없습니다.' }) });
      return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: `unmocked ${path}` }) });
    });

    await page.goto(base, { waitUntil: 'domcontentloaded' });
    await page.evaluate(() => {
      state.token = 'qa-session';
      state.userProfile = { id: 42, email: 'qa@example.com' };
      state.healthConsent = { consent_id: 11 };
      state.healthConsentStatus = 'active';
      state.checkupId = 1;
      state.capabilities = { challenge: true, currentHealth: true, futurePrediction: true };
      showStep(8, { recordHistory: false });
      showWorkspace('together', { moveFocus: false });
    });

    await page.locator('#header-my-page-toggle').click();
    await page.locator('#open-privacy-settings').click();
    await page.waitForFunction(() => document.querySelector('#consent-status-card')?.dataset.status === 'active');
    page.once('dialog', dialog => dialog.accept());
    await page.locator('#withdraw-health-consent').click();
    await page.waitForFunction(() => document.querySelector('#consent-status-card')?.dataset.status === 'withdrawn');
    assert.equal(await page.evaluate(() => state.capabilities.challenge), false);
    await page.locator('#renew-health-consent').click();
    await page.waitForFunction(() => document.querySelector('#consent-status-card')?.dataset.status === 'active');
    assert.ok(calls.includes('PATCH /consents/11/withdraw'));
    assert.ok(calls.includes('POST /consents'));

    await page.locator('#cancel-consent-settings').click();
    await page.locator('#open-forest-game').click();
    await page.locator('input[name="forest-entry-group"][value="7"]').check();
    await Promise.all([page.waitForURL('**/forest'), page.locator('#enter-forest-game').click()]);
    await page.waitForFunction(() => document.documentElement.classList.contains('forest-script-ready'));
    assert.equal(await page.locator('#forest-access-error').isHidden(), true);
    assert.equal(await page.locator('#adapter-badge').innerText(), 'Live API');
    assert.equal(await page.evaluate(() => localStorage.getItem('gandang-carrot-forest-demo-v1')), null);
    const beforeRefresh = calls.filter(call => call === 'GET /forest/spaces/7').length;
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.documentElement.classList.contains('forest-script-ready'));
    assert.ok(calls.filter(call => call === 'GET /forest/spaces/7').length > beforeRefresh);

    const restoredContext = await browser.newContext();
    await restoredContext.addInitScript(session => {
      sessionStorage.setItem('gandang-forest-api-session-v1', JSON.stringify(session));
    }, { version: 1, token: 'second-device-session', userId: 42, groupId: 7, createdAt: Date.now(), expiresAt: Date.now() + 60_000 });
    await restoredContext.route('**/api/v1/**', route => {
      const path = new URL(route.request().url()).pathname.replace('/api/v1', '');
      if (path === '/forest/spaces/7') return route.fulfill(envelope(forestHome));
      if (path === '/forest/catalog') return route.fulfill(envelope({ hair: [], outfits: [], accessories: [], objects: [{ code: 'bench', name: '나무 벤치', cost: 35 }] }));
      if (path === '/wallet') return route.fulfill(envelope({ carrot_balance: 100 }));
      if (path === '/inventory-items') return route.fulfill(envelope({ items: [] }));
      if (path === '/inventory') return route.fulfill(envelope({ items: [] }));
      if (path === '/avatar') return route.fulfill(envelope({ equipped_item_ids: [], version: 1 }));
      if (path === '/challenge-cycles/current') return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: '진행 중인 챌린지가 없습니다.' }) });
      return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'unmocked' }) });
    });
    const restoredPage = await restoredContext.newPage();
    await restoredPage.goto(`${base}/forest`, { waitUntil: 'domcontentloaded' });
    await restoredPage.waitForFunction(() => document.documentElement.classList.contains('forest-script-ready'));
    assert.equal(await restoredPage.locator('#adapter-badge').innerText(), 'Live API');
    assert.equal(await restoredPage.locator('#carrot-balance').innerText(), '100');
    await restoredContext.close();

    const expiredContext = await browser.newContext();
    await expiredContext.addInitScript(session => {
      sessionStorage.setItem('gandang-forest-api-session-v1', JSON.stringify(session));
    }, { version: 1, token: 'expired-session', userId: 42, groupId: 7, createdAt: Date.now(), expiresAt: Date.now() + 60_000 });
    await expiredContext.route('**/api/v1/**', route => route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: '로그인이 필요합니다.' }) }));
    const expiredPage = await expiredContext.newPage();
    await expiredPage.goto(`${base}/forest`, { waitUntil: 'domcontentloaded' });
    await expiredPage.waitForFunction(() => document.documentElement.classList.contains('forest-script-ready'));
    assert.match(await expiredPage.locator('#forest-access-error-copy').innerText(), /로그인 시간이 만료/);
    assert.equal(await expiredPage.evaluate(() => sessionStorage.getItem('gandang-forest-api-session-v1')), null);
    await expiredContext.close();

    const cleanContext = await browser.newContext();
    const cleanPage = await cleanContext.newPage();
    await cleanPage.goto(`${base}/forest`, { waitUntil: 'domcontentloaded' });
    await cleanPage.waitForFunction(() => document.documentElement.classList.contains('forest-script-ready'));
    assert.equal(await cleanPage.locator('#forest-access-error').isVisible(), true);
    await cleanContext.close();
    console.log('PASS consent withdrawal/re-consent, authenticated group entry, server refresh, and clean-device gate');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
