const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const app = fs.readFileSync(path.join(root, 'src/frontend/app.js'), 'utf8');
const forest = fs.readFileSync(path.join(root, 'src/frontend/forest.html'), 'utf8');

test('forest brand returns to the main service on the same origin', () => {
  assert.match(forest, /class="forest-brand" href="\/"/);
});

test('main service restores the cookie session before resuming the account', () => {
  assert.match(app, /async function resumeCookieSession\(\)/);
  assert.match(app, /api\("\/auth\/token\/refresh"\)/);
  assert.match(app, /state\.token = refreshed\.access_token;/);
  assert.match(app, /await resumeAuthenticatedAccount\(\);/);
  assert.match(app, /resumeCookieSession\(\);/);
});
