const assert = require('node:assert/strict');
const { mkdirSync, readFileSync } = require('node:fs');
assert.match(readFileSync('src/frontend/app.js', 'utf8'), /const duration = 200;/);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:8022';
assert.ok(['localhost', '127.0.0.1'].includes(new URL(base).hostname));
(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_BIN ? { executablePath: process.env.CHROME_BIN } : {}) });
  mkdirSync('tmp/ui-ux-qa', { recursive: true });
  try {
    for (const width of [1440, 380]) {
      const page = await browser.newPage({ viewport: { width, height: 1000 } });
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      await page.goto(base, { waitUntil: 'networkidle' });
      assert.ok(await page.locator('.service-story').isVisible());
      assert.equal(await page.locator('.service-story .story-note').count(), 0);
      assert.equal(await page.locator('.service-story .story-description').count(), 5);
      assert.equal(await page.locator('#story-forest .story-forest-footer').count(), 0);
      assert.ok(await page.locator('.intro-safety-note').isVisible());
      assert.ok((await page.locator('#story-closing-title').innerText()).includes('함께 시작해요'));
      const storyCta = page.locator('.story-closing [data-story-start]');
      assert.match(await storyCta.innerText(), /회원가입하고 시작하기/);
      assert.equal(await storyCta.locator('.story-arrow-icon').innerText(), '→');
      const ctaPalette = await storyCta.evaluate(button => {
        const style = getComputedStyle(button);
        const badge = getComputedStyle(button.querySelector('.story-arrow-badge'));
        return { background: style.backgroundColor, color: style.color, badge: badge.backgroundColor };
      });
      assert.deepEqual(ctaPalette, { background: 'rgb(23, 107, 91)', color: 'rgb(245, 244, 239)', badge: 'rgb(11, 77, 66)' });
      await storyCta.hover();
      await page.waitForTimeout(520);
      const reveal = await storyCta.evaluate(button => {
        const bounds = button.getBoundingClientRect();
        const icon = button.querySelector('.story-arrow-icon').getBoundingClientRect();
        return {
          badgeTransform: getComputedStyle(button.querySelector('.story-arrow-badge')).transform,
          iconOffset: Math.abs((icon.left + icon.width / 2) - (bounds.left + bounds.width / 2)),
        };
      });
      assert.notEqual(reveal.badgeTransform, 'none');
      assert.ok(reveal.iconOffset < 2);
      assert.equal(await page.locator('.service-story').evaluate(n => getComputedStyle(n).backgroundColor), 'rgb(245, 244, 239)');
      const minContrast = await page.evaluate(() => {
        const style = getComputedStyle(document.body);
        const luminance = hex => {
          const rgb = hex.trim().replace('#', '').match(/../g).map(v => parseInt(v, 16) / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4);
          return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722;
        };
        const inks = ['--landing-ink', '--landing-muted', '--landing-accent'].map(key => luminance(style.getPropertyValue(key)));
        const papers = ['#f5f4ef', '#eeeee8', '#e6ece5'].map(luminance);
        return Math.min(...inks.flatMap(ink => papers.map(paper => (paper + .05) / (ink + .05))));
      });
      assert.ok(minContrast >= 4.5, `Landing palette contrast ${minContrast}`);
      assert.equal(await page.locator('.landing-first img, .landing-first ol, .landing-first ul').count(), 0);
      assert.ok(await page.locator('#intro-start').isVisible());
      await page.locator('.landing-first').screenshot({ path: `tmp/ui-ux-qa/minimal-hero-${width}.png` });
      await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
      await page.locator('#landing-next').click();
      await page.waitForFunction(() => Math.abs(document.querySelector('.story-opening').getBoundingClientRect().top - document.querySelector('.topbar').getBoundingClientRect().height) < 3);
      assert.equal(await page.locator('#landing-position').innerText(), '서비스 소개');
      assert.ok(!/\d\s*\//.test(await page.locator('.landing-pager').innerText()));
      await page.locator('#landing-next').click();
      await page.waitForFunction(() => Math.abs(document.querySelector('#story-health').getBoundingClientRect().top - document.querySelector('.topbar').getBoundingClientRect().height) < 3);
      if (width === 1440) {
        await page.evaluate(() => new Promise(resolve => {
          let previous = scrollY, stable = 0;
          function frame() { stable = scrollY === previous ? stable + 1 : 0; previous = scrollY; if (stable >= 12) resolve(); else requestAnimationFrame(frame); }
          requestAnimationFrame(frame);
        }));
        await page.mouse.move(700, 450);
        const beforeWheel = await page.evaluate(() => scrollY);
        await page.mouse.wheel(0, 600);
        // A 200ms transition keeps the scene change quick while making the motion readable.
        await page.waitForFunction(before => scrollY > before + 100, beforeWheel);
        await page.waitForFunction(() => !document.documentElement.classList.contains('landing-transitioning'));
        assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).scrollSnapType), 'y mandatory');
        assert.equal(await page.locator('#story-health').evaluate(n => getComputedStyle(n).scrollSnapStop), 'always');
        await page.waitForFunction(() => Math.abs(document.querySelector('#story-results').getBoundingClientRect().top - document.querySelector('.topbar').getBoundingClientRect().height) < 3);
      }
      assert.ok(await page.locator('.service-story img').evaluateAll(nodes => nodes.every(n => n.complete && n.naturalWidth > 0)));
      assert.equal(await page.locator('.story-record-preview h3').innerText(), '나를 알아가는 기록');
      assert.equal(await page.locator('.story-record-preview h3').evaluate(n => getComputedStyle(n).textAlign), 'center');
      assert.equal(await page.locator('#story-health-title br, #story-challenge-title br, #story-report-title br, #story-health .story-description br, #story-results .story-description br').count(), 0);
      assert.ok((await page.locator('.zoom-guides').getAttribute('d')).includes('L'));
      assert.deepEqual(await page.locator('.story-record-categories li').allTextContents(), ['기본정보', '건강정보', '생활습관']);
      assert.equal(await page.locator('.story-record-categories').evaluate(n => getComputedStyle(n).textAlign), 'center');
      assert.ok(!(await page.locator('.story-record-preview').innerText()).includes('이용 화면 예시'));
      assert.equal(await page.locator('.story-practice-preview figcaption').innerText(), '차곡차곡 쌓인 실천');
      assert.equal(await page.locator('.story-practice-days span').count(), 28);
      assert.equal(await page.locator('.story-copy > p:not(.story-kicker)').count(), 0);
      for (const id of ['health', 'results', 'challenge', 'report']) {
        const layout = await page.locator(`#story-${id}`).evaluate(section => {
          const copy = section.querySelector('.story-copy').getBoundingClientRect();
          const art = section.querySelector('.story-scene').getBoundingClientRect();
          const description = section.querySelector('.story-description').getBoundingClientRect();
          return { below: art.top >= copy.bottom && description.top >= art.bottom - 1, width: art.width, height: art.height };
        });
        assert.ok(layout.below && layout.width >= width * .75 && layout.height >= 280);
        const panel = await page.locator(`#story-${id} .story-scene`).evaluate(n => {
          const style = getComputedStyle(n);
          return { color: style.backgroundColor, image: style.backgroundImage, radius: style.borderRadius };
        });
        assert.deepEqual(panel, { color: 'rgba(0, 0, 0, 0)', image: 'none', radius: '0px' });
      }
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false);
      await page.locator('#story-health').screenshot({ path: `tmp/ui-ux-qa/story-health-${width}.png` });
      await page.locator('#story-report').screenshot({ path: `tmp/ui-ux-qa/story-report-${width}.png` });
      await page.locator('#story-forest').screenshot({ path: `tmp/ui-ux-qa/story-forest-${width}.png` });
      await page.locator('.story-closing').screenshot({ path: `tmp/ui-ux-qa/story-closing-${width}.png` });
      for (const [label, selector] of [['시작', '.landing-first'], ['서비스 소개', '.story-opening'], ['건강정보', '#story-health'], ['위험 신호', '#story-results'], ['챌린지', '#story-challenge'], ['리포트', '#story-report'], ['당근의 숲', '#story-forest'], ['함께 시작', '.story-closing']]) {
        await page.locator('#landing-position').click();
        assert.equal(await page.locator('#landing-position').getAttribute('aria-expanded'), 'true');
        const menuBox = await page.locator('#landing-picker').boundingBox();
        assert.ok(menuBox.x >= 0 && menuBox.x + menuBox.width <= width);
        await page.locator('#landing-picker').getByRole('button', { name: label, exact: true }).click();
        await page.waitForFunction(() => !document.documentElement.classList.contains('landing-transitioning'));
        assert.ok(await page.locator('#landing-picker').isHidden());
        assert.equal(await page.locator('#landing-position').innerText(), label);
        assert.ok(await page.locator(`${selector} h1, ${selector} h2`).evaluate(n => n === document.activeElement));
      }
      await page.locator('#landing-position').click();
      await page.keyboard.press('Escape');
      assert.ok(await page.locator('#landing-picker').isHidden());
      assert.equal(await page.evaluate(() => document.activeElement.id), 'landing-position');
      assert.equal(await page.locator('#story-forest [data-story-start]').count(), 0);
      assert.equal(await page.locator('[data-story-start]').count(), 1);
      await page.locator('.story-closing [data-story-start]').click();
      assert.ok(await page.locator('#signup-form').isVisible());
      assert.ok(await page.locator('.service-story').isHidden());
      await page.evaluate(() => showStep(1));
      await page.locator('#intro-start').click();
      assert.ok(await page.locator('#signup-form').isVisible());
      await page.evaluate(() => showStep(1));
      await page.locator('#font-toggle').click();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false);
      assert.deepEqual(errors, []);
      await page.emulateMedia({ reducedMotion: 'reduce' });
      assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).scrollSnapType), 'none');
      console.log(`PASS ${width}px: snapped screen navigation, images, both signup CTAs, large-text/no overflow`);
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
