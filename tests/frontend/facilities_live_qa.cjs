// One synthetic local account and a public test location. Never reads .env,
// prints credentials/SDK URLs, or follows telephone links.
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME_BIN });
  try {
    const context = await browser.newContext({ viewport: { width: 380, height: 900 }, permissions: ['geolocation'], geolocation: { latitude: 37.5665, longitude: 126.9780 } });
    const page = await context.newPage();
    const credentials = { email: `facility-qa-${Date.now()}@example.com`, password: 'Qa9!' + require('node:crypto').randomBytes(8).toString('hex') };
    const signup = await page.request.post('http://127.0.0.1:8022/api/v1/auth/signup', { data: { ...credentials, terms_agreed: true } });
    assert.equal(signup.status(), 201);
    const login = await page.request.post('http://127.0.0.1:8022/api/v1/auth/login', { data: credentials });
    const auth = await login.json();
    const token = (auth.data || auth).access_token;
    assert.ok(token);
    await page.goto('http://127.0.0.1:8022/');
    await page.evaluate(token => { state.token = token; }, token);
    for (const kind of ['medical', 'emergency']) {
      await page.evaluate(async kind => {
        if (kind === 'medical') {
          showStep(6); document.querySelector('#medical-guidance-detail').hidden = false;
          await findNearbyMedicalFacilities();
        } else {
          showStep(3); document.querySelector('#eligibility-guidance').hidden = false;
          document.querySelector('#urgent-guidance-actions').hidden = false;
          await findNearbyEmergencyFacilities();
        }
      }, kind);
      assert.equal(await page.locator(`#${kind}-facility-status`).getAttribute('data-state'), 'done');
      const summary = await page.evaluate(kind => ({
        kind,
        cards: document.querySelector(`#${kind}-facility-results`).children.length,
        telephoneLinks: document.querySelectorAll(`#${kind}-facility-results a[href^="tel:"]`).length,
        externalLinksSafe: [...document.querySelectorAll(`#${kind}-facility-results a[target="_blank"]`)].every(a => a.rel.includes('noopener')),
        mapVisible: !document.querySelector(`#${kind}-facility-map`).hidden,
        markerCount: facilityMapMarkers[kind].length,
        horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1,
      }), kind);
      assert.ok(summary.cards > 0);
      assert.ok(summary.externalLinksSafe);
      assert.equal(summary.horizontalOverflow, false);
      console.log(JSON.stringify(summary));
    }
    const address = await page.evaluate(async () => {
      try { const p = await coordinatesForAddress('서울특별시 중구 세종대로 110'); return Number.isFinite(p.lat) && Number.isFinite(p.lon); }
      catch { return false; }
    });
    console.log(JSON.stringify({ addressLookupAvailable: address }));
  } finally { await browser.close(); }
})().catch(() => { console.error('FAIL live facility UI QA (sensitive error details suppressed)'); process.exitCode = 1; });
