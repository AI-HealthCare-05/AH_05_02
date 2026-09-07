/* Seoul clock, informational weather and real game fullscreen. */
(() => {
  "use strict";
  const KEY = "gandang-carrot-forest-atmosphere-v1";
  const HOUR = 3600000;
  function seoulTime(now = Date.now()) {
    const date = new Date(now + 9 * HOUR);
    return { hour: date.getUTCHours(), minute: date.getUTCMinutes(), second: date.getUTCSeconds(), key: Math.floor(now / HOUR) };
  }
  function strength(hour) {
    if (hour >= 20 || hour < 5) return .42;
    if (hour === 19 || hour === 5) return .3;
    if (hour === 18 || hour === 6) return .16;
    return 0;
  }
  function currentHour() {
    const raw = new URLSearchParams(location.search).get("hour");
    const forced = raw === null ? NaN : Number(raw);
    return Number.isFinite(forced) && forced >= 0 && forced < 24 ? Math.floor(forced) : seoulTime().hour;
  }
  function phase(hour) {
    if (hour < 5 || hour >= 20) return ["☾", "밤이 찾아왔어요", "등불 아래에서 쉬어가세요"];
    if (hour < 7) return ["☀", "아침이 밝아오고 있어요", "숲이 천천히 밝아집니다"];
    if (hour < 18) return ["☀", "환한 낮이 시작됐어요", "오늘도 숲에서 함께해요"];
    return ["☀", "저녁이 찾아왔어요", "숲이 천천히 어두워집니다"];
  }
  function hourlyEvent(previous, now, enabled, visible, lastHour) {
    const t = seoulTime(now);
    return enabled && visible && previous !== null && now > previous && now - previous < 70000
      && seoulTime(previous).key !== t.key && t.minute === 0 && t.second < 15 && t.key > lastHour;
  }
  function weatherLabel(code) {
    if (code === 0) return ["☀", "맑음"];
    if (code <= 2 && code >= 1) return ["⛅", "구름 조금"];
    if (code === 3) return ["☁", "흐림"];
    if ([45, 48].includes(code)) return ["≋", "안개"];
    if ([51, 53, 55, 56, 57].includes(code)) return ["☂", "이슬비"];
    if ([61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return ["☂", "비"];
    if ([71, 73, 75, 77, 85, 86].includes(code)) return ["❄", "눈"];
    if ([95, 96, 99].includes(code)) return ["ϟ", "뇌우"];
    return ["◇", "날씨 정보"];
  }
  window.ForestAtmosphere = { seoulTime, strength, currentHour, phase, hourlyEvent, weatherLabel };
  const clock = document.getElementById("forest-clock");
  if (!clock) return;
  const toast = document.getElementById("forest-time-toast");
  let toastTimer, previous = null, lastHour = -Infinity, previousHour = currentHour();
  function notify(icon, title, description) {
    clearTimeout(toastTimer);
    toast.querySelector(".time-toast-icon").textContent = icon;
    toast.querySelector("strong").textContent = title;
    toast.querySelector("small").textContent = description;
    toast.hidden = false;
    toast.classList.remove("is-announcing");
    requestAnimationFrame(() => toast.classList.add("is-announcing"));
    toastTimer = setTimeout(() => { toast.hidden = true; }, 6000);
  }
  function tick() {
    const now = Date.now(), t = seoulTime(now), hour = currentHour();
    const label = `${String(hour).padStart(2, "0")}:${String(t.minute).padStart(2, "0")}`;
    clock.textContent = label;
    clock.title = "한국 표준시 (Asia/Seoul)";
    const enabled = localStorage.getItem(KEY) !== "off", visible = !document.hidden;
    const chime = hourlyEvent(previous, now, enabled, visible, lastHour);
    if (chime) {
      lastHour = t.key;
      window.dispatchEvent(new CustomEvent("forest-hour-chime"));
    }
    if (enabled && visible && previous !== null && strength(previousHour) !== strength(hour)) {
      const [icon, title, subtitle] = phase(hour);
      notify(icon, title, `${label} · ${subtitle}${chime ? " · 정각 종소리" : ""}`);
      window.dispatchEvent(new CustomEvent("forest-time-changed"));
    } else if (chime) notify("🔔", `${label} · 숲의 종이 울립니다`, "새로운 한 시간이 시작됐어요");
    previous = now;
    previousHour = hour;
  }
  window.addEventListener("forest-atmosphere-updated", () => {
    previous = null;
    if (localStorage.getItem(KEY) === "off") toast.hidden = true;
    tick();
  });
  document.addEventListener("visibilitychange", () => { previous = null; tick(); });
  tick();
  setInterval(tick, 1000);

  const weather = document.getElementById("forest-weather-value");
  const updated = document.getElementById("forest-weather-updated");
  let busy = false;
  async function refreshWeather() {
    if (busy || document.hidden) return;
    busy = true;
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch("/api/v1/forest/weather", { signal: controller.signal, cache: "no-store" });
      if (!response.ok) throw new Error("weather unavailable");
      const data = await response.json();
      if (!Number.isFinite(data.temperature) || !Number.isInteger(data.code)) throw new Error("invalid weather");
      const [icon, label] = weatherLabel(data.code);
      weather.textContent = `${icon} ${label} ${Math.round(data.temperature)}°C`;
      updated.textContent = `인근 모델 날씨 · ${data.stale ? "이전 정보 · " : ""}${data.observedAt.replace("T", " ")} 기준 · 10분마다 갱신`;
    } catch {
      weather.textContent = "날씨 연결 대기";
      updated.textContent = "날씨를 불러오지 못했어요 · 잠시 후 다시 확인합니다";
    } finally { clearTimeout(timeout); busy = false; }
  }
  refreshWeather();
  setInterval(refreshWeather, 600000);
  window.addEventListener("online", refreshWeather);
  document.addEventListener("visibilitychange", refreshWeather);

  const stage = document.getElementById("world-stage"), zoom = document.getElementById("zoom-toggle");
  let fallback = false;
  function fitGame() {
    const active = document.fullscreenElement === stage || fallback;
    stage.classList.toggle("game-fullscreen", active);
    stage.dataset.fullscreenMode = fallback ? "window" : active ? "native" : "off";
    zoom.textContent = active ? "전체화면 나가기" : "확대 보기";
    zoom.setAttribute("aria-pressed", String(active));
    const frame = stage.querySelector(".canvas-frame");
    if (active) {
      const area = stage.querySelector(".canvas-workarea");
      frame.style.width = `${Math.max(0, Math.min(area.clientWidth - 16, (area.clientHeight - 16) * 1.5))}px`;
    } else frame.style.removeProperty("width");
    window.carrotForestPhaserGame?.scale.refresh();
  }
  zoom.addEventListener("click", async () => {
    if (fallback) { fallback = false; fitGame(); return; }
    if (document.fullscreenElement === stage) { await document.exitFullscreen(); return; }
    try {
      if (!stage.requestFullscreen) throw new Error("unsupported");
      await stage.requestFullscreen();
    } catch {
      fallback = true;
      notify("⛶", "창 전체 보기", "이 브라우저는 전체화면을 지원하지 않아요 · Esc로 닫기");
    }
    fitGame();
    document.getElementById("phaser-world").focus({ preventScroll: true });
  });
  document.addEventListener("fullscreenchange", fitGame);
  document.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    if (fallback) { fallback = false; fitGame(); }
    else if (document.fullscreenElement === stage) document.exitFullscreen().catch(() => {});
  });
  window.addEventListener("resize", fitGame);
  new ResizeObserver(fitGame).observe(stage.querySelector(".canvas-workarea"));
})();
