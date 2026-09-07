/* Native-size forest viewport and lightweight in-game HUD controls. */
(() => {
  "use strict";
  const NAME_KEY = "carrot-forest-name-v1";
  const DEFAULT_NAME = "우리의 작은 숲";
  const NATIVE_WIDTH = 768;
  const NATIVE_HEIGHT = 512;
  const MIN_ZOOM = .25, MAX_ZOOM = 1.5, ZOOM_EPSILON = 1e-6;
  const byId = id => document.getElementById(id);
  const cleanName = value => Array.from(String(value ?? "").replace(/[\u0000-\u001f\u007f]+/g, " ").replace(/\s+/g, " ").trim()).slice(0, 24).join("");
  let forestName = DEFAULT_NAME;
  try { forestName = cleanName(localStorage.getItem(NAME_KEY)) || DEFAULT_NAME; } catch { /* Storage may be unavailable in private browsing. */ }
  let zoom = 1;
  let uiHidden = false;
  const area = document.querySelector(".canvas-workarea");
  const frame = document.querySelector(".canvas-frame");
  const form = byId("forest-name-form");
  const input = byId("forest-name-input");
  const edit = byId("edit-forest-name");

  function setForestName(value) {
    const next = cleanName(value);
    if (!next) return false;
    forestName = next;
    try { localStorage.setItem(NAME_KEY, next); } catch { /* Keep the name for this visit even without storage. */ }
    window.dispatchEvent(new CustomEvent("forest-name-updated", { detail: { name: next } }));
    return true;
  }

  function fitGame() {
    if (!area || !frame || area.clientWidth <= 0 || area.clientHeight <= 0) return;
    const availableZoom = Math.min(MAX_ZOOM, area.clientWidth / NATIVE_WIDTH, area.clientHeight / NATIVE_HEIGHT);
    const displayedZoom = Math.min(zoom, availableZoom);
    const width = NATIVE_WIDTH * displayedZoom;
    const height = width * NATIVE_HEIGHT / NATIVE_WIDTH;
    const widthStyle = `${width}px`, heightStyle = `${height}px`;
    const changed = frame.style.width !== widthStyle || frame.style.height !== heightStyle;
    frame.style.width = widthStyle;
    frame.style.height = heightStyle;
    const level = byId("zoom-level");
    if (level) {
      level.textContent = `${Math.round(width / NATIVE_WIDTH * 100)}%`;
      level.title = `표시 크기 ${Math.round(width / NATIVE_WIDTH * 100)}% · 설정 ${Math.round(zoom * 100)}%`;
    }
    if (byId("zoom-out")) byId("zoom-out").disabled = displayedZoom <= MIN_ZOOM + ZOOM_EPSILON;
    if (byId("zoom-in")) byId("zoom-in").disabled = displayedZoom >= availableZoom - ZOOM_EPSILON;
    if (changed) window.carrotForestPhaserGame?.scale.refresh();
  }

  function changeZoom(delta) {
    if (!area || area.clientWidth <= 0 || area.clientHeight <= 0) return;
    const availableZoom = Math.min(MAX_ZOOM, area.clientWidth / NATIVE_WIDTH, area.clientHeight / NATIVE_HEIGHT);
    const displayedZoom = Math.min(zoom, availableZoom);
    if (delta > 0) {
      if (displayedZoom >= availableZoom - ZOOM_EPSILON) return;
      zoom = Math.min(MAX_ZOOM, (Math.floor((displayedZoom + ZOOM_EPSILON) * 4) + 1) / 4);
    } else {
      if (displayedZoom <= MIN_ZOOM + ZOOM_EPSILON) return;
      zoom = Math.max(MIN_ZOOM, (Math.ceil((displayedZoom - ZOOM_EPSILON) * 4) - 1) / 4);
    }
    fitGame();
  }

  function closeNameEditor() {
    if (form) form.hidden = true;
    if (edit) edit.setAttribute("aria-expanded", "false");
    if (input) input.setCustomValidity("");
  }

  edit?.addEventListener("click", () => {
    if (!form || !input) return;
    input.value = forestName;
    input.setCustomValidity("");
    form.hidden = false;
    edit.setAttribute("aria-expanded", "true");
    input.focus({ preventScroll: true });
    input.select();
  });
  input?.addEventListener("input", () => input.setCustomValidity(""));
  form?.addEventListener("submit", event => {
    event.preventDefault();
    if (!setForestName(input?.value)) {
      input?.setCustomValidity("숲 이름을 입력해주세요.");
      input?.reportValidity();
      return;
    }
    closeNameEditor();
    edit?.focus({ preventScroll: true });
  });
  form?.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    event.preventDefault();
    event.stopPropagation();
    closeNameEditor();
    edit?.focus({ preventScroll: true });
  });
  byId("cancel-forest-name")?.addEventListener("click", () => {
    closeNameEditor();
    edit?.focus({ preventScroll: true });
  });
  byId("zoom-in")?.addEventListener("click", () => changeZoom(.25));
  byId("zoom-out")?.addEventListener("click", () => changeZoom(-.25));
  byId("ui-toggle")?.addEventListener("click", () => {
    uiHidden = !uiHidden;
    document.body.classList.toggle("forest-ui-hidden", uiHidden);
    const button = byId("ui-toggle");
    button.textContent = uiHidden ? "UI 보이기" : "UI 숨기기";
    button.setAttribute("aria-pressed", String(uiHidden));
    if (uiHidden) {
      closeNameEditor();
      window.dispatchEvent(new CustomEvent("forest-controls-hidden"));
    }
    requestAnimationFrame(fitGame);
  });

  function setupDisclosure(buttonId, contentId, label, releasesControls) {
    const button = byId(buttonId), content = byId(contentId);
    if (!button || !content) return;
    const update = () => {
      button.textContent = `${label} ${content.hidden ? "보이기" : "숨기기"}`;
      button.setAttribute("aria-expanded", String(!content.hidden));
    };
    update();
    button.addEventListener("click", () => {
      content.hidden = !content.hidden;
      update();
      if (content.hidden && releasesControls) window.dispatchEvent(new CustomEvent("forest-controls-hidden"));
      requestAnimationFrame(fitGame);
    });
  }
  setupDisclosure("controls-toggle", "controls-content", "조작 버튼", true);
  setupDisclosure("objects-toggle", "placed-list", "오브젝트", false);

  window.ForestHud = {
    get forestName() { return forestName; },
    get zoom() { return zoom; },
    setForestName, fitGame, closeNameEditor,
  };
  let resizePending = false;
  function scheduleFit() {
    if (resizePending) return;
    resizePending = true;
    requestAnimationFrame(() => { resizePending = false; fitGame(); });
  }
  window.addEventListener("resize", scheduleFit);
  if (area && typeof ResizeObserver !== "undefined") new ResizeObserver(scheduleFit).observe(area);
  fitGame();
})();
