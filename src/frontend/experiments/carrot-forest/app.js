const STORAGE_KEY = "gandang-carrot-forest-demo-v1";

const defaultState = {
  carrots: 180,
  questsCompleted: 2,
  groupCompleted: 11,
  rewardOpened: false,
  activeCategory: "outfit",
  avatar: { outfit: "carrot", hair: "brown", accessory: "sprout" },
  inventory: ["carrot", "forest", "brown", "black", "sprout", "glasses"],
  decorations: [],
};

const catalog = {
  outfit: [
    { id: "carrot", name: "당근 탐험복", icon: "🧡", color: "#ef7f3b", note: "기본" },
    { id: "forest", name: "숲 지킴이", icon: "🌲", color: "#2e7550", note: "보유" },
    { id: "sky", name: "구름 산책복", icon: "☁️", color: "#62a9d8", note: "35 🥕", cost: 35 },
    { id: "sunset", name: "노을 캠핑복", icon: "🌅", color: "#bd5f70", note: "50 🥕", cost: 50 },
    { id: "lemon", name: "레몬 피크닉", icon: "🍋", color: "#e4bd3d", note: "잠김", locked: true },
    { id: "legend", name: "전설의 숲옷", icon: "✨", color: "#7050a5", note: "4주 보상", locked: true },
  ],
  hair: [
    { id: "brown", name: "밤색 단정컷", icon: "🤎", color: "#40342e", note: "기본" },
    { id: "black", name: "검정 웨이브", icon: "🖤", color: "#222a27", note: "보유" },
    { id: "orange", name: "당근 오렌지", icon: "🧡", color: "#a94e2e", note: "25 🥕", cost: 25 },
    { id: "silver", name: "은빛 숲결", icon: "🤍", color: "#a8aaa6", note: "30 🥕", cost: 30 },
  ],
  accessory: [
    { id: "sprout", name: "새싹 핀", icon: "🌱", note: "기본" },
    { id: "glasses", name: "동그란 안경", icon: "👓", note: "보유" },
    { id: "beret", name: "새싹 베레모", icon: "🧢", note: "보물상자", reward: true },
    { id: "rabbit", name: "토끼 친구", icon: "🐰", note: "45 🥕", cost: 45 },
    { id: "star", name: "별빛 오라", icon: "⭐", note: "4주 보상", locked: true },
  ],
};

let state = loadState();
let toastTimer;

function loadState() {
  try {
    return { ...defaultState, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") };
  } catch {
    return structuredClone(defaultState);
  }
}

function persist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function showToast(message) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.hidden = true; }, 2500);
}

function switchTab(name) {
  document.querySelectorAll(".tab").forEach((tab) => {
    const active = tab.dataset.tab === name;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    const active = panel.dataset.panel === name;
    panel.classList.toggle("active", active);
    panel.hidden = !active;
  });
}

function updateSummary() {
  document.querySelector("#carrot-balance").textContent = state.carrots;
  document.querySelector("#closet-balance").textContent = state.carrots;
  document.querySelector("#my-member-count").textContent = state.questsCompleted;
  document.querySelector("#group-count").textContent = `${state.groupCompleted}/15`;
  document.querySelector("#group-progress").style.width = `${Math.min(100, state.groupCompleted / 15 * 100)}%`;
  const remaining = Math.max(0, 15 - state.groupCompleted);
  document.querySelector("#group-message").textContent = remaining
    ? `${remaining}개만 더 완료하면 모두에게 보물상자가 열려요.`
    : "오늘의 공동 목표를 달성했어요! 숲이 한 단계 성장했습니다.";
  const memberStatus = document.querySelector("#my-member-status");
  memberStatus.textContent = state.questsCompleted === 3 ? "완료" : "진행 중";
  memberStatus.classList.toggle("complete", state.questsCompleted === 3);
}

function applyAvatar(target) {
  const outfit = catalog.outfit.find((item) => item.id === state.avatar.outfit);
  const hair = catalog.hair.find((item) => item.id === state.avatar.hair);
  const accessory = catalog.accessory.find((item) => item.id === state.avatar.accessory);
  target.style.setProperty("--outfit", outfit?.color || "#ef7f3b");
  target.style.setProperty("--hair", hair?.color || "#40342e");
  target.querySelector(".avatar-accessory").textContent = accessory?.icon || "🌱";
}

function applyAllAvatars() {
  applyAvatar(document.querySelector("#avatar-main"));
  applyAvatar(document.querySelector("#avatar-preview"));
}

function renderInventory() {
  const grid = document.querySelector("#inventory-grid");
  grid.replaceChildren();
  catalog[state.activeCategory].forEach((item) => {
    const owned = state.inventory.includes(item.id);
    const selected = state.avatar[state.activeCategory] === item.id;
    const button = document.createElement("button");
    button.type = "button";
    button.className = `item-card${selected ? " selected" : ""}${item.locked ? " locked" : ""}`;
    button.dataset.itemId = item.id;
    button.innerHTML = `<span>${item.icon}</span><strong>${item.name}</strong><small>${owned ? "보유 중" : item.note}</small>${selected ? "<em>착용 중</em>" : ""}`;
    button.addEventListener("click", () => selectItem(item));
    grid.append(button);
  });
}

