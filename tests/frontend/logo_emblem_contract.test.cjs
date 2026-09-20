const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const frontendRoot = path.join(__dirname, '../../src/frontend');
const emblemPath = '/static/assets/gandang-gandang-emblem-hyeoldangi-clean-transparent.png';

for (const relativePath of ['index.html', 'intro-retro.html', 'suin/index.html']) {
  const source = fs.readFileSync(path.join(frontendRoot, relativePath), 'utf8');
  assert.match(source, new RegExp(`<img class="brand-emblem" src="${emblemPath}" alt="">`));
  assert.doesNotMatch(source, /brand-mark" aria-hidden="true">\+<\/span> 간당간당/);
}

const forestSource = fs.readFileSync(path.join(frontendRoot, 'forest.html'), 'utf8');
assert.match(forestSource, new RegExp(`<img class="forest-boot-emblem" src="${emblemPath}" alt="간당간당">`));
assert.match(forestSource, new RegExp(`<img class="forest-brand-emblem" src="${emblemPath}" alt="">`));
assert.doesNotMatch(forestSource, /<span>간당<b>간당<\/b><\/span>/);

assert.ok(fs.existsSync(path.join(frontendRoot, 'assets/gandang-gandang-emblem-hyeoldangi-clean-transparent.png')));
console.log('PASS: text-free shared emblem is wired into service and carrot forest headers');
