const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../../src/frontend/app.js'), 'utf8');
const context = vm.createContext({});
vm.runInContext(source.match(/^function signupPasswordIssues\([^]*?^}/m)[0], context);
test('reports each missing password requirement without echoing the value', () => {
  for (const [value, expected] of [['abcdef12!', '대문자'], ['ABCDEF12!', '소문자'], ['Abcdefgh!', '숫자'], ['Abcdef123', '특수문자'], ['Ab1!', '8자']]) {
    const issues = context.signupPasswordIssues(value);
    assert.equal(issues.length, 1);
    assert.match(issues[0], new RegExp(expected));
    assert.ok(!issues[0].includes(value));
  }
});
test('empty password reports all five requirements; whitespace is not a special character', () => {
  assert.equal(context.signupPasswordIssues('').length, 5);
  assert.match(context.signupPasswordIssues('Abcdef12 ')[0], /특수문자/);
});
test('server-tested password format has no missing requirements', () => {
  assert.equal(context.signupPasswordIssues('ValidQa123!').length, 0);
});
