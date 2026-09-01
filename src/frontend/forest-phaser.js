(() => {
  "use strict";

  if (!window.Phaser || !document.getElementById("phaser-world")) return;

  const STORAGE_KEY = "gandang-carrot-forest-demo-v1";
  const WORLD = { width: 768, height: 512 };
  const AVATAR_RENDER_SCALE = 0.43;
  const NAMEPLATE_Y = -126;
  const directionRows = { down: 0, up: 1, left: 2, right: 3 };
  const animatedObjectRows = { duck_float: 0, animated_fountain: 1, firefly_lantern: 2, garden_pinwheel: 3 };
  const interactiveObjectTypes = {
    reward_cow: "cow", campfire: "fire", lantern: "light", firefly_lantern: "light", light_tent: "light",
  };
  const storageObjectCodes = [
    "tent", "light_tent", "picnic_table", "bbq_table", "chair_green",
    "chair_red", "picnic_blanket", "pond", "lantern", "fence",
    "flower_cart", "flower_pot", "mushroom", "bench", "campfire",
    "mailbox", "scarecrow", "carrot_crate", "watering_can", "wheelbarrow",
  ];
  const storageObjectIndex = Object.fromEntries(storageObjectCodes.map((code, index) => [code, index]));
  const premiumPresets = {
    red_bow: { path: "/static/assets/carrot-forest-avatar-red_bow-normalized-v2.png", rows: 6 },
    cow_hood: { path: "/static/assets/carrot-forest-avatar-cow_hood-normalized-v2.png", rows: 5 },
    midnight: { path: "/static/assets/carrot-forest-avatar-midnight-normalized-v2.png", rows: 6 },
    blue_cap: { path: "/static/assets/carrot-forest-avatar-blue_cap-normalized-v2.png", rows: 6 },
    teal_bob: { path: "/static/assets/carrot-forest-avatar-teal_bob-normalized-v2.png", rows: 6 },
  };
  const defaultCosmetics = {
    skin: "peach", outfit: "forest", bottom: "cream", shoes: "brown", hair: "soft",
    hat: "none", glasses: "none", face: "calm", accessory: "none",
    lpcHair: "messy", lpcOutfit: "tshirt", lpcBottom: "long_pants", lpcShoes: "boots",
    lpcHat: "none", lpcGlasses: "none", expression: "bright", bodyType: "male",
    lpcFaceShape: "oval", lpcExpression: "neutral", lpcEyeStyle: "round", lpcEyebrow: "thin", lpcNose: "button", lpcMouth: "smile", lpcEyes: "none", lpcWrinkles: "none",
    hairColor: "black", outfitColor: "navy", bottomColor: "black", shoeColor: "brown", hatColor: "brown", glassesColor: "brown",
  };
  const defaultTuning = { headOffsetY: -6, outfitOffsetY: 0, glassesOffsetY: 0, worldScale: AVATAR_RENDER_SCALE };
  const hairPresetByStyle = {
    red_wave: "red_bow", cow_brown: "cow_hood", midnight: "midnight",
    blue_short: "blue_cap", teal_bob: "teal_bob",
  };
  const outfitPresetByStyle = {
    navy_garden: "red_bow", cow_vest: "cow_hood", violet: "midnight",
    blue_overalls: "blue_cap", teal_garden: "teal_bob",
  };

  function storedState() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; } catch { return {}; }
  }

  function normalizedAvatar(source = {}) {
    return {
      name: source.name || "세준", gender: source.gender === "male" ? "male" : "female",
      engine: source.engine === "premium" ? "premium" : "lpc",
      preset: premiumPresets[source.preset] ? source.preset : "blue_cap",
      x: Number.isFinite(source.x) ? source.x : 384, y: Number.isFinite(source.y) ? source.y : 352,
      direction: directionRows[source.direction] == null ? "down" : source.direction,
      mounted: Boolean(source.mounted), sitting: Boolean(source.sitting),
      cosmetics: { ...defaultCosmetics, ...(source.cosmetics || {}) },
      tuning: { ...defaultTuning, ...(source.tuning || {}) },
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
      this.mountTransitioning = false;
      this.actionPose = null;
      this.actionUntil = 0;
      this.petAction = null;
      this.petActionUntil = 0;
      this.petTrail = [];
      this.petLastSampleAt = 0;
      this.petFacing = "right";
      this.ratActive = false;
      this.ratNextSpawnAt = 0;
      this.ratDespawnAt = 0;
      this.ratTurnAt = 0;
      this.ratDirection = "left";
      this.ratEventId = 0;
      this.lastRatAttackAt = 0;
      this.lastPetAttackAt = 0;
      this.lastStepSfxAt = 0;
    }

    preload() {
      this.load.image("world-bg", "/static/assets/carrot-forest-world-v3.png?v=20260831-1");
      this.load.image("home-bg", "/static/assets/carrot-forest-home-v1.png");
      this.load.image("garden-bg", "/static/assets/carrot-forest-garden-v1.png");
      this.load.spritesheet("lpc-pets", "/static/assets/carrot-forest-lpc-pets-v1.png?v=20260831-1", { frameWidth: 32, frameHeight: 32 });
      this.load.spritesheet("lpc-rat", "/static/assets/carrot-forest-lpc-rat-v1.png?v=20260831-1", { frameWidth: 32, frameHeight: 32 });
      this.load.spritesheet("animated-objects", "/static/assets/carrot-forest-animated-objects-v1.png?v=20260831-1", { frameWidth: 128, frameHeight: 128 });
      this.load.spritesheet("storage-objects", "/static/assets/carrot-forest-storage-atlas-v3.png?v=20260831-1", { frameWidth: 256, frameHeight: 256 });
      this.load.image("reward-cow", "/static/assets/carrot-forest-reward-cow-v1.png?v=20260831-1");
    }

    create() {
      this.background = this.add.image(WORLD.width / 2, WORLD.height / 2, "world-bg").setDisplaySize(WORLD.width, WORLD.height);
      this.createAnimatedObjectAnimations();
      this.placementGrid = this.add.graphics().setDepth(1).setVisible(false);
      this.placementPreview = null;
      this.placedObjectActors = [];
      this.syncPlacedObjects(storedState().placed || []);
      this.player = this.add.container(this.avatar.x, this.avatar.y);
      this.motionFx = this.add.graphics().setDepth(2);
      this.player.add(this.motionFx);
      // The world renderer deliberately owns no legacy avatar textures.  The
      // official LPC engine is the single visual source for the player.
      this.presetSources = {};
      if (this.textures.exists("avatar-composite")) this.textures.remove("avatar-composite");
      this.compositeTexture = this.textures.createCanvas("avatar-composite", 224, 288);
      // LPC의 실제 발바닥은 합성 캔버스 y=250 부근이다. 그 점을 컨테이너 원점(그림자)에 맞춘다.
      this.premiumAvatar = this.add.image(0, 0, "avatar-composite").setOrigin(0.5, 0.87).setDepth(3);
      this.player.add(this.premiumAvatar);
      this.pet = this.add.sprite(this.avatar.x + 31, this.avatar.y + 10, "lpc-pets", 0).setOrigin(0.5, 1).setScale(1.2).setDepth(this.avatar.y - 1);
      this.petEmoji = this.add.text(this.avatar.x + 31, this.avatar.y + 8, "", { fontSize: "25px" }).setOrigin(0.5, 1).setDepth(this.avatar.y - 1).setVisible(false);
      this.petHeart = this.add.text(this.avatar.x + 31, this.avatar.y - 28, "💚", { fontSize: "23px" }).setOrigin(0.5).setDepth(999).setVisible(false);
      this.petFollowX = this.avatar.x + 31;
      this.petFollowY = this.avatar.y + 10;
      this.ratActor = this.add.container(0, 0).setVisible(false);
      this.ratShadow = this.add.ellipse(0, 0, 22, 6, 0x17352a, 0.24).setOrigin(0.5, 0.5);
      this.ratSprite = this.add.sprite(0, 0, "lpc-rat", 1).setOrigin(0.5, 1).setScale(1.4);
      this.ratMarker = this.add.text(0, -38, "!", {
        fontFamily: "Pretendard, Noto Sans KR, sans-serif", fontSize: "14px", fontStyle: "bold",
        color: "#ffffff", backgroundColor: "#d85836", padding: { x: 5, y: 1 },
      }).setOrigin(0.5);
      this.ratActor.add([this.ratShadow, this.ratSprite, this.ratMarker]);
      this.nameplate = this.add.text(0, NAMEPLATE_Y, this.avatar.name, {
        fontFamily: "Pretendard, Noto Sans KR, sans-serif", fontSize: "12px", fontStyle: "bold",
        color: "#173528", backgroundColor: "rgba(255,255,255,.92)", padding: { x: 7, y: 3 },
      }).setOrigin(0.5).setStroke("#ffffff", 2);
      this.player.add(this.nameplate);
      this.rebuildAvatar();
      this.keys = this.input.keyboard.addKeys("W,A,S,D,R,Q,C,X,E,F");
      this.cursors = this.input.keyboard.createCursorKeys();
      // Phaser가 Space를 가로채면 슬로건 textarea에서 띄어쓰기가 되지 않는다.
      this.input.keyboard.removeCapture([Phaser.Input.Keyboard.KeyCodes.SPACE]);
      const formFocused = () => ["INPUT", "TEXTAREA", "SELECT", "BUTTON"].includes(document.activeElement?.tagName);
      this.input.keyboard.on("keydown-Q", () => { if (!formFocused()) window.dispatchEvent(new CustomEvent("forest-phaser-interact")); });
      this.input.keyboard.on("keydown-C", () => { if (!formFocused()) window.dispatchEvent(new CustomEvent("forest-phaser-action", { detail: "chat" })); });
      this.input.keyboard.on("keydown-X", (event) => {
        if (event.repeat || formFocused()) return;
        window.dispatchEvent(new CustomEvent("forest-phaser-action", { detail: "sit" }));
      });
      this.input.keyboard.on("keydown-F", (event) => {
        if (event.repeat || formFocused()) return;
        window.dispatchEvent(new CustomEvent("forest-phaser-action", { detail: "feed" }));
      });
      this.input.keyboard.on("keydown-E", () => { if (!formFocused()) window.dispatchEvent(new CustomEvent("forest-phaser-action", { detail: "ride" })); });
      this.input.keyboard.on("keydown-Z", (event) => {
        if (event.repeat || formFocused()) return;
        this.playAction("attack", this.equippedWeaponDuration());
      });
      this.input.keyboard.on("keydown-V", (event) => {
        if (event.repeat || formFocused()) return;
        event.preventDefault();
        window.dispatchEvent(new CustomEvent("forest-placement-confirm"));
      });
      this.input.keyboard.on("keydown", (event) => {
        if (event.key !== "0" || event.repeat || formFocused()) return;
        event.preventDefault();
        this.playTogether("dance", 1800);
      });
      this.events.on("shutdown", () => this.detachWindowEvents());
      this.attachWindowEvents();
      window.LpcAvatarEngine?.ready().then(() => this.rebuildAvatar());
      document.documentElement.classList.add("phaser-world-ready");
      window.carrotForestPhaserActive = true;
      window.carrotForestPhaserMove = (direction) => this.nudge(direction);
      this.input.once("pointerdown", () => document.getElementById("phaser-world")?.focus());
      this.input.on("pointerdown", (pointer) => {
        window.dispatchEvent(new CustomEvent("forest-world-pointer", { detail: { x: pointer.worldX, y: pointer.worldY } }));
      });
      this.emitPosition(true);
    }

    createAnimatedObjectAnimations() {
      Object.entries(animatedObjectRows).forEach(([code, row]) => {
        const key = `forest-object-${code}`;
        if (this.anims.exists(key)) return;
        this.anims.create({
          key,
          frames: this.anims.generateFrameNumbers("animated-objects", { start: row * 4, end: row * 4 + 3 }),
          frameRate: code === "garden_pinwheel" ? 7 : code === "firefly_lantern" ? 4 : 5,
          repeat: -1,
        });
      });
    }

    createPlacedObjectActor(item, preview = false) {
        let actor;
        if (Object.hasOwn(animatedObjectRows, item.code)) {
          const size = item.code === "firefly_lantern" || item.code === "garden_pinwheel" ? 76 : 96;
          actor = this.add.sprite(item.x, item.y, "animated-objects", animatedObjectRows[item.code] * 4)
            .setOrigin(0.5, 0.84)
            .setDisplaySize(size, size);
        } else if (item.code === "reward_cow") {
          actor = this.add.image(item.x, item.y, "reward-cow").setOrigin(0.5, 0.9).setDisplaySize(82, 82);
        } else if (Object.hasOwn(storageObjectIndex, item.code)) {
          const largeObjects = new Set(["tent", "light_tent", "picnic_table", "bbq_table", "pond", "fence", "flower_cart", "carrot_crate"]);
          const smallObjects = new Set(["chair_green", "chair_red", "lantern", "mailbox", "watering_can"]);
          const size = largeObjects.has(item.code) ? 96 : smallObjects.has(item.code) ? 70 : 82;
          actor = this.add.sprite(item.x, item.y, "storage-objects", storageObjectIndex[item.code])
            .setOrigin(0.5, 0.9)
            .setDisplaySize(size, size);
        }
        if (!actor) return null;
        actor.setAngle(Number(item.rotation) || 0)
          .setAlpha(preview ? .72 : 1)
          .setDepth(preview ? 998 : item.y - 2)
          .setVisible(this.sceneName === "world");
        this.applyPlacedObjectState(actor, item);
        return actor;
    }

    applyPlacedObjectState(actor, item) {
      const type = interactiveObjectTypes[item.code];
      if (Object.hasOwn(animatedObjectRows, item.code)) {
        if (!type || item.active) actor.play(`forest-object-${item.code}`);
        else actor.stop().setFrame(animatedObjectRows[item.code] * 4);
      }
      if (!type) return;
      actor.setData("interactive", true).setData("active", Boolean(item.active));
      this.tweens.killTweensOf(actor);
      actor.setPosition(item.x, item.y).setAlpha(item.active ? 1 : .58);
      if (!item.active) {
        actor.setTint(0x6f756d);
        return;
      }
      actor.clearTint();
      if (type === "cow") {
        this.tweens.add({
          targets: actor, y: item.y - 4, angle: (Number(item.rotation) || 0) + 3,
          duration: 330, yoyo: true, repeat: -1, ease: "Sine.easeInOut",
        });
      } else {
        this.tweens.add({
          targets: actor, alpha: { from: .82, to: 1 }, duration: type === "fire" ? 180 : 620,
          yoyo: true, repeat: -1, ease: "Sine.easeInOut",
        });
      }
    }

    syncPlacedObjects(placed = []) {
      this.placedObjectActors?.forEach((actor) => { this.tweens.killTweensOf(actor); actor.destroy(); });
      this.placedObjectActors = placed.map((item) => this.createPlacedObjectActor(item)).filter(Boolean);
    }

    syncPlacement(detail = {}) {
      this.placementGrid.clear().setVisible(Boolean(detail.active) && this.sceneName === "world");
      this.placementPreview?.destroy();
      this.placementPreview = null;
      if (!detail.active || this.sceneName !== "world") return;
      (detail.cells || []).forEach((cell) => {
        const fill = cell.valid ? 0x48c978 : 0xc95d50;
        const alpha = cell.valid ? .18 : .055;
        this.placementGrid.fillStyle(fill, alpha).fillRect(cell.x - 15, cell.y - 15, 30, 30);
        this.placementGrid.lineStyle(1, fill, cell.valid ? .78 : .2).strokeRect(cell.x - 15, cell.y - 15, 30, 30);
      });
      if (detail.draft) {
        this.placementGrid.lineStyle(3, 0xffc34d, .95).strokeRect(detail.draft.x - 16, detail.draft.y - 16, 32, 32);
        this.placementPreview = this.createPlacedObjectActor(detail.draft, true);
      }
    }

    rebuildAvatar() {
      const c = this.avatar.cosmetics;
      this.setPremiumFrame(this.avatar.direction, false, 0);
      this.nameplate?.setDepth(30).setText(this.avatar.name);
      const pet = c.pet;
      const petColumns = { blue_eyes_white_cat: 0, gold_eyes_orange_cat: 3, white_pup: 6 };
      this.pet?.setVisible(Object.hasOwn(petColumns, pet));
      this.petBaseColumn = petColumns[pet] || 0;
      this.pet?.setFrame(this.petBaseColumn);
      this.petEmoji?.setVisible(false);
      this.petTrail = [];
      this.petLastSampleAt = 0;
    }

    attachWindowEvents() {
      this.onAvatar = (event) => this.applyAvatarUpdate(normalizedAvatar({ ...this.avatar, ...(event.detail || {}) }));
      this.onState = (event) => {
        const detail = event.detail || {};
        if (detail.avatar) {
          const nextAvatar = normalizedAvatar(detail.avatar);
          this.player.setPosition(nextAvatar.x, nextAvatar.y);
          this.applyAvatarUpdate(nextAvatar);
        }
        if (detail.scene) this.setScene(detail.scene);
        if (Array.isArray(detail.placed)) this.syncPlacedObjects(detail.placed);
      };
      window.addEventListener("forest-avatar-updated", this.onAvatar);
      window.addEventListener("forest-state-updated", this.onState);
      this.onAction = (event) => {
        const detail = event.detail || {};
        this.playAction(detail.pose || detail, Number(detail.duration) || 1100);
      };
      window.addEventListener("forest-avatar-action", this.onAction);
      this.onPetFed = () => this.showPetHeart();
      window.addEventListener("forest-pet-fed", this.onPetFed);
      this.onPlacement = (event) => this.syncPlacement(event.detail || {});
      window.addEventListener("forest-placement-updated", this.onPlacement);
    }

    detachWindowEvents() {
      window.removeEventListener("forest-avatar-updated", this.onAvatar);
      window.removeEventListener("forest-state-updated", this.onState);
      window.removeEventListener("forest-avatar-action", this.onAction);
      window.removeEventListener("forest-pet-fed", this.onPetFed);
      window.removeEventListener("forest-placement-updated", this.onPlacement);
    }

    showPetHeart() {
      const actor = this.pet?.visible ? this.pet : this.petEmoji;
      if (!actor || !actor.visible) return;
      this.petHeart.setPosition(actor.x, actor.y - 35).setAlpha(1).setScale(0.7).setVisible(true);
      this.tweens.killTweensOf(this.petHeart);
      this.tweens.add({
        targets: this.petHeart, y: actor.y - 62, alpha: 0, scale: 1.35, duration: 1150, ease: "Back.easeOut",
        onComplete: () => this.petHeart.setVisible(false),
      });
    }

    playAction(pose, duration = 1100) {
      this.actionPose = pose;
      this.actionUntil = performance.now() + duration;
      if (pose === "attack") this.tryAttackRat(performance.now());
      if (pose === "attack") {
        const weapon = this.avatar.cosmetics?.lpcWeapon;
        const name = weapon === "bow" ? "attack-bow" : ["wand", "cane"].includes(weapon) ? "attack-magic" : "attack-sword";
        window.dispatchEvent(new CustomEvent("forest-sfx", { detail: { name, volume: 0.34, minInterval: 280 } }));
      }
      if (pose === "dance") window.dispatchEvent(new CustomEvent("forest-sfx", { detail: { name: "dance", volume: 0.28, minInterval: 900 } }));
      if (pose === "dance") {
        this.petAction = "dance";
        this.petActionUntil = this.actionUntil;
      }
    }

    equippedWeaponDuration() {
      return {
        bow: 1280,
        wand: 980,
        cane: 860,
        dagger: 680,
        sword: 780,
      }[this.avatar.cosmetics?.lpcWeapon] || 780;
    }

    playTogether(pose, duration = 1600) {
      this.playAction(pose, duration);
      this.petAction = pose;
      this.petActionUntil = performance.now() + duration;
      window.dispatchEvent(new CustomEvent("forest-companion-action", { detail: pose }));
    }

    applyAvatarUpdate(nextAvatar) {
      if (nextAvatar.mounted !== this.avatar.mounted && this.premiumAvatar) {
        this.playMountTransition(nextAvatar);
        return;
      }
      const sittingChanged = nextAvatar.sitting !== this.avatar.sitting;
      this.avatar = nextAvatar;
      if (sittingChanged) {
        this.petAction = nextAvatar.sitting ? "sit" : "idle";
        this.petActionUntil = performance.now() + 900;
      }
      this.rebuildAvatar();
    }

    playMountTransition(nextAvatar) {
      this.mountTransitioning = true;
      this.tweens.killTweensOf(this.premiumAvatar);
      this.motionFx.clear();
      this.actionPose = "jump";
      this.actionUntil = performance.now() + 520;
      let swapped = false;
      this.tweens.add({
        targets: this.premiumAvatar,
        y: -12,
        duration: 210,
        yoyo: true,
        ease: "Sine.easeOut",
        onUpdate: (tween) => {
          if (!swapped && tween.progress >= 0.5) {
            swapped = true;
            this.avatar = nextAvatar;
          }
          this.setPremiumFrame(this.avatar.direction, false, performance.now());
        },
        onComplete: () => {
          this.avatar = nextAvatar;
          this.actionPose = null;
          this.actionUntil = 0;
          this.premiumAvatar.setY(0);
          this.mountTransitioning = false;
          this.motionFx.clear();
          this.rebuildAvatar();
        },
      });
    }

    setScene(sceneName) {
      this.sceneName = ["world", "home", "garden"].includes(sceneName) ? sceneName : "world";
      this.background.setTexture(`${this.sceneName}-bg`).setDisplaySize(WORLD.width, WORLD.height);
      this.ratActor?.setVisible(this.sceneName === "world" && this.ratActive);
      this.placedObjectActors?.forEach((actor) => actor.setVisible(this.sceneName === "world"));
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
      if (this.mountTransitioning) return;
      this.updateRat(time, delta);
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
        this.updatePet(time, delta, false);
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
        const stepInterval = running ? 190 : 310;
        if (!this.avatar.mounted && time - this.lastStepSfxAt >= stepInterval) {
          this.lastStepSfxAt = time;
          window.dispatchEvent(new CustomEvent("forest-sfx", {
            detail: { name: running ? "run-grass" : "step-grass", volume: running ? 0.19 : 0.15, minInterval: stepInterval - 20 },
          }));
        }
      }
      this.setPremiumFrame(direction, true, time, running);
      this.updatePet(time, delta, true);
      this.emitPosition();
    }

    spawnRat(time) {
      const spawnPoints = [
        [374, 286], [420, 420], [540, 330], [650, 365], [690, 445], [355, 470],
      ];
      const candidates = spawnPoints.filter(([x, y]) => Phaser.Math.Distance.Between(x, y, this.avatar.x, this.avatar.y) > 110);
      const [x, y] = Phaser.Utils.Array.GetRandom(candidates.length ? candidates : spawnPoints);
      this.ratEventId += 1;
      this.ratActive = true;
      this.ratDespawnAt = time + 12000;
      this.ratTurnAt = time + Phaser.Math.Between(900, 1800);
      this.ratDirection = Phaser.Utils.Array.GetRandom(["left", "right", "up", "down"]);
      this.ratActor.setPosition(x, y).setDepth(y - 2).setAlpha(1).setScale(1).setVisible(true);
      window.dispatchEvent(new CustomEvent("forest-rat-appeared", { detail: { eventId: this.ratEventId } }));
    }

    dismissRat(time, caught = false) {
      if (!this.ratActive) return;
      this.ratActive = false;
      this.ratNextSpawnAt = time + Phaser.Math.Between(12000, 22000);
      if (!caught) {
        this.ratActor.setVisible(false);
        return;
      }
      const x = this.ratActor.x;
      const y = this.ratActor.y;
      const rewardText = this.add.text(x, y - 30, "+5 🥕", {
        fontFamily: "Pretendard, Noto Sans KR, sans-serif", fontSize: "14px", fontStyle: "bold",
        color: "#fff7bd", stroke: "#5c3511", strokeThickness: 4,
      }).setOrigin(0.5).setDepth(999);
      this.tweens.add({
        targets: this.ratActor, alpha: 0, scale: 1.45, duration: 180,
        onComplete: () => this.ratActor.setVisible(false).setAlpha(1).setScale(1),
      });
      this.tweens.add({
        targets: rewardText, y: y - 58, alpha: 0, duration: 850,
        onComplete: () => rewardText.destroy(),
      });
    }

    tryAttackRat(time) {
      if (this.sceneName !== "world" || !this.ratActive || time - this.lastRatAttackAt < 320) return;
      this.lastRatAttackAt = time;
      const dx = this.ratActor.x - this.avatar.x;
      const dy = this.ratActor.y - this.avatar.y;
      const distance = Math.hypot(dx, dy);
      const facing = { left: [-1, 0], right: [1, 0], up: [0, -1], down: [0, 1] }[this.avatar.direction] || [0, 1];
      const facingScore = distance ? (dx * facing[0] + dy * facing[1]) / distance : 1;
      if (distance > 76 || facingScore < -0.1) return;
      const eventId = this.ratEventId;
      this.dismissRat(time, true);
      window.dispatchEvent(new CustomEvent("forest-rat-caught", { detail: { eventId, amount: 5 } }));
    }

    updateRat(time, delta) {
      if (this.sceneName !== "world") {
        this.ratActor?.setVisible(false);
        return;
      }
      if (!this.ratActive) {
        if (!this.ratNextSpawnAt) this.ratNextSpawnAt = time + Phaser.Math.Between(3500, 7000);
        if (time >= this.ratNextSpawnAt) this.spawnRat(time);
        return;
      }
      this.ratActor.setVisible(true);
      if (time >= this.ratDespawnAt) {
        this.dismissRat(time);
        return;
      }
      if (time >= this.ratTurnAt) {
        this.ratDirection = Phaser.Utils.Array.GetRandom(["left", "right", "up", "down"]);
        this.ratTurnAt = time + Phaser.Math.Between(700, 1600);
      }
      const speed = 23 * Math.min(delta, 40) / 1000;
      const vector = { left: [-speed, 0], right: [speed, 0], up: [0, -speed], down: [0, speed] }[this.ratDirection];
      const nextX = this.ratActor.x + vector[0];
      const nextY = this.ratActor.y + vector[1];
      if (this.isBlocked(nextX, nextY)) {
        this.ratDirection = Phaser.Utils.Array.GetRandom(["left", "right", "up", "down"]);
        this.ratTurnAt = time + 500;
      } else {
        this.ratActor.setPosition(nextX, nextY).setDepth(nextY - 2);
      }
      const directionRow = { down: 0, left: 1, right: 2, up: 3 }[this.ratDirection] || 0;
      this.ratSprite.setFrame(directionRow * 3 + Math.floor(time / 145) % 3);
      this.ratShadow.setY(0);
    }

    updatePet(time, delta, playerMoving) {
      if ((!this.pet || !this.pet.visible) && (!this.petEmoji || !this.petEmoji.visible)) return;
      if (!this.petTrail.length) {
        this.petTrail.push({ x: this.avatar.x, y: this.avatar.y, direction: this.avatar.direction, time });
      }
      if (playerMoving && time - this.petLastSampleAt >= 42) {
        this.petTrail.push({ x: this.avatar.x, y: this.avatar.y, direction: this.avatar.direction, time });
        this.petLastSampleAt = time;
        while (this.petTrail.length > 28 || (this.petTrail[1] && time - this.petTrail[1].time > 1600)) this.petTrail.shift();
      }
      const directionOffset = {
        left: [32, 8], right: [-32, 8], up: [27, 18], down: [-29, 9],
      }[this.avatar.direction] || [-29, 9];
      const delayed = playerMoving
        ? [...this.petTrail].reverse().find((point) => point.time <= time - 330)
        : null;
      const petActor = this.pet?.visible ? this.pet : this.petEmoji;
      const ratDistanceFromPlayer = this.ratActive ? Phaser.Math.Distance.Between(this.ratActor.x, this.ratActor.y, this.avatar.x, this.avatar.y) : Infinity;
      const autoHunting = this.sceneName === "world" && this.ratActive && this.pet?.visible && ratDistanceFromPlayer < 185;
      const targetX = autoHunting ? this.ratActor.x : delayed ? delayed.x : this.avatar.x + directionOffset[0];
      const targetY = autoHunting ? this.ratActor.y : delayed ? delayed.y + 8 : this.avatar.y + directionOffset[1];
      const follow = autoHunting ? Math.min(0.12, Math.max(0.035, delta / 260)) : playerMoving ? Math.min(0.34, Math.max(0.08, delta / 120)) : Math.min(0.22, Math.max(0.045, delta / 210));
      const actor = petActor;
      const previousX = this.petFollowX;
      this.petFollowX += (targetX - this.petFollowX) * follow;
      this.petFollowY += (targetY - this.petFollowY) * follow;
      const togetherSitting = this.avatar.sitting;
      const dancing = this.petAction === "dance" && time < this.petActionUntil;
      if (Math.abs(this.petFollowX - previousX) > 0.08) this.petFacing = this.petFollowX < previousX ? "left" : "right";
      const gait = playerMoving || autoHunting ? Math.sin(time / (autoHunting ? 190 : 82)) : 0;
      const danceX = dancing ? Math.sin(time / 120) * 7 : 0;
      const hop = dancing ? -Math.abs(Math.sin(time / 118)) * 7 : playerMoving || autoHunting ? -Math.abs(gait) * 2.6 : togetherSitting ? 4 : Math.sin(time / 430) * 0.7;
      actor.setPosition(this.petFollowX + danceX, this.petFollowY + hop).setDepth(this.petFollowY - 1);
      let petDirection = this.avatar.direction;
      if (autoHunting) {
        const dx = this.ratActor.x - this.petFollowX;
        const dy = this.ratActor.y - this.petFollowY;
        petDirection = Math.abs(dx) > Math.abs(dy) ? (dx < 0 ? "left" : "right") : (dy < 0 ? "up" : "down");
      }
      const petDirectionRow = { down: 0, left: 1, right: 2, up: 3 }[petDirection] || 0;
      const petFrame = playerMoving || autoHunting ? Math.floor(time / (autoHunting ? 210 : 105)) % 3 : 1;
      this.pet?.setFrame(petDirectionRow * 9 + (this.petBaseColumn || 0) + petFrame);
      actor.setFlipX?.(false);
      actor.setAngle(dancing ? Math.sin(time / 95) * 11 : playerMoving || autoHunting ? gait * 2.2 : 0);
      if (this.pet?.visible) {
        const baseScale = togetherSitting ? 1.08 : 1.2;
        const squash = dancing ? Math.sin(time / 118) * 0.08 : playerMoving ? Math.abs(gait) * 0.035 : 0;
        actor.setScale(baseScale + squash, baseScale - squash * 0.65);
      } else {
        const emojiScale = togetherSitting ? 0.88 : dancing ? 1 + Math.sin(time / 118) * 0.08 : 1;
        actor.setScale(emojiScale, emojiScale);
      }
      if (time >= this.petActionUntil) this.petAction = null;
      if (autoHunting && Phaser.Math.Distance.Between(this.petFollowX, this.petFollowY, this.ratActor.x, this.ratActor.y) < 25 && time - this.lastPetAttackAt > 2600) {
        this.lastPetAttackAt = time;
        this.petAction = "attack";
        this.petActionUntil = time + 760;
        const eventId = this.ratEventId;
        this.dismissRat(time, true);
        window.dispatchEvent(new CustomEvent("forest-rat-caught", { detail: { eventId, amount: 5, source: "pet" } }));
      }
    }

    setPremiumFrame(direction, moving, time, running = false) {
      if (!this.premiumAvatar || !window.CarrotAvatarCompositor) return;
      const rate = running || this.avatar.mounted ? 90 : 140;
      const cosmetics = this.avatar.cosmetics;
      const context = this.compositeTexture.getContext();
      context.clearRect(0, 0, 224, 288);
      const pose = performance.now() < this.actionUntil ? this.actionPose : null;
      if (!pose) this.actionPose = null;
      const usedLpc = this.avatar.engine === "lpc" && window.LpcAvatarEngine?.draw(context, this.avatar, {
        direction, moving, running, pose, frame: Math.floor(time / rate),
      }, { x: 16, y: 58, width: 192, height: 192 });
      if (!usedLpc) this.premiumAvatar.setVisible(false);
      else this.premiumAvatar.setVisible(true);
      this.compositeTexture.refresh();
      this.drawMotionEffects(direction, moving, Math.floor(time / rate) % 4);
      const worldScale = Math.min(0.58, Math.max(0.32, Number(this.avatar.tuning.worldScale) || AVATAR_RENDER_SCALE));
      this.premiumAvatar.setScale(worldScale);
      this.nameplate?.setY(-Math.round(288 * worldScale * 0.87) - 7);
    }

    drawMotionEffects() {
      this.motionFx?.clear();
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
