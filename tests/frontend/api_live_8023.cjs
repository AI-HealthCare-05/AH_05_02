// Live HTTP/SQLite verification, not a model-accuracy or Worker test.
// Creates one synthetic account per invocation in the isolated 8023 database.
// No network mocks, secrets, tokens, or request bodies are recorded.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const fs = require('node:fs');
const crypto = require('node:crypto');
const base = 'http://127.0.0.1:8023';
const report = { mode: 'live HTTP, embedded-demo inference', checks: [], http: [], errors: [] };
const output = '/tmp/api-live-8023.json';
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' });
  const email = `qa-api-${Date.now()}@example.com`;
  const password = `Qa-${crypto.randomBytes(16).toString('hex')}!9`;
  report.syntheticAccount = email;
  let page;
  async function newPage() {
    const p = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    p.setDefaultTimeout(12000);
    p.on('response', r => {
      const u = new URL(r.url());
      if (u.pathname.startsWith('/api/')) report.http.push({ method: r.request().method(), path: u.pathname, status: r.status() });
    });
    p.on('pageerror', e => report.errors.push(e.message));
    return p;
  }
  async function check(name, fn) {
    try { const details = await fn(); report.checks.push({ name, status: 'PASS', details }); console.log(`PASS ${name}`); return true; }
    catch (e) { report.checks.push({ name, status: 'FAIL', error: e.message }); console.log(`FAIL ${name}: ${e.message}`); return false; }
  }
  async function login(p) {
    await p.goto(`${base}/?auth=login`);
    await p.locator('#login-email').fill(email);
    await p.locator('#login-password').fill(password);
    await p.locator('#login-form button[type=submit]').click();
  }
  try {
    page = await newPage();
    const health = await (await page.request.get(`${base}/api/health`)).json();
    assert.equal(health.redis, 'embedded-demo', 'Refuse to mutate an unexpected environment');
    report.health = health;
    if (!await check('UI signup -> profile + consent -> eligibility', async () => {
      await page.goto(`${base}/?auth=signup`);
      await page.locator('#signup-nickname').fill('API검증용집');
      await page.locator('#email').fill(email);
      await page.locator('#password').fill(password);
      await page.locator('#signup-birth-date').fill('1966-04-12');
      await page.locator('#personal-consent').check();
      await page.locator('#health-consent').check();
      await page.locator('#signup-form button[type=submit]').click();
      await page.locator('.screen[data-step="3"].active').waitFor();
      assert.ok(report.http.some(r => r.path.endsWith('/auth/signup') && r.status === 201));
    })) return;
    await check('Fresh login without health -> eligibility', async () => {
      const p = await newPage();
      try { await login(p); await p.locator('.screen[data-step="3"].active').waitFor(); }
      finally { await p.close(); }
    });
    if (!await check('Eligibility API -> eight input panels -> review', async () => {
      await page.locator('#eligibility-age-band-check').selectOption('60');
      await page.locator('label').filter({ has: page.locator('input[name="urgent-warning"][value="no"]') }).click();
      await page.locator('label').filter({ has: page.locator('input[name="diabetes-diagnosis"][value="no"]') }).click();
      await page.locator('#eligibility-form button[type=submit]').click();
      await page.locator('.screen[data-step="4"].active').waitFor();
      await page.locator('#height').fill('170');
      await page.locator('#weight').fill('70');
      for (const next of ['vitals','drinking','habits','activity','family','nutrition','socioeconomic']) {
        await page.locator(`[data-next-health-panel="${next}"]`).click();
      }
      await page.locator('#health-socioeconomic-panel button[type=submit]').click();
      await page.locator('#health-review-panel').waitFor({ state: 'visible' });
      assert.match(await page.locator('#review-health').innerText(), /170/);
    })) return;
    await check('Health save -> both model HTTP jobs -> demo results', async () => {
      await page.locator('#submit-analysis').click();
      await page.waitForFunction(() => state.step === 6 || (state.step === 5 && !document.querySelector('#retry-analysis').hidden), null, { timeout: 45000 });
      const result = await page.evaluate(() => ({ step: state.step, models: Object.entries(state.analysisRun.models).map(([key,m]) => ({ key, status:m.status, error:m.error, predictionId:m.predictionId, modelVersion:m.prediction?.model_version, displayAllowed:m.prediction?.display_allowed, operational:m.prediction?.operational_model_activated })) }));
      report.analysis = result;
      assert.equal(result.step, 6);
      assert.equal(result.models.length, 2);
      assert.ok(result.models.every(m => m.status === 'succeeded'));
      assert.ok(result.models.every(m => m.operational !== true));
      return result;
    });
    await check('Results -> challenge selection -> stored cycle', async () => {
      await page.locator('#to-challenges').click();
      if (await page.locator('#medical-guidance-detail').isVisible()) await page.locator('#medical-to-challenges').click();
      await page.locator('.screen[data-step="7"].active').waitFor();
      if (await page.locator('#acknowledge-challenge-follow-up').isVisible()) await page.locator('#acknowledge-challenge-follow-up').click();
      await page.locator('.challenge-v3-card').first().waitFor();
      await page.locator('#start-challenge').click();
      await page.waitForFunction(() => state.step === 8 && state.activeWorkspace === 'challenge');
      assert.ok(report.http.some(r => r.path.endsWith('/challenge-cycles') && r.method === 'POST' && r.status < 300));
    });
    await check('Fresh login with saved health -> home and cycle restored', async () => {
      const fresh = await newPage(); await login(fresh);
      await fresh.locator('.screen[data-step="8"].active').waitFor();
      const snapshot = await fresh.evaluate(() => ({ height:state.healthCheckupResult?.height_cm, weight:state.healthCheckupResult?.weight_kg, count:state.cycle?.user_challenges?.length }));
      await page.close(); page = fresh;
      assert.equal(Number(snapshot.height), 170); assert.equal(Number(snapshot.weight), 70); assert.equal(snapshot.count, 3);
      return snapshot;
    });
    await check('Daily record UI -> HTTP save -> server reread', async () => {
      report.walletBefore = await page.evaluate(() => api('/wallet'));
      await page.locator('[data-top-step="7"]').click();
      await page.locator('.daily-record-open[data-record-type="simple"]').first().click();
      await page.locator('#confirm-simple-record').click();
      await page.locator('.daily-record-card.done').first().waitFor();
      await page.evaluate(() => loadDailyRecords());
      await page.locator('.daily-record-card.done').first().waitFor();
      assert.ok(report.http.some(r => r.method === 'PUT' && /\/logs\//.test(r.path) && r.status < 300));
      report.walletAfter = await page.evaluate(() => api('/wallet'));
    });
    // Authenticated read-only diagnostics continue even when a UI segment fails.
    const token = await page.evaluate(() => state.token);
    const paths = ['/users/me','/health-checkups','/challenge-cycles/current','/dashboard/summary','/weekly-reports/current','/reports?period=four-week','/reports?period=all','/education-contents','/health-education/quizzes','/wearables/connections','/invitations','/shared-challenge-groups','/wallet','/inventory','/forest/catalog'];
    for (const path of paths) await check(`GET ${path}`, async () => {
      const r = await page.request.get(`${base}/api/v1${path}`, { headers:{ Authorization:`Bearer ${token}` } });
      const body = await r.json().catch(() => ({}));
      const data = body.data || body;
      const details = { status:r.status(), keys:Object.keys(data), errorCode:body.error?.code || body.code, detail:typeof body.detail === 'string' ? body.detail : undefined };
      report.http.push({ method:'GET',path, status:r.status() });
      assert.ok(r.ok(), JSON.stringify(details));
      return details;
    });
    async function call(path, method = 'GET', data) {
      const r = await page.request.fetch(`${base}/api/v1${path}`, { method, headers:{ Authorization:`Bearer ${token}` }, ...(data ? { data } : {}) });
      report.http.push({ method, path, status:r.status() });
      assert.ok(r.ok(), `HTTP ${r.status()} ${method} ${path}`);
      const body = await r.json(); return body.data || body;
    }
    await check('Both XAI endpoints: explicitly unavailable, no invented factors', async () => {
      const items = [];
      for (const m of report.analysis.models) {
        const d = await call(`/predictions/${m.predictionId}/risk-factors`);
        assert.equal(d.shap_claimed, false); assert.equal(d.items.length, 0);
        items.push({ model:m.key, status:d.status, shap_claimed:d.shap_claimed, itemCount:d.items.length });
      }
      return items;
    });
    await check('RAG HTTP: source links, missing evidence, unsafe request refusal', async () => {
      const cases = [ ['걷기 운동은 어떻게 시작하나요?', 'grounded'], ['우주선 궤도 계산', 'insufficient_evidence'], ['약 용량 변경 방법', 'medical_safety_refusal'] ];
      const results = [];
      for (const [question, expected] of cases) {
        const d = await call('/health-education/questions', 'POST', { question });
        assert.equal(d.answer_status, expected);
        if (expected === 'grounded') assert.ok(d.citations?.length && d.citations.every(c => /^https:\/\//.test(c.url)));
        results.push({ status:d.answer_status, sourceCount:d.citations?.length || 0 });
      }
      return results;
    });
    await check('Wearable manual adapter: import -> reread values', async () => {
      const c = await call('/wearables/connections', 'POST', { provider:'development_mock', scopes:['activity','sleep','heart_rate'] });
      const today = new Date().toISOString().slice(0,10);
      const imported = await call('/wearables/daily-summaries/import', 'POST', { connection_id:c.connection_id, items:[{summary_date:today,steps:3500,active_minutes:15,sleep_minutes:420,resting_heart_rate:68}] });
      assert.equal(imported.imported_count, 1);
      const summaries = await call(`/wearables/daily-summaries?start_date=${today}&end_date=${today}`);
      assert.equal(summaries.items[0].steps, 3500); assert.equal(summaries.items[0].sleep_minutes, 420);
      return { mode:c.mode, imported:imported.imported_count, source:summaries.items[0].source, autoLogged:imported.auto_logged_challenges.length };
    });
    await check('Food adapter: filename classification and explicit user confirmation (not CV)', async () => {
      const d = await call('/food-analyses','POST',{ image_name:'qa-salad.jpg' });
      assert.equal(d.requires_user_confirmation, true);
      const confirmed = await call(`/food-analyses/${d.analysis_id}/confirm`,'PATCH',{ confirmed_category:'채소' });
      assert.equal(confirmed.status,'user_confirmed');
      const unknown = await call('/food-analyses','POST',{ image_name:'qa-unrelated.txt' });
      assert.equal(unknown.predicted_category, '확인불가');
      return { provider:d.provider, status:confirmed.status, unknown:unknown.predicted_category };
    });
    await check('Report tabs show real 404 and retry, not sample data', async () => {
      await page.locator('[data-top-workspace="report"]').click();
      for (const period of ['four-week','all']) {
        await page.locator(`[data-report-period="${period}"]`).click();
        const retry = page.locator(`.retry-period-report[data-period="${period}"]`);
        await retry.waitFor({state:'visible'});
        await retry.click(); await retry.waitFor({state:'visible'});
      }
    });
    await check('Fresh login restores completed daily record after reload', async () => {
      const p = await newPage();
      try { await login(p); await p.locator('.screen[data-step="8"].active').waitFor(); await p.locator('[data-top-step="7"]').click(); await p.locator('.daily-record-card.done').first().waitFor(); }
      finally { await p.close(); }
    });
    await check('Together -> personal forest navigation (detect demo boundary)', async () => {
      await page.locator('[data-top-workspace="together"]').click();
      await page.locator('#open-forest-game').click();
      await page.waitForURL('**/forest?demo=1');
      return { path:'/forest?demo=1', persistentRewardIntegration:false };
    });
    await check('No browser JavaScript exceptions', async () => assert.deepEqual(report.errors, []));
  } finally {
    if (page) {
      report.finalScreen = await page.locator('.screen.active').innerText().catch(() => 'unavailable');
      await page.screenshot({ path:'/tmp/api-live-8023-final.png', fullPage:true }).catch(() => {});
    }
    fs.writeFileSync(output, JSON.stringify(report,null,2));
    console.log(`Report: ${output}`);
    await browser.close();
    if (report.checks.some(c => c.status === 'FAIL')) process.exitCode = 1;
  }
})().catch(e => { console.error(e.message); process.exitCode=1; });
