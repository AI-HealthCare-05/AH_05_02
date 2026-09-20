const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const frontendRoot = path.join(__dirname, '../../src/frontend');
const logoPath = '/static/assets/gandang-logo-web-v2.png';
const faviconPath = '/static/assets/gandang-site-icon-32.png';

for (const relativePath of ['index.html', 'intro-retro.html', 'suin/index.html']) {
  const source = fs.readFileSync(path.join(frontendRoot, relativePath), 'utf8');
  assert.match(source, new RegExp(`<img class="brand-logo" src="${logoPath}"`));
  assert.match(source, new RegExp(`<link rel="icon" href="${faviconPath}"`));
  assert.doesNotMatch(source, /brand-mark" aria-hidden="true">\+<\/span> 간당간당/);
}

const forestSource = fs.readFileSync(path.join(frontendRoot, 'forest.html'), 'utf8');
assert.match(forestSource, /<img class="forest-boot-logo" src="\/static\/assets\/gandang-logo-forest-pixel-v2\.png"/);
assert.match(forestSource, /<img class="forest-brand-logo" src="\/static\/assets\/gandang-logo-forest-pixel-v2\.png"/);
assert.doesNotMatch(forestSource, /<span>간당<b>간당<\/b><\/span>/);

for (const file of [
  'assets/gandang-logo-web-v2.png',
  'assets/gandang-logo-forest-pixel-v2.png',
  'assets/gandang-site-icon-32.png',
  'assets/gandang-site-icon-180.png',
  'assets/gandang-site-icon-192.png',
  'assets/gandang-site-icon-512.png',
  'favicon.ico',
]) {
  assert.ok(fs.existsSync(path.join(frontendRoot, file)));
}
console.log('PASS: dedicated web, forest, and browser icon assets are wired into every service shell');
