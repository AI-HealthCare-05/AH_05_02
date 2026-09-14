const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../src/frontend/app.js'), 'utf8');
const c = vm.createContext({ URL });
vm.runInContext(source.match(/^const safeExternalUrl = [^]*?^};/m)[0], c);
for (const name of ['normalizeHealthEducationResult', 'isSampleFacilityPayload']) {
  vm.runInContext(source.match(new RegExp(`^function ${name}\\([^]*?^}`, 'm'))[0], c);
}
test('empty and malformed answers are never successful', () => {
  for (const value of [null, {}, { answer: '' }, { answer: '  ' }, { answer: 12 }, { answer: ['text'] }]) {
    assert.equal(c.normalizeHealthEducationResult(value).state, 'empty');
  }
});
test('unknown status fails closed', () => {
  for (const answer_status of ['unknown', '__proto__']) {
    assert.throws(() => c.normalizeHealthEducationResult({ answer: 'QA', answer_status }), /응답 형식/);
  }
});
test('grounded answer requires usable sources, without unsafe link fallback', () => {
  const input = { answer: 'QA answer', answer_status: 'grounded' };
  for (const citations of [[], [null], [{ url: 'javascript:alert(1)' }]]) {
    const result = c.normalizeHealthEducationResult({ ...input, citations });
    assert.equal(result.state, 'insufficient');
    assert.notEqual(result.answer, input.answer);
  }
  const result = c.normalizeHealthEducationResult({ ...input, citations: [{ url: 'https://example.com/reference', title: '출처' }] });
  assert.equal(result.state, 'done');
  assert.equal(result.citations.length, 1);
  assert.ok(result.medicalNotice.includes('진단'));
});
test('insufficient and medical refusal preserve non-success statuses', () => {
  assert.equal(c.normalizeHealthEducationResult({ answer: 'QA', answer_status: 'insufficient_evidence' }).state, 'insufficient');
  assert.equal(c.normalizeHealthEducationResult({ answer: 'QA', answer_status: 'medical_safety_refusal' }).state, 'refused');
});
test('either development marker identifies sample facility data', () => {
  assert.equal(c.isSampleFacilityPayload({ provider_kind: 'development' }), true);
  assert.equal(c.isSampleFacilityPayload({ data_source: 'development_mock' }), true);
  assert.equal(c.isSampleFacilityPayload({ provider_kind: 'kakao_local_api' }), false);
});
