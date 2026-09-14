// Local audit only. One synthetic account; no model jobs, health records, or calls to 119.
const assert = require('node:assert/strict');
const { chromium, request } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = 'http://127.0.0.1:8022';
const report = { live: {}, ui: [], failures: [] };
async function check(name, run) {
  try { await run(); report.ui.push(name); }
  catch (e) { report.failures.push({ name, error: e.message }); }
}
(async () => {
  const client = await request.newContext({ baseURL: base, timeout: 15000 });
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME_BIN });
  try {
    const schema = await (await client.get('/api/openapi.json')).json();
    report.live.aiJobsRoute = Boolean(schema.paths['/api/v1/ai-jobs']);
    const credentials = { email: `qa-map-${Date.now()}@example.com`, password: `Qa-${require('node:crypto').randomBytes(12).toString('hex')}!9` };
    const signup = await client.post('/api/v1/auth/signup', { data: { ...credentials, terms_agreed: true } });
    assert.equal(signup.status(), 201);
    const login = await client.post('/api/v1/auth/login', { data: credentials });
    const loginBody = await login.json();
    const token = (loginBody.data || loginBody).access_token;
    assert.ok(token);
    const headers = { Authorization: `Bearer ${token}` };
    for (const kind of ['medical', 'emergency']) {
      const r = await client.get(`/api/v1/${kind}-facilities/nearby?lat=37.5665&lon=126.9780&radius=5000`, { headers });
      const body = await r.json(); const data = body.data || body;
      // Never print upstream error text: service URLs can contain credentials.
      report.live[kind] = { status: r.status(), provider: data.provider_kind, source: data.data_source, count: data.facilities?.length };
    }
    const ragReplies = [];
    for (const question of ['걷기 운동은 어떻게 시작하나요?', '우주선 색깔은?', '약 복용을 중단해도 되나요?']) {
      const r = await client.post('/api/v1/health-education/questions', { headers, data: { question } });
      const body = await r.json(); const data = body.data || body;
      ragReplies.push(data);
      report.live[`rag-${ragReplies.length}`] = { status: r.status(), answerStatus: data.answer_status, citationCount: data.citations?.length, method: data.retrieval_method, hasNotice: Boolean(data.medical_notice) };
    }
    for (const width of [1440, 380]) {
      const page = await browser.newPage({ viewport: { width, height: 1000 } });
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      let reply = {}, responseStatus = 200, calls = 0;
      await page.route('**/api/v1/**', route => { calls++; return route.fulfill({ status: responseStatus, contentType: 'application/json', body: JSON.stringify(responseStatus === 200 ? { data: reply } : { detail: { error_code: 'UPSTREAM_UNAVAILABLE', message: 'QA upstream failure', retryable: true } }) }); });
      await page.goto(base, { waitUntil: 'domcontentloaded' });
      // Component-level fixture setup; no private location or user session is read.
      await page.evaluate(() => { state.token = 'qa-controlled'; showStep(6); document.querySelector('#medical-guidance-detail').hidden = false; });
      for (const kind of ['medical', 'emergency']) {
        if (kind === 'emergency') await page.evaluate(() => { showStep(3); document.querySelector('#eligibility-guidance').hidden = false; document.querySelector('#urgent-guidance-actions').hidden = false; });
        for (const geoCode of [1, 3]) await check(`${width} ${kind} location error ${geoCode}`, async () => {
          const before = calls;
          await page.evaluate(async ({ kind, geoCode }) => {
            Object.defineProperty(navigator, 'geolocation', { configurable: true, value: { getCurrentPosition: (_ok, fail) => fail({ code: geoCode }) } });
            state.lastKnownLocation = null;
            if (kind === 'medical') await findNearbyMedicalFacilities(); else await findNearbyEmergencyFacilities();
          }, { kind, geoCode });
          assert.equal(await page.locator(`#${kind}-facility-status`).getAttribute('data-state'), geoCode === 1 ? 'permission' : 'timeout');
          assert.equal(calls, before);
          if (kind === 'emergency') assert.ok(await page.locator('#urgent-guidance-actions a[href="tel:119"]').isVisible());
        });
        for (const scenario of ['success', 'empty', 'failed', 'sample']) await check(`${width} ${kind} ${scenario}`, async () => {
          responseStatus = scenario === 'failed' ? 503 : 200;
          reply = { provider_kind: kind === 'medical' ? 'kakao_local_api' : 'nemc_emergency_api', facilities: scenario === 'success' ? [{ name: 'QA 기관', address: '가상 주소', distance_meters: 320, phone: '02-000-0000', map_url: 'https://example.com/map' }] : [] };
          if (scenario === 'sample') reply = { provider_kind: 'development', data_source: 'development_mock', facilities: [{ name: 'QA 샘플', phone: '02-000-0000', map_url: 'https://example.com/sample' }] };
          await page.evaluate(async kind => {
            // Exclude third-party map SDK availability from API/list-state checks.
            renderFacilityMap = async () => {};
            if (kind === 'medical') await requestMedicalFacilities({ lat: 37.5665, lon: 126.9780 }, document.querySelector('#find-nearby-medical-facilities'));
            else await requestEmergencyFacilities({ lat: 37.5665, lon: 126.9780 }, document.querySelector('#find-nearby-emergency'));
          }, kind);
          assert.equal(await page.locator(`#${kind}-facility-status`).getAttribute('data-state'), scenario === 'success' ? 'done' : scenario);
          if (scenario === 'sample') {
            assert.ok(await page.locator(`#${kind}-facility-results`).isHidden());
            assert.equal(await page.locator(`#${kind}-facility-results a`).count(), 0);
          }
          if (kind === 'emergency') assert.ok(await page.locator('#urgent-guidance-actions a[href="tel:119"]').isVisible());
        });
      }
      await page.evaluate(() => { document.querySelector('#eligibility-guidance').hidden = true; state.capabilities.challenge = true; showStep(8); showWorkspace('tools'); let n=document.querySelector('#rag-form'); while(n){ if(n.tagName==='DETAILS') n.open=true; n=n.parentElement; } });
      for (let i=0; i<ragReplies.length; i++) await check(`${width} live RAG reply ${i+1} rendered`, async () => {
        responseStatus = 200; reply = ragReplies[i];
        await page.locator('#rag-question').fill('QA 화면 확인');
        await page.locator('#rag-form button').click();
        await page.waitForFunction(() => document.querySelector('#rag-result').dataset.state !== 'loading');
        assert.equal(await page.locator('#rag-result').getAttribute('data-state'), ['done', 'insufficient', 'refused'][i]);
        assert.equal(await page.locator('#rag-result a').count(), reply.citations.length);
      });
      await check(`${width} RAG failure/retry retains question`, async () => {
        responseStatus=503;
        await page.locator('#rag-question').fill('걷기 운동');
        await page.locator('#rag-form button').click();
        await page.waitForFunction(() => document.querySelector('#rag-result').dataset.state === 'failed');
        assert.equal(await page.locator('#rag-question').inputValue(), '걷기 운동');
        assert.ok(await page.locator('#rag-form button').isEnabled());
        responseStatus=200; reply=ragReplies[0];
        await page.locator('#rag-form button').click();
        await page.waitForFunction(() => document.querySelector('#rag-result').dataset.state === 'done');
      });
      await check(`${width} RAG empty response is not success`, async () => {
        responseStatus=200; reply={};
        await page.locator('#rag-form button').click();
        await page.waitForFunction(() => document.querySelector('#rag-result').dataset.state !== 'loading');
        assert.notEqual(await page.locator('#rag-result').getAttribute('data-state'), 'done');
      });
      await check(`${width} no JS errors or horizontal overflow`, async () => {
        assert.deepEqual(errors, []);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      });
      await page.close();
    }
    console.log(JSON.stringify(report, null, 2));
    if (report.failures.length) process.exitCode = 1;
  } finally { await browser.close(); await client.dispose(); }
})().catch(e => { console.error(e.message); process.exitCode=1; });
