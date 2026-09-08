const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../src/frontend/app.js'), 'utf8');
function harness(status, body, offline = false) {
  const context = vm.createContext({ state: {}, fetch: async () => {
    if (offline) throw new Error('QA offline');
    return { ok: status < 400, status, json: async () => body };
  } });
  vm.runInContext(source.match(/^class ApiError extends Error \{[^]*?^}/m)[0], context);
  for (const name of ['normalizeModelErrorCode', 'fallbackApiErrorCode', 'fallbackApiErrorMessage', 'api', 'normalizeForecastSignal', 'forecastSignalLabel']) {
    vm.runInContext(source.match(new RegExp(`^(?:async )?function ${name}\\([^]*?^}`, 'm'))[0], context);
  }
  return context;
}
for (const [code, status, retryable, expected] of [
  ['ML_INPUT_INVALID', 422, false, 'ML_INPUT_OUT_OF_RANGE'],
  ['MODEL_UNAVAILABLE', 503, false, 'ML_MODEL_UNAVAILABLE'],
  ['MODEL_CONTRACT_INVALID', 503, false, 'ML_MODEL_CONTRACT_ERROR'],
  ['QUEUE_UNAVAILABLE', 503, true, 'QUEUE_UNAVAILABLE'],
]) test(`structured error ${code} retains retry policy`, async () => {
  const c = harness(status, { detail: { error_code: code, message: 'QA error', retryable } });
  await assert.rejects(c.api('/qa'), e => e.code === expected && e.retryable === retryable && e.message === 'QA error');
});
test('legacy string error, validation array, network error remain actionable', async () => {
  await assert.rejects(harness(422, { detail: '프로필 입력 필요' }).api('/qa'), e => e.message === '프로필 입력 필요');
  await assert.rejects(harness(422, { detail: [{ loc: ['body', 'height_cm'], msg: 'invalid' }] }).api('/qa'), e => e.message.includes('height_cm') && e.details.length === 1);
  await assert.rejects(harness(0, {}, true).api('/qa'), e => e.code === 'NETWORK_ERROR' && e.retryable);
});
test('signal mapping is Korean and unknown signals stay pending', () => {
  const c = harness(200, {});
  for (const [key, label] of [['low', '낮음'], ['caution', '주의'], ['high', '높음']]) {
    assert.equal(c.forecastSignalLabel(c.normalizeForecastSignal(key)), label);
  }
  assert.equal(c.normalizeForecastSignal('unknown'), null);
  assert.equal(c.forecastSignalLabel(null), '결과 준비 중');
});
