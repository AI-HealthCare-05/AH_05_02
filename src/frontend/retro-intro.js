/* Time types the opening; native scrolling scrubs the disk and camera. */
(() => {
  const hero = document.querySelector('.retro-intro');
  if (!hero) return;
  const health = document.querySelector('#story-health');
  const orbit = document.querySelector('#story-orbit');
  const forest = document.querySelector('#story-forest');
  const topbar = document.querySelector('.topbar');
  const routeNav = document.querySelector('.intro-route-nav');
  const computer = hero.querySelector('.retro-computer');
  const headerGuarded = [...document.querySelectorAll('.retro-computer-shell,.retro-display,.orbit-copy,.orbit-belt,.orbit-mascot,.handoff-computer,.story-flow-step,.forest-computer,#story-forest>.story-description,.story-closing>[data-closing-type],.story-closing>[data-story-start]')];
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const clamp = (value) => Math.max(0, Math.min(1, value));
  const ramp = (p, start, end) => clamp((p - start) / (end - start));
  const ease = (p) => p * p * (3 - 2 * p);
  function retroFrame(progress) {
    const overall = clamp(progress);
    const p = clamp(overall / .7);
    const enter = ease(ramp(p, .4, .54));
    return {
      scale: 1 + .22 * ease(ramp(p, 0, .32)) - .16 * ease(ramp(p, .46, .66)) + .38 * ease(ramp(overall, .73, .86)),
      copy: 1 - ramp(p, .08, .2),
      meet: ramp(p, .19, .31) * (1 - ramp(p, .86, .92)),
      meetScale: .9 + .1 * ramp(p, .19, .31),
      hint: 1 - ramp(p, .36, .45),
      diskOffset: 1 - enter,
      diskVisible: ramp(p, .4, .43) * (1 - ramp(p, .83, .845)),
      diskTurn: ease(ramp(p, .58, .74)),
      diskInsert: ease(ramp(p, .74, .84)),
      handLeave: ease(ramp(p, .84, .95)),
      handVisible: ramp(p, .4, .43) * (1 - ramp(p, .93, .97)),
      camera: ease(ramp(p, .44, .65)),
      loaded: ramp(p, .89, .96) * (1 - ramp(overall, .9, .97)),
      spin: ease(ramp(overall, .76, .9)),
      wipe: ramp(overall, .9, 1),
    };
  }
  function handoffFrame(progress) {
    const p = clamp(progress);
    return { reveal: ease(ramp(p, .45, .72)), turn: ease(ramp(p, .55, .9)), clear: 1 - ramp(p, .38, .62) };
  }
  function typedCharacters(elapsed, start, length, speed) {
    return Math.min(length, Math.max(0, Math.floor((elapsed - start) / speed)));
  }
  function sceneEntrance(top, viewportHeight, finish = .65) {
    return ease(ramp(1 - top / Math.max(1, viewportHeight), 0, finish));
  }
  function headerCutoff(safeEdge, top, paintedHeight, layoutHeight) {
    // Convert viewport clearance into local coordinates, including scaled CRTs.
    return (safeEdge - top) * layoutHeight / Math.max(1, paintedHeight);
  }
  let frame = 0;
  let typingFrame = 0;
  let typingDone = false;
  const lines = [...hero.querySelectorAll('.retro-type-line')];
  const timings = [1000, 2450, 3650];
  const speeds = [105, 60, 60];
  let typingStart = null;
  let monitorReady = false;
  let wasAtOpening = false;
  const letterGroups = lines.map(line => {
    const text = line.querySelector('.retro-type-text');
    if (!line.parentElement.hasAttribute('aria-label')) line.parentElement.setAttribute('aria-label', line.parentElement.textContent);
    text.setAttribute('aria-hidden', 'true');
    return Array.from(text.textContent).map((letter, index) => {
      if (index === 0) text.textContent = '';
      const span = document.createElement('span');
      span.textContent = letter;
      span.style.opacity = '0';
      text.appendChild(span);
      return span;
    });
  });
  function finishTyping() {
    cancelAnimationFrame(typingFrame);
    typingDone = true;
    hero.style.setProperty('--intro-details', 1);
    letterGroups.forEach(group => group.forEach(letter => { letter.style.opacity = '1'; }));
    lines.forEach(line => { line.style.setProperty('--typed', 1); line.style.setProperty('--cursor', 0); });
  }
  function startTyping() {
    cancelAnimationFrame(typingFrame);
    typingDone = false;
    typingStart = null;
    hero.style.setProperty('--intro-details', 0);
    letterGroups.forEach(group => group.forEach(letter => { letter.style.opacity = '0'; }));
    lines.forEach(line => { line.style.setProperty('--typed', 0); line.style.setProperty('--cursor', 0); });
    typingFrame = requestAnimationFrame(type);
  }
  function type(now) {
    if (reduced.matches) { finishTyping(); return; }
    if (!monitorReady || document.hidden || !document.body.classList.contains('intro-mode') || progress() > .06) {
      typingFrame = 0;
      return;
    }
    if (typingStart === null) typingStart = now;
    const elapsed = now - typingStart;
    hero.style.setProperty('--intro-details', ease(ramp(elapsed, 2600, 3000)));
    lines.forEach((line, index) => {
      const group = letterGroups[index];
      const count = typedCharacters(elapsed, timings[index], group.length, speeds[index]);
      group.forEach((letter, i) => { letter.style.opacity = i < count ? '1' : '0'; });
      line.style.setProperty('--typed', count / Math.max(1, group.length));
      line.style.setProperty('--cursor', elapsed >= timings[index] && count < group.length ? 1 : 0);
    });
    if (elapsed < 5300 && !typingDone) typingFrame = requestAnimationFrame(type);
    else finishTyping();
  }
  const shell = hero.querySelector('.retro-computer-shell');
  shell.decode().catch(() => {}).then(() => {
    monitorReady = true;
    if (progress() <= .06) startTyping();
  });
  addEventListener('visibilitychange', () => {
    if (!document.hidden && progress() <= .06 && !typingDone) startTyping();
  });
  // A fresh visit/reload starts with the empty monitor, not a restored scroll scene.
  history.scrollRestoration = 'manual';
  addEventListener('pageshow', () => {
    if (document.body.classList.contains('intro-mode') && !location.hash) {
      scrollTo({ top: 0, behavior: 'instant' });
      startTyping();
    }
  });
  function progress() {
    return clamp(-hero.getBoundingClientRect().top / Math.max(1, hero.offsetHeight - innerHeight));
  }
  function update() {
    frame = 0;
    if (!document.body.classList.contains('intro-mode')) return;
    const p = reduced.matches ? 0 : progress();
    const compact = scrollY > 80;
    topbar.classList.toggle('retro-nav-compact', compact);
    routeNav.hidden = compact;
    const headerBottom = topbar.getBoundingClientRect().bottom;
    document.documentElement.style.setProperty('--intro-safe-top', `${Math.ceil(headerBottom + 28)}px`);
    // Extra sticky space belongs to the folder cover, not the mascot reveal.
    const guideCoverHold = parseFloat(getComputedStyle(orbit).getPropertyValue('--guide-cover-hold')) || 0;
    const orbitProgress = clamp(-orbit.getBoundingClientRect().top / Math.max(1, orbit.offsetHeight - innerHeight * (1 + guideCoverHold)));
    const handoff = reduced.matches ? { reveal: 0, turn: 0, clear: 1 } : handoffFrame(orbitProgress);
    orbit.style.setProperty('--orbit-scroll', orbitProgress);
    orbit.style.setProperty('--handoff-reveal', handoff.reveal);
    orbit.style.setProperty('--handoff-turn', handoff.turn);
    orbit.style.setProperty('--handoff-clear', handoff.clear);
    // Follow the incoming folder directly so reverse scrolling restores the guide.
    const folderCover = guideCoverHold && !reduced.matches
      ? ease(ramp(1 - health.getBoundingClientRect().top / innerHeight, .16, .54)) : 0;
    orbit.style.setProperty('--guide-folder-cover', folderCover);
    // Reveal from actual scroll position, including the ending wheel destinations.
    forest.style.setProperty('--forest-enter', reduced.matches ? 1 : sceneEntrance(forest.getBoundingClientRect().top, innerHeight));
    const forestFitsViewport = matchMedia('(min-width:761px) and (min-height:681px)').matches;
    forest.style.setProperty('--forest-caption', reduced.matches ? 1 : forestFitsViewport
      ? sceneEntrance(forest.getBoundingClientRect().top, innerHeight, .8)
      : sceneEntrance(forest.getBoundingClientRect().top + forest.querySelector('.story-description').offsetTop, innerHeight, .3));
    closing.style.setProperty('--closing-enter', reduced.matches ? 1 : sceneEntrance(closing.getBoundingClientRect().top, innerHeight, .55));
    orbit.querySelector('.orbit-handoff').setAttribute('aria-hidden', String(handoff.reveal < .5));
    const atOpening = p <= .01;
    if (atOpening && !wasAtOpening && monitorReady) startTyping();
    wasAtOpening = atOpening;
    const values = retroFrame(p);
    for (const [key, value] of Object.entries(values)) hero.style.setProperty(`--retro-${key.replace(/[A-Z]/g, letter => '-' + letter.toLowerCase())}`, value);
    const width = computer.offsetWidth;
    const height = computer.offsetHeight;
    const top = parseFloat(getComputedStyle(computer).top) || 0;
    const slotY = top + height * .42 + height * (.746 - .42) * values.scale;
    const slotCamera = Math.min(0, innerHeight * .76 - slotY) * values.camera;
    const screenCamera = innerHeight * .5 - (top + height * .42 - height * .03 * values.scale);
    hero.style.setProperty('--retro-camera-y', (slotCamera * (1 - values.spin) + screenCamera * values.spin) + 'px');
    hero.style.setProperty('--retro-disk-x', (values.diskOffset * width * .85) + 'px');
    hero.style.setProperty('--retro-hand-x', ((values.diskOffset + values.handLeave) * width * .85) + 'px');
    hero.style.setProperty('--retro-copy-shift', -20 * (1 - values.copy));
    hero.querySelector('.retro-scroll').disabled = values.hint < .1;
    hero.querySelector('.retro-meet').setAttribute('aria-hidden', String(values.meet < .5));
    hero.querySelector('.retro-loaded').setAttribute('aria-hidden', String(values.loaded < .5));
    hero.querySelector('.retro-scroll-label').textContent = p < .3 ? '스크롤해서 만나보세요' : '디스크를 넣어볼까요?';
    health.style.setProperty('--health-reveal', reduced.matches ? 1 : clamp((innerHeight - health.getBoundingClientRect().top) / (innerHeight * .6)));
    // Only fade artwork/copy at the header edge; section backgrounds remain continuous.
    for (const element of headerGuarded) {
      const rect = element.getBoundingClientRect();
      element.style.setProperty('--header-cutoff', `${headerCutoff(headerBottom + 28, rect.top, rect.height, element.offsetHeight)}px`);
    }
    if (typeof updateLandingPosition === 'function') updateLandingPosition();
  }
  function schedule() { if (!frame) frame = requestAnimationFrame(update); }
  function advance() {
    finishTyping();
    const p = progress();
    const target = p < .22 ? .238 : p < .38 ? .392 : p < .67 ? .70 : p < .79 ? .83 : p < .94 ? .97 : null;
    const top = reduced.matches || target === null ? scrollY + orbit.getBoundingClientRect().top : scrollY + hero.getBoundingClientRect().top + (hero.offsetHeight - innerHeight) * target;
    scrollTo({ top, behavior: reduced.matches ? 'instant' : 'smooth' });
  }
  function snapToOrbit() {
    finishTyping();
    scrollTo({ top: scrollY + orbit.getBoundingClientRect().top, behavior: reduced.matches ? 'instant' : 'smooth' });
  }
  let introSnapLock = 0;
  function snapLateIntroWheel(event) {
    if (reduced.matches || !document.body.classList.contains('intro-mode') || event.deltaY <= 0) return;
    const p = progress();
    if (p < .78 || p >= 1 || Date.now() < introSnapLock) return;
    event.preventDefault();
    introSnapLock = Date.now() + 850;
    snapToOrbit();
  }
  addEventListener('scroll', schedule, { passive: true });
  addEventListener('wheel', snapLateIntroWheel, { passive: false });
  addEventListener('resize', schedule, { passive: true });
  new ResizeObserver(schedule).observe(topbar);
  reduced.addEventListener('change', () => { if (reduced.matches) finishTyping(); schedule(); });
  new MutationObserver(schedule).observe(document.body, { attributes: true, attributeFilter: ['class'] });
  hero.querySelector('.retro-scroll').addEventListener('click', advance);
  hero.addEventListener('retro-advance', advance);
  document.querySelector('[data-intro-signup]').addEventListener('click', () => document.querySelector('#sidebar-signup').click());
  routeNav.querySelectorAll('a').forEach(link => link.addEventListener('click', event => {
    event.preventDefault();
    moveLandingTo(document.querySelector(link.getAttribute('href')));
  }));
  new IntersectionObserver(entries => {
    orbit.classList.toggle('is-orbit-visible', entries[0].isIntersecting);
  }, { threshold: .05 }).observe(orbit);
  const closing = document.querySelector('.story-closing');
  const closingButton = closing.querySelector('[data-story-start]');
  const closingLines = [...closing.querySelectorAll('[data-closing-type]')];
  const closingLetters = closingLines.map(line => {
    line.setAttribute('aria-label', line.textContent);
    line.style.visibility = 'visible';
    const letters = [];
    [...line.childNodes].forEach(node => {
      if (node.nodeType !== Node.TEXT_NODE) return;
      const fragment = document.createDocumentFragment();
      Array.from(node.textContent).forEach(character => {
        const span = document.createElement('span');
        span.className = 'closing-letter';
        span.setAttribute('aria-hidden', 'true');
        span.textContent = character;
        fragment.appendChild(span);
        letters.push(span);
      });
      node.replaceWith(fragment);
    });
    return letters;
  });
  const closingSpeeds = [95, 55];
  const closingStarts = [500, 500 + closingLetters[0].length * 95 + 450];
  let closingFrame = 0;
  let closingStart = null;
  let closingFinished = false;
  function finishClosing() {
    cancelAnimationFrame(closingFrame);
    closingLetters.forEach(group => group.forEach(letter => { letter.style.opacity = '1'; }));
    closing.classList.add('closing-ready');
    closingButton.disabled = false;
    closingFinished = true;
  }
  function typeClosing(now) {
    if (reduced.matches) { finishClosing(); return; }
    if (closingStart === null) closingStart = now;
    const elapsed = now - closingStart;
    closingLetters.forEach((group, index) => {
      const count = typedCharacters(elapsed, closingStarts[index], group.length, closingSpeeds[index]);
      group.forEach((letter, i) => { letter.style.opacity = i < count ? '1' : '0'; });
    });
    if (elapsed >= closingStarts[1] + closingLetters[1].length * closingSpeeds[1] + 350) finishClosing();
    else closingFrame = requestAnimationFrame(typeClosing);
  }
  closingButton.disabled = !reduced.matches;
  if (reduced.matches) finishClosing();
  new IntersectionObserver(entries => {
    if (entries[0].isIntersecting && !closingFinished && closingStart === null) closingFrame = requestAnimationFrame(typeClosing);
  }, { threshold: .15 }).observe(closingLines[0]);
  reduced.addEventListener('change', () => { if (reduced.matches) finishClosing(); });
  update();
})();
