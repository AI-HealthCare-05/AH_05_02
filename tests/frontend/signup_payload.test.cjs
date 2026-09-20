// Execute the actual signup submit handler; capture its serialized API request.
// No browser, server, real account, or network connection is needed.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../src/frontend/app.js'), 'utf8');
const handlerSource = source.match(/^\$\("#signup-form"\)\.addEventListener\("submit", async \(event\) => \{[\s\S]*?^\}\);/m);
assert.ok(handlerSource, 'Signup submit handler must exist');
const passwordValidationSource = source.match(/^function signupPasswordIssues\(value\) \{[\s\S]*?(?=^function showAuthError)/m);
assert.ok(passwordValidationSource, 'Password validation helpers must exist');

for (const checked of [true, false]) {
  test(`signup JSON terms_agreed follows checkbox: ${checked}`, async () => {
    const stopAfterCapture = new Error('Stop before any real account creation');
    let handler, request, released = false;
    const nodes = {
      '#signup-form': {
        getAttribute: () => null,
        addEventListener: (name, callback) => { assert.equal(name, 'submit'); handler = callback; },
      },
      '#eligibility-guidance': { hidden: false },
      '#email': { value: 'payload-fixture@example.com' },
      '#signup-nickname': { value: '테스트집주인' },
      '#password': { value: 'FixtureOnly123!', removeAttribute() {}, setAttribute() {} },
      '#password-error': { hidden: true, textContent: '' },
      '#signup-birth-date': { value: '1966-04-12' },
      '#signup-gender': { value: 'FEMALE' },
      '#personal-consent': { checked },
      '#health-consent': { checked: true },
    };
    const context = vm.createContext({
      $: selector => { assert.ok(nodes[selector], `Unexpected selector ${selector}`); return nodes[selector]; },
      state: {}, getAgeFromBirth: () => 60,
      setFormBusy: () => () => { released = true; },
      api: async (endpoint, options) => { request = { endpoint, method: options.method, body: JSON.parse(options.body) }; throw stopAfterCapture; },
      isUnderMinimumBirthdayError: () => false,
      showAuthError: (_form, error) => assert.equal(error, stopAfterCapture),
    });
    vm.runInContext(passwordValidationSource[0] + handlerSource[0], context);
    await handler({ preventDefault() {}, currentTarget: nodes['#signup-form'], submitter: {} });
    assert.ok(request, 'Signup must issue a request');
    assert.equal(request.endpoint, '/auth/signup');
    assert.equal(request.method, 'POST');
    assert.deepEqual(request.body, {
      email: nodes['#email'].value, password: nodes['#password'].value,
      birth_date: nodes['#signup-birth-date'].value, gender: nodes['#signup-gender'].value,
      terms_agreed: checked,
    });
    assert.equal(released, true);
  });
}