function selectItem(item) {
  if (item.locked) {
    showToast("아직 잠긴 아이템이에요. 주간 퀘스트에서 만나요!");
    return;
  }
  if (!state.inventory.includes(item.id)) {
    if (item.reward) {
      showToast("오늘의 당근 보물상자에서 얻을 수 있어요.");
      return;
    }
    if (state.carrots < item.cost) {
      showToast("당근이 부족해요. 퀘스트를 완료해 주세요.");
      return;
    }
    state.carrots -= item.cost;
    state.inventory.push(item.id);
    showToast(`${item.name} 아이템을 획득했어요!`);
  }
  state.avatar[state.activeCategory] = item.id;
  persist();
  updateSummary();
  applyAllAvatars();
  renderInventory();
}

function renderDecorations() {
  const layer = document.querySelector("#placed-items");
  layer.replaceChildren();
  const positions = [
    [18, 67], [69, 69], [78, 54], [34, 72], [57, 62], [7, 77],
  ];
  state.decorations.forEach((icon, index) => {
    const element = document.createElement("span");
    element.className = "placed-item";
    element.textContent = icon;
    const [left, top] = positions[index % positions.length];
    element.style.left = `${left}%`;
    element.style.top = `${top}%`;
    layer.append(element);
  });
}

function completeQuest() {
  if (state.questsCompleted === 3) return;
  state.questsCompleted = 3;
  state.groupCompleted = Math.min(15, state.groupCompleted + 1);
  state.carrots += 20;
  document.querySelector("#pending-quest").classList.add("complete");
  const rewardButton = document.querySelector("#open-reward");
  rewardButton.disabled = state.rewardOpened;
  rewardButton.textContent = state.rewardOpened ? "오늘 보상 수령 완료" : "당근 보물상자 열기";
  document.querySelector("#reward-copy").textContent = state.rewardOpened
    ? "오늘의 보상을 이미 받았어요. 내일 다시 만나요!"
    : "오늘의 퀘스트를 모두 완료했어요. 보물상자가 열렸습니다!";
  persist();
  updateSummary();
  showToast("퀘스트 완료! 당근 20개를 받았어요.");
}

function openReward() {
  if (state.rewardOpened || state.questsCompleted < 3) return;
  state.rewardOpened = true;
  if (!state.inventory.includes("beret")) state.inventory.push("beret");
  persist();
  document.querySelector("#open-reward").disabled = true;
  document.querySelector("#open-reward").textContent = "오늘 보상 수령 완료";
  document.querySelector("#reward-copy").textContent = "새싹 베레모가 옷장에 추가됐어요!";
  document.querySelector("#reward-dialog").showModal();
  renderInventory();
}

function initRewardState() {
  const quest = document.querySelector("#vegetable-quest");
  if (state.questsCompleted === 3) {
    quest.checked = true;
    quest.disabled = true;
    document.querySelector("#pending-quest").classList.add("complete");
  }
  const button = document.querySelector("#open-reward");
  button.disabled = state.questsCompleted < 3 || state.rewardOpened;
  button.textContent = state.rewardOpened ? "오늘 보상 수령 완료" : state.questsCompleted === 3 ? "당근 보물상자 열기" : "퀘스트를 먼저 완료해 주세요";
}

function bindEvents() {
  document.querySelectorAll(".tab").forEach((button) => button.addEventListener("click", () => switchTab(button.dataset.tab)));
  document.querySelectorAll("[data-open-tab]").forEach((button) => button.addEventListener("click", () => switchTab(button.dataset.openTab)));
  document.querySelector("#vegetable-quest").addEventListener("change", completeQuest);
  document.querySelector("#open-reward").addEventListener("click", openReward);
  document.querySelector("#open-decorations").addEventListener("click", () => document.querySelector("#decoration-dialog").showModal());
  document.querySelectorAll("[data-close-dialog]").forEach((button) => button.addEventListener("click", () => button.closest("dialog").close()));
  document.querySelectorAll(".inventory-tab").forEach((button) => button.addEventListener("click", () => {
    state.activeCategory = button.dataset.category;
    document.querySelectorAll(".inventory-tab").forEach((tab) => tab.classList.toggle("active", tab === button));
    renderInventory();
  }));
  document.querySelectorAll("[data-decoration]").forEach((button) => button.addEventListener("click", () => {
    const cost = Number(button.dataset.cost);
    const message = document.querySelector("#decoration-message");
    if (state.carrots < cost) {
      message.textContent = "당근이 부족해요. 퀘스트를 더 완료해 주세요.";
      return;
    }
    state.carrots -= cost;
    state.decorations.push(button.dataset.decoration);
    persist();
    updateSummary();
    renderDecorations();
    message.textContent = `${button.textContent.trim()} 오브젝트를 숲에 배치했어요!`;
  }));
  document.querySelector("#save-avatar").addEventListener("click", () => {
    persist();
    showToast("새 코디를 저장했어요. 우리 숲에도 반영됐습니다!");
  });
  document.querySelector("#reset-demo").addEventListener("click", () => {
    localStorage.removeItem(STORAGE_KEY);
    window.location.reload();
  });
}

updateSummary();
applyAllAvatars();
renderInventory();
renderDecorations();
initRewardState();
bindEvents();
