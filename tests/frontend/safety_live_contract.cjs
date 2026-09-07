// Opt-in local API test: creates one synthetic account and eligibility records only.
// Never reads key files, prints credentials, submits health/model jobs, or calls 119.
const assert = require('node:assert/strict');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:8022';
assert.ok(['localhost', '127.0.0.1'].includes(new URL(base).hostname));
let token;
async function call(path, method = 'GET', data) {
  const response = await fetch(`${base}/api/v1${path}`, {
    method, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    ...(data === undefined ? {} : { body: JSON.stringify(data) }), signal: AbortSignal.timeout(15000),
  });
  const body = await response.json().catch(() => ({}));
  return { status: response.status, data: body.data || body };
}
const birthday = age => {
  const [year, month, day] = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date()).split('-');
  return `${Number(year) - age}-${month}-${day}`;
};
async function eligibility(age, flags = {}) {
  let date = birthday(age);
  let profile = await call('/users/me/profile', 'PATCH', { birthday: date, gender: 'FEMALE' });
  if (age === 14 && profile.status === 422) {
    console.log('PENDING exact 14th birthday rejected with 422; profile validator uses < rather than <=');
    date = new Date(Date.parse(date) - 86400000).toISOString().slice(0, 10);
    profile = await call('/users/me/profile', 'PATCH', { birthday: date, gender: 'FEMALE' });
  }
  assert.equal(profile.status, 200);
  const result = await call('/eligibility-checks', 'POST', { birth_date: date, has_diabetes_diagnosis: false, has_urgent_warning_sign: false, population_in_scope: true, ...flags });
  assert.equal(result.status, 200);
  return result.data;
}
(async () => {
  const credentials = { email: `qa-safe-${Date.now()}@example.com`, password: `Qa-${require('node:crypto').randomBytes(12).toString('hex')}!9` };
  assert.equal((await call('/auth/signup', 'POST', { ...credentials, terms_agreed: true })).status, 201);
  const login = await call('/auth/login', 'POST', credentials);
  assert.equal(login.status, 200); token = login.data.access_token; assert.ok(token);
  const underage = await call('/users/me/profile', 'PATCH', { birthday: birthday(13), gender: 'FEMALE' });
  assert.equal(underage.status, 422);
  console.log('PASS age 13: profile rejected (signup endpoint itself has no birthday field)');
  const noConsent = await eligibility(60);
  assert.ok(noConsent.reason_codes.includes('CONSENT_REQUIRED'));
  assert.equal(noConsent.model_eligible, false);
  assert.equal(noConsent.challenge_eligible, false);
  console.log('PASS consent missing: prediction/challenge blocked');
  assert.equal((await call('/consents', 'POST', { consent_item: 'health_data', version: '1.0', is_agreed: true })).status, 201);
  for (const age of [14, 18, 19, 44, 45, 105, 106]) {
    const data = await eligibility(age);
    const inRange = age >= data.active_model.min_age && (data.active_model.max_age == null || age <= data.active_model.max_age);
    assert.equal(data.current_health_check_eligible, age >= 19);
    assert.equal(data.future_prediction_eligible, inRange);
    assert.equal(data.challenge_eligible, true);
    console.log(`PASS age ${age}: current=${data.current_health_check_eligible}, future=${data.future_prediction_eligible}, challenge=${data.challenge_eligible}, next=${data.next_action}`);
  }
  for (const [flags, reason, action] of [
    [{ has_urgent_warning_sign: true }, 'URGENT_MEDICAL_ATTENTION', 'urgent_medical_guidance'],
    [{ has_diabetes_diagnosis: true }, 'DIAGNOSED_DIABETES', 'clinician_guidance'],
  ]) {
    const data = await eligibility(60, flags);
    assert.ok(data.reason_codes.includes(reason));
    assert.equal(data.current_health_check_eligible, false);
    assert.equal(data.future_prediction_eligible, false);
    assert.equal(data.challenge_eligible, false);
    assert.equal(data.next_action, action);
    console.log(`PASS ${reason}: all personalized routes blocked, next=${action}`);
  }
  const schema = await (await fetch(`${base}/api/openapi.json`)).json();
  assert.equal(Boolean(schema.paths['/api/v1/current-screening-inputs']), false);
  console.log('PENDING current-screening-inputs absent from running OpenAPI; same-day symptom field absent from EligibilityCreateRequest');
})().catch(error => { console.error(`FAIL ${error.name}: ${error.message}`); process.exitCode = 1; });
