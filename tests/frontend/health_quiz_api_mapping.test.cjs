const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../src/frontend/app.js'), 'utf8');
const context = vm.createContext({ Map });

for (const name of [
  'inferredEducationAnswer',
  'quizTypeLabel',
  'quizOptions',
  'mapHealthEducationQuizzes',
  'educationQuestions',
]) {
  const match = source.match(new RegExp(`^function ${name}\\([^]*?^}`, 'm'));
  assert.ok(match, `${name} must exist`);
  vm.runInContext(match[0], context);
}

test('server quiz ids and choices reach the grading request model', () => {
  const payload = {
    items: [{
      quiz_id: 'ox-kdca-diabetes',
      question: '이 설명은 맞을까요?',
      quiz_type: 'ox',
      options: null,
      source_title: '질병관리청',
      source_url: 'https://health.kdca.go.kr/example',
      week_number: 1,
      locked: false,
    }],
  };
  const mapped = context.mapHealthEducationQuizzes(payload);
  const questions = context.educationQuestions(mapped.items[0]);

  assert.equal(questions[0].quizId, 'ox-kdca-diabetes');
  assert.deepEqual([...questions[0].options], ['참', '거짓']);
  assert.equal(questions[0].source.title, '질병관리청');
});

test('the screen loads the server quiz endpoint instead of the legacy catalogue', () => {
  assert.match(source, /api\("\/health-education\/quizzes"\)/);
});

test('the retro intro auth runtime also loads the server quiz endpoint', () => {
  const retroSource = fs.readFileSync(path.join(__dirname, '../../src/frontend/intro-retro-app.js'), 'utf8');
  assert.match(retroSource, /api\("\/health-education\/quizzes"\)/);
  assert.match(retroSource, /health-education\/quizzes\/\$\{encodeURIComponent\(question\.quizId\)\}\/answers/);
});
