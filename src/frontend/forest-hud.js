/* Fixed-size forest viewport, camera zoom, and lightweight in-game HUD controls. */
(() => {
  "use strict";
  const NAME_KEY = "carrot-forest-name-v1";
  const DEFAULT_NAME = "우리의 작은 숲";
  const NATIVE_WIDTH = 768;
  const NATIVE_HEIGHT = 512;
  const MAX_FRAME_SCALE = 2;
  const MIN_ZOOM = .5, MAX_ZOOM = 2, ZOOM_STEP = .25;
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
    // Double the former frame's width, height and diagonal when space allows.
    // Fit both axes up to 1536x1024; camera +/- never changes the DOM frame.
    const fittedScale = Math.min(MAX_FRAME_SCALE, area.clientWidth / NATIVE_WIDTH, area.clientHeight / NATIVE_HEIGHT);
    const width = NATIVE_WIDTH * fittedScale;
    const height = width * NATIVE_HEIGHT / NATIVE_WIDTH;
    const widthStyle = `${width}px`, heightStyle = `${height}px`;
    const changed = frame.style.width !== widthStyle || frame.style.height !== heightStyle;
    frame.style.width = widthStyle;
    frame.style.height = heightStyle;
    if (changed) window.carrotForestPhaserGame?.scale.refresh();
  }

  function updateZoomControls() {
    const level = byId("zoom-level");
    if (level) {
      level.textContent = `${Math.round(zoom * 100)}%`;
      level.title = `카메라 확대 ${Math.round(zoom * 100)}%`;
    }
    if (byId("zoom-out")) byId("zoom-out").disabled = zoom <= MIN_ZOOM;
    if (byId("zoom-in")) byId("zoom-in").disabled = zoom >= MAX_ZOOM;
  }

  function setZoom(value) {
    const requested = Number(value);
    if (!Number.isFinite(requested)) return zoom;
    const next = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.round(requested / ZOOM_STEP) * ZOOM_STEP));
    if (next === zoom) return zoom;
    zoom = next;
    updateZoomControls();
    window.dispatchEvent(new CustomEvent("forest-camera-zoom", { detail: { zoom } }));
    return zoom;
  }

  function resetZoom() { return setZoom(1); }

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
  byId("zoom-in")?.addEventListener("click", () => setZoom(zoom + ZOOM_STEP));
  byId("zoom-out")?.addEventListener("click", () => setZoom(zoom - ZOOM_STEP));
  function updateUiToggle() {
    const button = byId("ui-toggle");
    if (!button) return;
    button.textContent = uiHidden ? "UI 보이기(0)" : "UI 숨기기(0)";
    button.setAttribute("aria-pressed", String(uiHidden));
  }
  byId("ui-toggle")?.addEventListener("click", () => {
    uiHidden = !uiHidden;
    document.body.classList.toggle("forest-ui-hidden", uiHidden);
    updateUiToggle();
    if (uiHidden) {
      closeNameEditor();
      window.dispatchEvent(new CustomEvent("forest-controls-hidden"));
    }
    requestAnimationFrame(fitGame);
  });

  function setupDisclosure(buttonId, contentId, label, releasesControls, shortcut = "") {
    const button = byId(buttonId), content = byId(contentId);
    if (!button || !content) return;
    const update = () => {
      button.textContent = `${label} ${content.hidden ? "보이기" : "숨기기"}${shortcut}`;
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
  setupDisclosure("controls-toggle", "controls-content", "버튼", true, "(8)");
  setupDisclosure("objects-toggle", "placed-list", "오브젝트", false);
  if (byId("reset-position")) byId("reset-position").textContent = "초기화(9)";

  const shortcutButtons = { "8": "controls-toggle", "9": "reset-position", "0": "ui-toggle" };
  function isEditing(target) {
    return Boolean(target && (
      ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) || target.isContentEditable ||
      target.closest?.('form, input, textarea, select, [contenteditable]:not([contenteditable="false"]), [role="textbox"]')
    ));
  }
  window.addEventListener("keydown", event => {
    const buttonId = shortcutButtons[event.key];
    if (!buttonId || event.defaultPrevented || event.repeat || event.isComposing ||
      event.altKey || event.ctrlKey || event.metaKey || event.shiftKey ||
      isEditing(event.target) || isEditing(document.activeElement) ||
      document.querySelector('dialog[open], [aria-modal="true"]:not([hidden])')) return;
    const button = byId(buttonId);
    if (!button || button.disabled) return;
    event.preventDefault();
    // Route all input through one click handler; Enter/Space retain native button behavior.
    button.click();
  });

  window.ForestHud = {
    get forestName() { return forestName; },
    get zoom() { return zoom; },
    setForestName, fitGame, closeNameEditor, setZoom, resetZoom,
  };
  let resizePending = false;
  function scheduleFit() {
    if (resizePending) return;
    resizePending = true;
    requestAnimationFrame(() => { resizePending = false; fitGame(); });
  }
  window.addEventListener("resize", scheduleFit);
  if (area && typeof ResizeObserver !== "undefined") new ResizeObserver(scheduleFit).observe(area);
  updateZoomControls();
  updateUiToggle();
  fitGame();
  window.dispatchEvent(new CustomEvent("forest-camera-zoom", { detail: { zoom } }));
})();
