// Controlled browser responses only: no real accounts, health records, or model jobs are created.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const base = process.env.QA_BASE_URL || 'http://127.0.0.1:8022';
assert.ok(['localhost', '127.0.0.1'].includes(new URL(base).hostname));
const envelope = data => ({ contentType: 'application/json', body: JSON.stringify({ data }) });

function authenticatedFixtures(route, { predictionExpired = false, reauthenticated = false } = {}) {
  const request = route.request();
  const endpoint = new URL(request.url()).pathname.replace('/api/v1', '');
  const method = request.method();
  if (endpoint === '/auth/login') return route.fulfill(envelope({ access_token: 'fresh-session-token' }));
  if (endpoint === '/users/me') return route.fulfill(envelope({ id: 7, email: 'resume@example.com', birthday: '1966-04-12', gender: 'FEMALE' }));
  if (endpoint === '/consents') return route.fulfill(envelope({ items: [{ consent_item: 'health_data', version: '1.0', is_agreed: true, withdrawn_at: null }] }));
  if (endpoint === '/eligibility-checks/latest') return route.fulfill(envelope({
    age: 60, model_eligible: true, current_health_check_eligible: true,
    future_prediction_eligible: false, challenge_eligible: true, reason_codes: [],
  }));
  if (endpoint === '/health-checkups' && method === 'GET') return route.fulfill(envelope({ items: [{
    checkup_id: 777, height_cm: 170, weight_kg: 70, waist_cm: null,
    current_drinker: false, regular_exercise: false, meal_count_yesterday: 3,
  }] }));
  if (endpoint === '/prediction-jobs' && method === 'POST' && predictionExpired && !reauthenticated) {
    return route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: { error_code: 'UNAUTHENTICATED', message: '로그인이 만료되었습니다.' } }) });
  }
  if (endpoint === '/prediction-jobs' && method === 'POST') return route.fulfill(envelope({ job_id: 9102, status: 'queued' }));
  if (endpoint === '/prediction-jobs/9102') return route.fulfill(envelope({ job_id: 9102, status: 'succeeded', prediction_id: 9202 }));
  if (endpoint === '/predictions/9202') return route.fulfill(envelope({
    prediction_id: 9202, model_key: 'diabetes_current_screening',
    result_status: 'not_approved', promotion_status: 'not_approved', display_allowed: false,
  }));
  return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'QA fixture not found' }) });
}

(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}) });
  try {
    const draftPage = await browser.newPage({ viewport: { width: 380, height: 844 } });
    await draftPage.route('**/api/v1/**', route => authenticatedFixtures(route));
    await draftPage.goto(base, { waitUntil: 'domcontentloaded' });
    await draftPage.evaluate(() => {
      state.token = 'expired-session-token';
      state.userProfile = { id: 7, email: 'resume@example.com' };
      state.capabilities.currentHealth = true;
      showStep(4);
    });
    await draftPage.locator('#height').fill('181');
    await draftPage.locator('#weight').fill('83');
    await draftPage.locator('#to-lifestyle-input').click();
    await draftPage.locator('#self-health').selectOption('good');
    const storedDraft = await draftPage.evaluate(() => sessionStorage.getItem('gandang-health-draft-v1'));
    assert.ok(storedDraft);
    assert.doesNotMatch(storedDraft, /password|token|email/i);
    await draftPage.reload({ waitUntil: 'domcontentloaded' });
    await draftPage.locator('#sidebar-login').click();
    await draftPage.locator('#login-email').fill('resume@example.com');
    await draftPage.locator('#login-password').fill('Example123!');
    await draftPage.locator('#login-form button[type="submit"]').click();
    await draftPage.locator('.screen[data-step="4"].active').waitFor();
    assert.equal(await draftPage.locator('#height').inputValue(), '181');
    assert.equal(await draftPage.locator('#weight').inputValue(), '83');
    assert.equal(await draftPage.locator('#self-health').inputValue(), 'good');
    assert.match(await draftPage.locator('#message').innerText(), /복원/);
    assert.ok(await draftPage.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    console.log('PASS unsaved health draft survives reload and resumes after same-user login');
    await draftPage.close();

    const sessionPage = await browser.newPage({ viewport: { width: 380, height: 844 } });
    let reauthenticated = false;
    await sessionPage.route('**/api/v1/**', route => authenticatedFixtures(route, { predictionExpired: true, reauthenticated }));
    await sessionPage.goto(base, { waitUntil: 'domcontentloaded' });
    await sessionPage.evaluate(() => {
      state.token = 'expired-session-token';
      state.userProfile = { id: 7, email: 'resume@example.com' };
      state.checkupId = 777;
      state.healthCheckupResult = { checkup_id: 777 };
      state.currentHealthOnly = true;
      state.capabilities.currentHealth = true;
      state.healthConsentStatus = 'active';
      showStep(5);
    });
    await sessionPage.evaluate(() => runPrediction());
    await sessionPage.locator('#login-form').waitFor({ state: 'visible' });
    assert.equal(await sessionPage.evaluate(() => state.token), null);
    assert.equal(await sessionPage.locator('#login-email').inputValue(), 'resume@example.com');
    assert.match(await sessionPage.locator('#login-form .auth-error-summary').innerText(), /만료/);
    reauthenticated = true;
    await sessionPage.locator('#login-password').fill('Example123!');
    await sessionPage.locator('#login-form button[type="submit"]').click();
    await sessionPage.locator('.screen[data-step="5"].active').waitFor();
    assert.equal(await sessionPage.locator('#retry-analysis').isEnabled(), true);
    assert.match(await sessionPage.locator('#message').innerText(), /로그인이 복구/);
    await sessionPage.locator('#retry-analysis').click();
    await sessionPage.locator('.screen[data-step="6"].active').waitFor();
    assert.equal(await sessionPage.evaluate(() => state.checkupId), 777);
    assert.equal(await sessionPage.evaluate(() => sessionStorage.getItem('gandang-session-recovery-v1')), null);
    console.log('PASS expired analysis session reauthenticates and retries the same saved checkup');
    await sessionPage.close();
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
