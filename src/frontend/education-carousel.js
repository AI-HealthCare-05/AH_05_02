/* Independent vanilla-JS interaction inspired by Originkit's public Magnetic Carousel preview. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.EducationCarousel = api;
})(typeof window === "undefined" ? globalThis : window, function () {
  "use strict";
  function proximity(distance, range = 240) {
    if (!Number.isFinite(distance) || !Number.isFinite(range) || range <= 0) return 0;
    const t = Math.max(0, 1 - Math.abs(distance) / range);
    return t * t * (3 - 2 * t);
  }
  function nextIndex(current, direction, count) {
    if (count <= 0) return -1;
    if (current < 0) return direction < 0 ? count - 1 : 0;
    return Math.max(0, Math.min(count - 1, current + direction));
  }
  function mount(root, options = {}) {
    if (!root) return null;
    const list = root.querySelector(options.listSelector || "#education-list");
    const controls = root.querySelector(".education-carousel-controls");
    const status = root.querySelector(options.statusSelector || "#education-carousel-status");
    const previous = root.querySelector("[data-education-prev]");
    const next = root.querySelector("[data-education-next]");
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");
    let cards = [], openId = null, frame = 0, pointerX = null;
    const id = card => card.dataset.contentId;
    function resetMagnets() {
      if (frame) window.cancelAnimationFrame(frame);
      frame = 0;
      pointerX = null;
      cards.forEach(card => card.style.setProperty("--magnet", "0"));
    }
    function update() {
      list.classList.toggle("has-open", openId !== null && !options.onOpen);
      cards.forEach(card => {
        const active = id(card) === openId;
        card.classList.toggle("is-open", active && !options.onOpen);
        card.classList.toggle("is-selected", active);
        if (!options.onOpen) card.querySelector(".education-card-toggle").setAttribute("aria-expanded", String(active));
        const details = card.querySelector(".education-card-details");
        if (details) details.hidden = !active || Boolean(options.onOpen);
      });
      const index = cards.findIndex(card => id(card) === openId);
      previous.disabled = cards.length < 2 || index === 0;
      next.disabled = cards.length < 2 || index === cards.length - 1;
      controls.hidden = cards.length === 0;
      status.textContent = index < 0 ? `총 ${cards.length}개 · ${options.itemLabel ? `${options.itemLabel}을` : "주차를"} 선택해 주세요` : `${index + 1} / ${cards.length} · ${options.getLabel ? options.getLabel(cards[index]) : `${cards[index].dataset.week}주차`} 선택`;
    }
    function reveal(card, focus = false) {
      if (!card) return;
      resetMagnets();
      openId = id(card);
      update();
      if (focus) card.querySelector(".education-card-toggle").focus({ preventScroll: true });
      card.scrollIntoView({ behavior: reduce.matches ? "auto" : "smooth", block: "nearest", inline: "center" });
    }
    function close(focus = false) {
      const card = cards.find(card => id(card) === openId);
      openId = null;
      resetMagnets();
      update();
      if (focus) card?.querySelector(".education-card-toggle").focus({ preventScroll: true });
    }
    function move(direction) {
      const index = nextIndex(cards.findIndex(card => id(card) === openId), direction, cards.length);
      reveal(cards[index], true);
    }
    root.addEventListener("click", event => {
      const toggle = event.target.closest(".education-card-toggle");
      if (toggle) {
        const card = toggle.closest(".education-overview-card");
        if (options.onOpen) { reveal(card); options.onOpen(id(card)); }
        else if (id(card) === openId) close(true);
        else reveal(card);
      } else if (event.target.closest("[data-education-prev]")) move(-1);
      else if (event.target.closest("[data-education-next]")) move(1);
      else if (event.target === list) close();
    });
    root.addEventListener("keydown", event => {
      if (event.key === "Escape" && openId !== null) {
        event.preventDefault(); close(true); return;
      }
      const toggle = event.target.closest(".education-card-toggle");
      if (!toggle) return;
      const index = cards.indexOf(toggle.closest(".education-overview-card"));
      let target;
      if (event.key === "ArrowRight") target = nextIndex(index, 1, cards.length);
      else if (event.key === "ArrowLeft") target = nextIndex(index, -1, cards.length);
      else if (event.key === "Home") target = 0;
      else if (event.key === "End") target = cards.length - 1;
      else return;
      event.preventDefault(); reveal(cards[target], true);
    });
    list.addEventListener("pointermove", event => {
      if (openId !== null || reduce.matches || !finePointer.matches || event.pointerType === "touch") return;
      pointerX = event.clientX;
      if (frame) return;
      frame = window.requestAnimationFrame(() => {
        frame = 0;
        const positions = cards.map(card => card.getBoundingClientRect());
        positions.forEach((rect, index) => cards[index].style.setProperty("--magnet", proximity(pointerX - rect.left - rect.width / 2).toFixed(3)));
      });
    });
    list.addEventListener("pointerleave", resetMagnets);
    list.addEventListener("pointercancel", resetMagnets);
    reduce.addEventListener("change", resetMagnets);
    function refresh() {
      resetMagnets();
      cards = [...list.querySelectorAll(".education-overview-card")];
      if (!cards.some(card => id(card) === openId)) openId = null;
      update();
    }
    refresh();
    return { refresh, close };
  }
  return { proximity, nextIndex, mount };
});
