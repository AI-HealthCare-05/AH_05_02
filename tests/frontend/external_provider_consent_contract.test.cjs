const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.join(__dirname, '../../src/frontend');
for (const [htmlName, scriptName] of [
  ['index.html', 'app.js'],
  ['intro-retro.html', 'intro-retro-app.js'],
]) {
  const html = fs.readFileSync(path.join(root, htmlName), 'utf8');
  const script = fs.readFileSync(path.join(root, scriptName), 'utf8');
  assert.match(html, /id="ocr-external-provider-consent"/);
  assert.match(script, /formData\.append\("external_provider_consent", "true"\)/);
  assert.match(script, /외부 OCR 처리 동의/);
}
console.log('PASS: OCR upload requires explicit external-provider consent in both service entries');
