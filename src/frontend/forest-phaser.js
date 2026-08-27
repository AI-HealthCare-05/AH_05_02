(() => {
  "use strict";

  if (!window.Phaser || !document.getElementById("phaser-world")) return;

  const STORAGE_KEY = "gandang-carrot-forest-demo-v1";
  const WORLD = { width: 768, height: 512 };
  const directionRows = { down: 0, up: 1, left: 2, right: 3 };
  const premiumPresets = {
    red_bow: { path: "/static/assets/carrot-forest-preset-red-bow-v1.png", rows: 6 },
    cow_hood: { path: "/static/assets/carrot-forest-preset-cow-hood-v1.png", rows: 5 },
    midnight: { path: "/static/assets/carrot-forest-preset-midnight-v1.png", rows: 6 },
    blue_cap: { path: "/static/assets/carrot-forest-preset-blue-cap-v1.png", rows: 6 },
    teal_bob: { path: "/static/assets/carrot-forest-preset-teal-bob-v1.png", rows: 6 },
  };
  const defaultCosmetics = {
    skin: "peach", outfit: "forest", bottom: "cream", shoes: "brown", hair: "soft",
    hat: "none", glasses: "none", face: "calm", accessory: "none",
  };

  function storedState() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; } catch { return {}; }
  }

  function normalizedAvatar(source = {}) {
    return {
      name: source.name || "세준", gender: source.gender === "male" ? "male" : "female",
      preset: premiumPresets[source.preset] ? source.preset : "blue_cap",
      x: Number.isFinite(source.x) ? source.x : 384, y: Number.isFinite(source.y) ? source.y : 352,
      direction: directionRows[source.direction] == null ? "down" : source.direction,
      mounted: Boolean(source.mounted), sitting: Boolean(source.sitting),
      cosmetics: { ...defaultCosmetics, ...(source.cosmetics || {}) },
    };
  }

  class ForestScene extends Phaser.Scene {
    constructor() {
      super("forest-world");
      this.avatar = normalizedAvatar(storedState().avatar);
      this.sceneName = "world";
      this.lastPersist = 0;
      this.forcedDirection = null;
      this.forcedUntil = 0;
    }

    preload() {
      this.load.image("world-bg", "/static/assets/carrot-forest-world-v2.png");
      this.load.image("home-bg", "/static/assets/carrot-forest-home-v1.png");
      this.load.image("garden-bg", "/static/assets/carrot-forest-garden-v1.png");
      Object.entries(premiumPresets).forEach(([key, config]) => this.load.image(`preset-${key}`, config.path));
      this.load.spritesheet("cat-pets", "/static/assets/carrot-forest-cat-pets-v1.png", { frameWidth: 887, frameHeight: 887 });
    }

    create() {
      this.background = this.add.image(WORLD.width / 2, WORLD.height / 2, "world-bg").setDisplaySize(WORLD.width, WORLD.height);
      this.shadow = this.add.ellipse(0, 16, 42, 15, 0x16382a, 0.25);
      this.player = this.add.container(this.avatar.x, this.avatar.y);
      this.player.add(this.shadow);
      this.preparePresetFrames();
      this.premiumAvatar = this.add.image(0, 0, `preset-${this.avatar.preset}`, "r0c0").setOrigin(0.5, 0.82).setDepth(3);
      this.player.add(this.premiumAvatar);
      this.pet = this.add.sprite(39, 12, "cat-pets", 0).setOrigin(0.5, 1).setScale(0.057).setDepth(1);
      this.player.add(this.pet);
      this.nameplate = this.add.text(0, -50, this.avatar.name, {
        fontFamily: "Pretendard, Noto Sans KR, sans-serif", fontSize: "12px", fontStyle: "bold",
        color: "#173528", backgroundColor: "rgba(255,255,255,.92)", padding: { x: 7, y: 3 },
      }).setOrigin(0.5).setStroke("#ffffff", 2);
      this.player.add(this.nameplate);
      this.rebuildAvatar();
      this.keys = this.input.keyboard.addKeys("W,A,S,D,R,Q,C,X,E");
      this.cursors = this.input.keyboard.createCursorKeys();
      this.input.keyboard.on("keydown-Q", () => window.dispatchEvent(new CustomEvent("forest-phaser-interact")));
      this.input.keyboard.on("keydown-C", () => window.dispatchEvent(new CustomEvent("forest-phaser-action", { detail: "chat" })));
      this.input.keyboard.on("keydown-X", () => window.dispatchEvent(new CustomEvent("forest-phaser-action", { detail: "sit" })));
      this.input.keyboard.on("keydown-E", () => window.dispatchEvent(new CustomEvent("forest-phaser-action", { detail: "ride" })));
      this.events.on("shutdown", () => this.detachWindowEvents());
      this.attachWindowEvents();
      document.documentElement.classList.add("phaser-world-ready");
      window.carrotForestPhaserActive = true;
      window.carrotForestPhaserMove = (direction) => this.nudge(direction);
      this.input.once("pointerdown", () => document.getElementById("phaser-world")?.focus());
      this.emitPosition(true);
    }

    preparePresetFrames() {
      Object.entries(premiumPresets).forEach(([preset, config]) => {
        const texture = this.textures.get(`preset-${preset}`);
        const source = texture.getSourceImage();
        const cellWidth = source.width / 4;
        const cellHeight = source.height / config.rows;
        for (let row = 0; row < config.rows; row += 1) {
          for (let column = 0; column < 4; column += 1) {
            const frameName = `r${row}c${column}`;
            if (!texture.has(frameName)) texture.add(frameName, 0, column * cellWidth, row * cellHeight, cellWidth, cellHeight);
          }
        }
      });
    }

    rebuildAvatar() {
      const c = this.avatar.cosmetics;
      this.premiumAvatar?.setTexture(`preset-${this.avatar.preset}`, "r0c0").setDepth(3);
      this.setPremiumFrame(this.avatar.direction, false, 0);
      this.nameplate?.setDepth(30).setText(this.avatar.name);
      const pet = c.pet;
      this.pet?.setVisible(["cat", "blue_eyes_white_cat", "gold_eyes_orange_cat"].includes(pet));
      this.pet?.setFrame(pet === "gold_eyes_orange_cat" ? 1 : 0);
    }

    attachWindowEvents() {
      this.onAvatar = (event) => { this.avatar = normalizedAvatar({ ...this.avatar, ...(event.detail || {}) }); this.rebuildAvatar(); };
      this.onState = (event) => {
        const detail = event.detail || {};
        if (detail.avatar) { this.avatar = normalizedAvatar(detail.avatar); this.player.setPosition(this.avatar.x, this.avatar.y); this.rebuildAvatar(); }
        if (detail.scene) this.setScene(detail.scene);
      };
      window.addEventListener("forest-avatar-updated", this.onAvatar);
      window.addEventListener("forest-state-updated", this.onState);
    }

    detachWindowEvents() {
      window.removeEventListener("forest-avatar-updated", this.onAvatar);
      window.removeEventListener("forest-state-updated", this.onState);
    }

    setScene(sceneName) {
      this.sceneName = ["world", "home", "garden"].includes(sceneName) ? sceneName : "world";
      this.background.setTexture(`${this.sceneName}-bg`).setDisplaySize(WORLD.width, WORLD.height);
    }

    nudge(direction) {
      this.forcedDirection = directionRows[direction] == null ? null : direction;
      this.forcedUntil = performance.now() + 170;
      document.getElementById("phaser-world")?.focus();
    }

    isBlocked(x, y) {
      if (x < 28 || x > WORLD.width - 28 || y < 42 || y > WORLD.height - 32) return true;
      if (this.sceneName === "home") return x < 64 || x > 710 || y < 100 || y > 458;
      if (this.sceneName === "garden") return x < 105 || x > 675 || y < 105 || y > 458;
      return (x > 45 && x < 335 && y > 55 && y < 275) || (x > 465 && x < 735 && y > 45 && y < 255) || (x > 35 && x < 270 && y > 300 && y < 475);
    }

    emitPosition(force = false) {
      const now = performance.now();
      if (!force && now - this.lastPersist < 180) return;
      this.lastPersist = now;
      window.dispatchEvent(new CustomEvent("forest-phaser-position", { detail: { x: this.avatar.x, y: this.avatar.y, direction: this.avatar.direction } }));
    }

    update(time, delta) {
      const inputAllowed = !["INPUT", "SELECT", "TEXTAREA", "BUTTON"].includes(document.activeElement?.tagName);
      let direction = performance.now() < this.forcedUntil ? this.forcedDirection : null;
      if (inputAllowed) {
        if (this.cursors.left.isDown || this.keys.A.isDown) direction = "left";
        else if (this.cursors.right.isDown || this.keys.D.isDown) direction = "right";
        else if (this.cursors.up.isDown || this.keys.W.isDown) direction = "up";
        else if (this.cursors.down.isDown || this.keys.S.isDown) direction = "down";
      }
      const running = inputAllowed && this.keys.R.isDown;
      if (!direction) {
        this.setPremiumFrame(this.avatar.direction, false, time);
        return;
      }
      const speed = this.avatar.mounted ? 185 : running ? 150 : 92;
      const distance = speed * Math.min(delta, 40) / 1000;
      const vector = { left: [-distance, 0], right: [distance, 0], up: [0, -distance], down: [0, distance] }[direction];
      const nextX = this.avatar.x + vector[0];
      const nextY = this.avatar.y + vector[1];
      this.avatar.direction = direction;
      if (!this.isBlocked(nextX, nextY)) {
        this.avatar.x = nextX; this.avatar.y = nextY;
        this.player.setPosition(nextX, nextY).setDepth(nextY);
      }
      this.setPremiumFrame(direction, true, time, running);
      this.emitPosition();
    }

    setPremiumFrame(direction, moving, time, running = false) {
      if (!this.premiumAvatar) return;
      const source = this.premiumAvatar.texture.getSourceImage();
      const cellWidth = source.width / 4;
      const rows = premiumPresets[this.avatar.preset].rows;
      const cellHeight = source.height / rows;
      const directionColumn = { down: 0, up: 1, left: 2, right: 3 }[direction] || 0;
      const row = this.avatar.mounted ? (moving && rows === 6 ? 5 : 4) : directionRows[direction];
      const rate = running || this.avatar.mounted ? 90 : 140;
      const column = this.avatar.mounted ? directionColumn : moving ? Math.floor(time / rate) % 4 : 0;
      this.premiumAvatar.setFrame(`r${row}c${column}`);
      this.premiumAvatar.setScale(138 / cellHeight);
    }
  }

  const game = new Phaser.Game({
    type: Phaser.AUTO,
    parent: "phaser-world",
    width: WORLD.width,
    height: WORLD.height,
    backgroundColor: "#78b96a",
    pixelArt: true,
    roundPixels: true,
    render: { antialias: false, pixelArt: true, roundPixels: true },
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
    scene: ForestScene,
  });
  window.carrotForestPhaserGame = game;
})();
