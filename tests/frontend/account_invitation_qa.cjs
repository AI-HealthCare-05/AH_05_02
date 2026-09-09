const assert = require('node:assert/strict');
const { mkdirSync } = require('node:fs');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:8022';

assert.ok(['localhost', '127.0.0.1'].includes(new URL(base).hostname));

(async () => {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}),
  });
  try {
    mkdirSync('tmp/account-invitation-qa', { recursive: true });
    const page = await browser.newPage({ viewport: { width: 980, height: 900 } });
    const calls = { created: 0, accepted: 0, logout: 0, deleted: 0 };
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));

    await page.route('**/api/v1/invitations', async route => {
      if (route.request().method() === 'GET') {
        return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ data: {
          sent: [],
          received: [{ invitation_id: 7, invitee_email: 'family@example.com', relation_type: 'family', status: 'pending', expires_at: '2026-09-15T00:00:00Z' }],
        } }) });
      }
      calls.created += 1;
      assert.deepEqual(await route.request().postDataJSON(), { invitee_email: 'new-family@example.com', relation_type: 'family' });
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ data: {
        invitation_id: 8,
        invitee_email: 'new-family@example.com',
        relation_type: 'family',
        token: 'backend-issued-invitation-code-123456',
        expires_at: '2026-09-15T00:00:00Z',
        sharing_scope: ['challenge_status'],
      } }) });
    });
    await page.route('**/api/v1/invitations/accept', async route => {
      calls.accepted += 1;
      assert.equal((await route.request().postDataJSON()).token, '12345678901234567890');
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ data: { connection_id: 4, relation_type: 'family', sharing_scope: ['challenge_status'] } }) });
    });
    await page.route('**/api/v1/connections', route => route.fulfill({ contentType: 'application/json', body: JSON.stringify({ data: { items: [] } }) }));
    await page.route('**/api/v1/auth/logout', route => {
      calls.logout += 1;
      return route.fulfill({ status: 204, body: '' });
    });
    await page.route('**/api/v1/users/me', route => {
      if (route.request().method() === 'DELETE') {
        calls.deleted += 1;
        return route.fulfill({ status: 204, body: '' });
      }
      return route.continue();
    });

    await page.goto(base, { waitUntil: 'domcontentloaded' });
    await page.evaluate(async () => {
      state.token = 'qa-session';
      state.userProfile = { id: 4, email: 'family@example.com' };
      showStep(8, { recordHistory: false });
      showWorkspace('together', { moveFocus: false });
      await loadInvitations();
    });
    assert.equal(await page.locator('.forest-invite-summary').count(), 2);
    assert.equal(await page.locator('#received-invite-panel').isHidden(), true);
    assert.equal(await page.locator('#create-invite-panel').isHidden(), true);
    await page.locator('#open-create-invite').click();
    assert.equal(await page.locator('#create-invite-panel').isVisible(), true);
    assert.equal(await page.locator('#received-invite-panel').isHidden(), true);
    assert.equal(await page.locator('#open-create-invite').getAttribute('aria-expanded'), 'true');
    await page.locator('#invite-email').fill('new-family@example.com');
    await page.locator('#invite-form button[type="submit"]').click();
    await page.waitForFunction(() => document.querySelector('#forest-invite-code')?.textContent.includes('backend-issued'));
    assert.equal(calls.created, 1);
    assert.equal(await page.locator('#invite-panel-code').isVisible(), true);
    assert.equal(await page.locator('#forest-invite-code').innerText(), 'backend-issued-invitation-code-123456');
    assert.equal(await page.locator('#copy-invite-code').isEnabled(), true);
    assert.equal(await page.locator('#invite-result').isVisible(), false);
    console.log('PASS backend invitation token is shown in the existing invitation code panel');

    await page.locator('#open-received-invites').click();
    assert.equal(await page.locator('#received-invite-panel').isVisible(), true);
    assert.equal(await page.locator('#create-invite-panel').isHidden(), true);
    assert.equal(await page.locator('#open-received-invites').getAttribute('aria-expanded'), 'true');
    assert.equal(await page.locator('#open-create-invite').getAttribute('aria-expanded'), 'false');
    assert.match(await page.locator('#received-invitation-list').innerText(), /가족 초대/);
    await page.screenshot({ path: 'tmp/account-invitation-qa/received-open.png', fullPage: true });
    await page.locator('#invitation-token').fill('12345678901234567890');
    await page.locator('#accept-invitation-form button[type="submit"]').click();
    await page.waitForFunction(() => document.querySelector('#message').textContent.includes('초대를 수락'));
    assert.equal(calls.accepted, 1);
    console.log('PASS received invitations load and token acceptance are connected');

    await page.locator('#header-my-page-toggle').click();
    await page.locator('#account-logout').click();
    await page.waitForFunction(() => document.querySelector('.screen.active')?.dataset.step === '2');
    assert.equal(calls.logout, 1);
    assert.equal(await page.evaluate(() => state.token), null);
    console.log('PASS logout calls the API and clears the local session');

    await page.evaluate(() => {
      state.token = 'qa-session-2';
      state.userProfile = { id: 5, email: 'delete@example.com' };
      showStep(8, { recordHistory: false });
    });
    await page.locator('#header-my-page-toggle').click();
    await page.locator('#open-account-delete').click();
    assert.ok(await page.locator('#confirm-account-delete').isDisabled());
    await page.locator('#account-delete-confirm').fill('탈퇴');
    assert.ok(await page.locator('#confirm-account-delete').isEnabled());
    await page.locator('#confirm-account-delete').click();
    await page.waitForFunction(() => document.querySelector('.screen.active')?.dataset.step === '2');
    assert.equal(calls.deleted, 1);
    assert.equal(await page.evaluate(() => state.token), null);
    assert.deepEqual(errors, []);
    console.log('PASS account deletion requires explicit confirmation and clears the session');
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
