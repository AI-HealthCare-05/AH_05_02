/* A reversible, source-sprite group portrait inside the live Phaser field. */
((root) => {
  "use strict";

  const NICKNAMES = Object.freeze(["성실한 당근", "꾸준한 상균", "달빛의 빛샘", "숲속의 수인", "발명의 준혁", "해결의 세준"]);
  const CAMERA = Object.freeze({ x: 694, y: 338, width: 52, height: 76 });
  // The real carrot house occupies x149..286, y0..240 in the 768x512 map.
  // Keep its leafy roof and doorstep visible above the group; never replace
  // the field with a generated backdrop or stretch the original background.
  const FRAME = Object.freeze({ x: 0, y: 0, width: 640, height: 360, scale: 4 });
  const POSITIONS = Object.freeze([[57, 294], [126, 284], [195, 280], [264, 280], [333, 284], [402, 294]].map(Object.freeze));
  const clone = value => JSON.parse(JSON.stringify(value));

  function portraitPresets(presets) {
    if (!Array.isArray(presets) || presets.length !== 6) throw new Error("공식 프리셋 여섯 벌을 준비하지 못했어요.");
    return NICKNAMES.map((nickname, index) => {
      const preset = presets.find(item => Number(item?.number) === index + 1);
      if (!preset?.avatar || preset.avatar.engine !== "lpc") throw new Error(`${index + 1}번 공식 의상을 불러오지 못했어요.`);
      // Portrait labels never become profile or saved-preset names. Copy every
      // actual outfit layer/color and only normalize the temporary actor pose.
      return { number: index + 1, nickname, avatar: { ...clone(preset.avatar), mounted: false, sitting: false, direction: "down" } };
    });
  }

  function alphaBounds(pixels, width, height) {
    let left = width, top = height, right = -1, bottom = -1;
    for (let y = 0; y < height; y += 1) for (let x = 0; x < width; x += 1) {
      if (pixels[(y * width + x) * 4 + 3] < 16) continue;
      left = Math.min(left, x); right = Math.max(right, x);
      top = Math.min(top, y); bottom = Math.max(bottom, y);
    }
    return right < left ? null : { x: left, y: top, width: right - left + 1, height: bottom - top + 1 };
  }

  function fitWithin(width, height, maxWidth, maxHeight) {
    const scale = Math.min(maxWidth / width, maxHeight / height);
    return { width: width * scale, height: height * scale };
  }

  function overlapsPortrait(actor) {
    if (!actor) return false;
    let bounds;
    try { bounds = actor.getBounds?.(); } catch { /* A destroyed actor may no longer expose its bounds. */ }
    const width = Number(bounds?.width ?? actor.displayWidth ?? 0);
    const height = Number(bounds?.height ?? actor.displayHeight ?? 0);
    const x = Number(bounds?.x ?? (actor.x - width * (actor.originX ?? .5)));
    const y = Number(bounds?.y ?? (actor.y - height * (actor.originY ?? 1)));
    if (![x, y, width, height].every(Number.isFinite) || width < 0 || height < 0) return false;
    return x + width >= FRAME.x && x <= FRAME.x + FRAME.width
      && y + height >= FRAME.y && y <= FRAME.y + FRAME.height;
  }

  function labelY(feetY, opaqueTop, { height = 288, originY = .87, scale = .43, gap = 4 } = {}) {
    return feetY + (opaqueTop - height * originY) * scale - gap;
  }

  function trimmedTexture(scene, key) {
    const trimmed = `${key}-trimmed-v159`;
    if (scene.textures.exists(trimmed)) return trimmed;
    const source = scene.textures.get(key).getSourceImage();
    const canvas = root.document.createElement("canvas");
    canvas.width = source.naturalWidth || source.width;
    canvas.height = source.naturalHeight || source.height;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    context.drawImage(source, 0, 0);
    const bounds = alphaBounds(context.getImageData(0, 0, canvas.width, canvas.height).data, canvas.width, canvas.height);
    if (!bounds) throw new Error(`Empty field decoration: ${key}`);
    const crop = root.document.createElement("canvas");
    crop.width = bounds.width; crop.height = bounds.height;
    crop.getContext("2d").drawImage(canvas, bounds.x, bounds.y, bounds.width, bounds.height, 0, 0, bounds.width, bounds.height);
    scene.textures.addCanvas(trimmed, crop);
    return trimmed;
  }

  function fitImage(image, maxWidth, maxHeight) {
    const size = fitWithin(image.width, image.height, maxWidth, maxHeight);
    return image.setDisplaySize(size.width, size.height);
  }

  function pngBlob(dataUrl) {
    if (typeof dataUrl !== "string" || !dataUrl.startsWith("data:image/png;base64,")) throw new Error("PNG 사진을 생성하지 못했어요.");
    const binary = root.atob(dataUrl.slice(dataUrl.indexOf(",") + 1));
    return new root.Blob([Uint8Array.from(binary, char => char.charCodeAt(0))], { type: "image/png" });
  }

  function saveView(scene) {
    const camera = scene.cameras.main;
    return {
      zoom: camera.zoom, scrollX: camera.scrollX, scrollY: camera.scrollY,
      x: camera.x ?? 0, y: camera.y ?? 0, width: camera.width, height: camera.height,
      target: camera._follow, roundPixels: camera.roundPixels,
      lerpX: camera.lerp?.x ?? 1, lerpY: camera.lerp?.y ?? 1,
      offsetX: camera.followOffset?.x ?? 0, offsetY: camera.followOffset?.y ?? 0,
      useBounds: camera.useBounds,
    };
  }

  function restoreView(scene, saved) {
    // Phaser's CameraManager shuts down before the scene's own listener.
    const camera = scene.cameras?.main;
    if (!camera) return;
    camera.stopFollow();
    camera.setViewport?.(saved.x, saved.y, saved.width, saved.height);
    camera.useBounds = saved.useBounds;
    camera.setZoom(saved.zoom);
    if (saved.target) camera.startFollow(saved.target, saved.roundPixels, saved.lerpX, saved.lerpY, saved.offsetX, saved.offsetY);
    else camera.setFollowOffset(saved.offsetX, saved.offsetY);
    camera.roundPixels = saved.roundPixels;
    // Do not centerOn/rebuild: restore the exact pre-photo pan even while a
    // following camera was between frames. Its next normal frame resumes it.
    camera.scrollX = saved.scrollX; camera.scrollY = saved.scrollY;
  }

  class Controller {
    constructor(scene) {
      this.scene = scene;
      this.session = null;
      this.sequence = 0;
      this.onStart = event => { void this.start(event.detail || {}); };
      this.onCancel = event => this.cancel("", event.detail?.requestId);
      root.addEventListener("forest-memory-start", this.onStart);
      root.addEventListener("forest-memory-cancel", this.onCancel);
    }

    get active() { return Boolean(this.session); }

    emit(type, session, detail = {}) {
      root.dispatchEvent(new root.CustomEvent(type, { detail: { requestId: session.requestId, ...detail } }));
    }

    progress(session, stage, message) {
      if (session.stage === stage) return;
      session.stage = stage;
      this.emit("forest-memory-progress", session, { stage, message });
    }

    async start(detail) {
      if (this.active) return false;
      const scene = this.scene;
      const session = { requestId: detail.requestId, id: ++this.sequence, objects: [], textures: [], visibility: [], animationScales: [], cleanups: [], restored: false };
      this.session = session;
      try {
        if (scene.sceneName !== "world" || scene.mountTransitioning || scene.placementActive) throw new Error("숲 들판에서 이동과 가구 배치를 마친 뒤 촬영해 주세요.");
        session.presets = portraitPresets(detail.presets);
        session.startedAt = root.performance.now();
        session.sceneStartedAt = scene.time.now;
        session.view = saveView(scene);
        session.inputEnabled = scene.input.enabled;
        session.tweenScale = scene.tweens.timeScale;
        session.clockScale = scene.time.timeScale;
        scene.memoryCapturing = true;
        scene.input.enabled = false;
        scene.tweens.timeScale = 0;
        scene.time.timeScale = 0;
        const freezeAnimations = object => {
          if (object.anims) { session.animationScales.push([object.anims, object.anims.timeScale]); object.anims.timeScale = 0; }
          object.list?.forEach(freezeAnimations);
        };
        scene.children.list.forEach(freezeAnimations);
        this.progress(session, "loading", "공식 의상과 숲 친구들을 준비하고 있어요.");
        if (this.session !== session) return false;
        const required = ["forest-rabbit-bunbun", "forest-rabbit-last-tick", "lpc-pets", "forest-cow-eat", "forest-cow-walk"];
        if (required.some(key => !scene.textures.exists(key))) throw new Error("Bunbun·Last tick과 모든 동물의 원본 이미지가 있어야 촬영할 수 있어요.");
        if (typeof root.LpcAvatarEngine?.prepare !== "function") throw new Error("공식 의상 준비 기능을 불러오지 못했어요. 새로고침해 주세요.");
        await this.bounded(session, root.LpcAvatarEngine.prepare(session.presets.map(item => item.avatar)), 20000, "의상 이미지 로딩 시간이 길어지고 있어요. 다시 시도해 주세요.");
        if (this.session !== session) return false;
        if (root.document.fonts?.ready) await this.bounded(session, root.document.fonts.ready, 5000, "이름표 글꼴을 불러오지 못했어요.");
        if (this.session !== session) return false;
        this.assemble(session);
        return true;
      } catch (error) {
        if (this.session === session) {
          this.restore(session);
          this.emit("forest-memory-error", session, { message: error?.message || "사진을 찍지 못했어요. 다시 시도해 주세요." });
        }
        return false;
      }
    }

    bounded(session, promise, milliseconds, message) {
      return new Promise((resolve, reject) => {
        const timer = root.setTimeout(() => reject(new Error(message)), milliseconds);
        const cancel = () => { root.clearTimeout(timer); resolve(null); };
        session.cleanups.push(cancel);
        Promise.resolve(promise).then(value => { root.clearTimeout(timer); resolve(value); }, error => { root.clearTimeout(timer); reject(error); });
      });
    }

    assemble(session) {
      const scene = this.scene;
      const hide = object => {
        if (!object) return;
        session.visibility.push([object, object.visible]);
        object.setVisible(false);
      };
      [scene.player, scene.pet, scene.petOverlay, scene.petEmoji, scene.petHeart, scene.ratActor, scene.ratAttackButton,
        scene.ratAttackPlate, scene.placementGrid, scene.placementPreview, scene.memoryCameraActor,
        scene.nightOverlay, scene.lightFx].forEach(hide);
      // Bounds include tall/rotated furniture whose center is outside the shot.
      // This changes visibility only; every saved placement is restored intact.
      scene.placedObjectActors?.filter(overlapsPortrait).forEach(hide);
      const camera = scene.cameras.main;
      camera.stopFollow();
      camera.useBounds = false;
      const viewZoom = Math.min(session.view.width / FRAME.width, session.view.height / FRAME.height) * .94;
      const viewWidth = Math.round(FRAME.width * viewZoom);
      const viewHeight = Math.round(FRAME.height * viewZoom);
      // On portrait phones, a full-height camera reveals empty world below
      // the authored map. Center a landscape viewport inside the same backing
      // canvas instead; only its display framing changes, never the PNG crop.
      camera.setViewport?.(session.view.x + Math.round((session.view.width - viewWidth) / 2),
        session.view.y + Math.round((session.view.height - viewHeight) / 2), viewWidth, viewHeight);
      camera.setZoom(viewZoom);
      camera.centerOn(FRAME.x + FRAME.width / 2, FRAME.y + FRAME.height / 2);
      const add = object => { session.objects.push(object); return object; };
      session.people = session.presets.map((preset, index) => {
        const [x, y] = POSITIONS[index];
        const key = `forest-memory-person-${session.id}-${index}`;
        const texture = scene.textures.createCanvas(key, 224, 288);
        session.textures.push(key);
        const shadow = add(scene.add.ellipse(x, y + 1, 22, 6, 0x243c2b, .18).setDepth(y - 1));
        const sprite = add(scene.add.image(x, y, key).setOrigin(.5, .87).setScale(.43).setDepth(y));
        const label = add(scene.add.text(x, y - 69, preset.nickname, {
          resolution: 4, fontFamily: "Pretendard, Noto Sans KR, sans-serif", fontSize: "10px", fontStyle: "bold",
          color: "#fffbee", stroke: "#284e35", strokeThickness: 3, padding: { x: 3, y: 2 },
        }).setOrigin(.5, 1).setDepth(1000));
        return { ...preset, x, y, startX: x + (index < 3 ? -36 : 36), startY: y, sprite, shadow, label, texture };
      });
      const animalDefinitions = [
        { kind: "bunbun", x: 87, y: 302, key: "forest-rabbit-bunbun", scale: 1.4 },
        { kind: "last-tick", x: 152, y: 301, key: "forest-rabbit-last-tick", scale: 1.4 },
        { kind: "pet", column: 3, x: 294, y: 336, key: "lpc-pets", scale: 1.2 },
        { kind: "pet", column: 6, x: 353, y: 338, key: "lpc-pets", scale: 1.2 },
        { kind: "cow", x: 500, y: 330, key: "forest-cow-eat", scale: 1.12 },
      ];
      session.animals = animalDefinitions.map((animal) => {
        const approachesFromLeft = animal.kind === "bunbun" || animal.kind === "last-tick";
        const staged = { ...animal, startX: animal.x + (approachesFromLeft ? -22 : 25), startY: animal.y,
          sprite: add(scene.add.sprite(animal.x, animal.y, animal.key, 0).setOrigin(.5, 1).setScale(animal.scale).setDepth(animal.y)),
        };
        return staged;
      });
      // Each added preset brings its selected kitten. Optional licensed sheets
      // never block the portrait; the existing LPC companion remains a fallback.
      const portraitPetActions = Object.freeze({
        3: Object.freeze({ action: "idle", direction: "right", rest: "curled" }),
        4: Object.freeze({ action: "sit", direction: "down" }),
        5: Object.freeze({ action: "idle", direction: "left", rest: "stretched" }),
        6: Object.freeze({ action: "idle", direction: "down", rest: "grooming" }),
      });
      session.people.filter(person => person.number >= 3 && root.ForestPets?.definition(person.avatar.cosmetics?.pet)).forEach(person => {
        // Preset 3 rests at the water's edge while the other kittens remain
        // beside their own guests.
        const x = person.number === 3 ? 250 : person.x + 17;
        const y = person.number === 3 ? 330 : person.y + 20;
        const portrait = portraitPetActions[person.number];
        session.animals.push({ kind: "preset-pet", petId: person.avatar.cosmetics.pet,
          petAccessory: person.avatar.cosmetics.petAccessory || (person.avatar.cosmetics.pet === "last_tick_ribbon" ? "valentine_bow_red" : "none"),
          portraitAction: portrait.action, portraitDirection: portrait.direction, portraitRest: portrait.rest || null,
          x, y, startX: x + 22, startY: y,
          sprite: add(scene.add.sprite(x, y, "lpc-pets", 1).setOrigin(.5, 1).setScale(1.2).setDepth(y)),
          overlay: add(scene.add.sprite(x, y, "lpc-pets", 1).setOrigin(.5, 1).setScale(1.2).setDepth(y + .01).setVisible(false)),
        });
      });
      session.stagedAt = root.performance.now();
      session.reducedMotion = root.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true;
      this.progress(session, "gathering", "여섯 친구와 동물들이 당근집 앞에 모이고 있어요.");
      this.update(session.stagedAt);
    }

    update(now = root.performance.now()) {
      const session = this.session;
      if (!session?.people || session.capturing) return;
      try {
        const elapsed = Math.max(0, now - session.stagedAt);
        const gatherDuration = session.reducedMotion ? 0 : 1600;
        const movement = gatherDuration ? Math.min(1, elapsed / gatherDuration) : 1;
        const moving = movement < 1;
        const ease = 1 - Math.pow(1 - movement, 2);
        session.people.forEach((person, index) => {
          const x = Math.round(person.startX + (person.x - person.startX) * ease);
          const y = Math.round(person.startY + (person.y - person.startY) * ease);
          person.sprite.setPosition(x, y).setDepth(y);
          person.shadow.setPosition(x, y + 1).setDepth(y - 1);
          person.label.setPosition(x, y - 69).setVisible(!moving);
          const context = person.texture.getContext();
          context.clearRect(0, 0, 224, 288);
          if (!root.LpcAvatarEngine.draw(context, person.avatar, {
            direction: moving ? (index < 3 ? "right" : "left") : "down", moving,
            pose: !moving && index % 2 ? "emote" : null,
            frame: session.reducedMotion ? 0 : Math.floor(elapsed / 150),
          }, { x: 16, y: 58, width: 192, height: 192 })) throw new Error("공식 의상 프레임을 그리지 못했어요.");
          if (!moving && typeof context.getImageData === "function") {
            const bounds = alphaBounds(context.getImageData(0, 0, 224, 288).data, 224, 288);
            // Hair and tall hats belong to the complete rendered outfit, so a
            // fixed feet offset cannot safely anchor every official preset.
            if (bounds) person.label.setPosition(x, labelY(y, bounds.y));
          }
          person.texture.refresh();
        });
        session.animals.forEach(animal => this.animateAnimal(animal, elapsed, ease, moving, session.reducedMotion));
        const poseTime = elapsed - gatherDuration;
        if (poseTime >= 0 && poseTime < 550) this.progress(session, "posing", "모두 여기 봐요. 하나, 둘…");
        else if (poseTime >= 550 && poseTime < 1450) this.progress(session, "countdown", "셋! 오늘의 숲을 한 장에 담아요.");
        else if (poseTime >= 1450) { session.capturing = true; void this.capture(session); }
      } catch (error) {
        this.restore(session);
        this.emit("forest-memory-error", session, { message: error.message });
      }
    }

    animateAnimal(animal, elapsed, ease, moving, reducedMotion) {
      const sprite = animal.sprite;
      const x = Math.round(animal.startX + (animal.x - animal.startX) * ease);
      const y = Math.round(animal.startY + (animal.y - animal.startY) * ease);
      sprite.setPosition(x, y).setDepth(y);
      const animals = root.ForestAnimals;
      const travelDirection = animal.startX < animal.x ? "right" : "left";
      if (animal.kind === "preset-pet") {
        const comicPounce = false;
        const portraitPose = animal.kind === "preset-pet" && !moving;
        const action = moving ? "walk" : comicPounce ? "attack" : portraitPose ? animal.portraitAction : "sit";
        const direction = comicPounce ? "left" : portraitPose ? animal.portraitDirection : moving ? travelDirection : "down";
        const actionDuration = root.ForestPets?.actionDurations?.[action];
        let actionElapsed = !moving && Number.isFinite(actionDuration)
          ? Math.max(0, elapsed - 1600) % actionDuration
          : elapsed;
        let idleMs = actionElapsed;
        if (portraitPose && animal.portraitRest === "curled") idleMs = 60000 + Math.max(0, elapsed - 1600) % 1800;
        if (portraitPose && animal.portraitRest === "stretched") idleMs = 120000 + Math.max(0, elapsed - 1600) % 2000;
        if (portraitPose && animal.portraitRest === "grooming") {
          actionElapsed = 7200 + Math.max(0, elapsed - 1600) % 1260;
          idleMs = actionElapsed;
        }
        const pose = root.ForestPets?.pose(animal.petId, { action, direction, elapsed: actionElapsed,
          idleMs, equipment: animal.petAccessory, reducedMotion });
        if (pose && this.scene.textures.exists(pose.key) && (!pose.overlay || this.scene.textures.exists(pose.overlay.key))) {
          sprite.setTexture(pose.key, pose.frame).setOrigin(pose.originX, pose.originY).setScale(pose.scale).setFlipX(Boolean(pose.flipX));
          const visible = Boolean(pose.overlay && this.scene.textures.exists(pose.overlay.key));
          animal.overlay.setVisible(visible);
          if (visible) animal.overlay.setTexture(pose.overlay.key, pose.overlay.frame).setPosition(x, y).setDepth(y + .01)
            .setOrigin(pose.originX, pose.originY).setScale(pose.scale).setFlipX(Boolean(pose.overlay.flipX ?? pose.flipX));
        } else {
          const fallbackFrame = animal.petId === "last_tick_ginger" ? 4 : 1;
          sprite.setTexture("lpc-pets", fallbackFrame).setOrigin(.5, 1).setScale(1.2).setFlipX(false);
          animal.overlay.setVisible(false);
        }
      } else if (animal.kind === "bunbun" || animal.kind === "last-tick") {
        const action = animal.kind === "bunbun" ? (moving ? "jump_forward" : "idle") : (moving ? `hop_${travelDirection}` : "ear_flick_1");
        const clip = animals.rabbitAction(animal.kind, action);
        const pose = animals.rabbitPose(animal.kind, { action, direction: moving ? travelDirection : animal.kind === "bunbun" ? "right" : "down", elapsedMs: elapsed % clip.durationMs, reducedMotion });
        sprite.setTexture(pose.key, pose.frame).setOrigin(pose.originX, pose.originY).setScale(pose.scale).setFlipX(Boolean(pose.flipX));
      } else if (animal.kind === "cow") {
        const pose = animals.cowFrame(moving ? -1 : elapsed % animals.cowReactionDurationMs, { direction: moving ? travelDirection : "left", reducedMotion });
        const row = travelDirection === "left" ? 1 : 3;
        sprite.setTexture(moving ? "forest-cow-walk" : pose.key,
          moving ? row * 4 + (reducedMotion ? 0 : Math.floor(elapsed / 180) % 4) : pose.frame).setOrigin(pose.originX, pose.originY);
      } else {
        const row = moving ? (travelDirection === "right" ? 2 : 1) : 0;
        const stride = moving && !reducedMotion ? Math.floor(elapsed / 150) % 3 : 1;
        sprite.setFrame(animal.kind === "pet" ? row * 9 + animal.column + stride : row * 3 + stride);
      }
    }

    async capture(session) {
      try {
        this.progress(session, "shutter", "당근집 앞 추억을 선명한 PNG로 저장하고 있어요.");
        if (this.session !== session) return;
        const scene = this.scene;
        // Render the same live display-list objects with a dedicated integer
        // 4× camera, never a contact sheet or a screenshot of DOM/HUD controls.
        // An offscreen target avoids resizing the user's responsive viewport.
        const target = scene.make.renderTexture({ x: 0, y: 0, width: FRAME.width * FRAME.scale, height: FRAME.height * FRAME.scale, add: false });
        session.target = target;
        target.camera.setZoom(FRAME.scale);
        target.camera.roundPixels = true;
        target.camera.centerOn(FRAME.x + FRAME.width / 2, FRAME.y + FRAME.height / 2);
        scene.children.depthSort();
        target.draw(scene.children.list.filter(object => object.visible && object !== target));
        // Phaser 3.90 CanvasRenderer.snapshotCanvas clamps an offscreen target
        // to the MAIN canvas size. Read its own backing directly on Canvas to
        // retain the full 2560×1440 photograph even on a small phone viewport.
        const image = target.texture?.canvas
          ? { src: target.texture.canvas.toDataURL("image/png") }
          : await this.bounded(session, new Promise((resolve, reject) => {
            target.snapshot(value => value?.src ? resolve(value) : reject(new Error("사진 읽기에 실패했어요.")), "image/png");
          }), 8000, "사진 생성 시간이 길어지고 있어요. 다시 시도해 주세요.");
        if (this.session !== session) return;
        const dataUrl = image.src;
        const blob = pngBlob(dataUrl);
        // The offscreen render above is the immutable colour original. Keep
        // the live portrait tableau in place until the UI explicitly emits a
        // cancel/exit event; the gradual monochrome effect is display-only CSS.
        session.target?.destroy();
        session.target = null;
        this.emit("forest-memory-ready", session, { blob, dataUrl, width: FRAME.width * FRAME.scale, height: FRAME.height * FRAME.scale });
      } catch (error) {
        if (this.session === session) {
          this.restore(session);
          this.emit("forest-memory-error", session, { message: error?.message || "PNG 사진을 저장하지 못했어요." });
        }
      }
    }

    cancel(message = "", requestId) {
      const session = this.session;
      if (!session || (requestId != null && session.requestId !== requestId)) return false;
      this.restore(session);
      if (message) this.emit("forest-memory-error", session, { message });
      return true;
    }

    restore(session) {
      if (!session || session.restored) return;
      session.restored = true;
      if (this.session === session) this.session = null;
      const scene = this.scene;
      scene.memoryCapturing = false;
      // A shutdown may already have destroyed one plugin/object. Recover the
      // remaining independent state even when a resource is no longer alive.
      const recover = operation => { try { operation(); } catch { /* already disposed */ } };
      session.cleanups.forEach(cleanup => recover(cleanup));
      recover(() => session.target?.destroy());
      session.objects.forEach(object => recover(() => object.destroy()));
      session.textures.forEach(key => recover(() => scene.textures.remove(key)));
      session.visibility.forEach(([object, visible]) => recover(() => { if (object.scene) object.setVisible(visible); }));
      session.animationScales.forEach(([anims, scale]) => recover(() => { anims.timeScale = scale; }));
      if (session.view) {
        recover(() => { scene.input.enabled = session.inputEnabled; });
        recover(() => { scene.tweens.timeScale = session.tweenScale; });
        recover(() => { scene.time.timeScale = session.clockScale; });
        const elapsed = root.performance.now() - session.startedAt;
        const sceneElapsed = Math.max(0, (scene.time?.now ?? session.sceneStartedAt) - session.sceneStartedAt);
        ["actionStartedAt", "actionUntil", "petActionUntil", "forcedUntil"].forEach(key => { if (scene[key] > 0) scene[key] += elapsed; });
        ["ratNextSpawnAt", "ratDespawnAt", "ratTurnAt", "rabbitActionStartedAt", "rabbitActionUntil", "ratHoverUntil", "ratAttackPressedUntil"].forEach(key => { if (scene[key] > 0) scene[key] += sceneElapsed; });
        recover(() => restoreView(scene, session.view));
      }
    }

    destroy() {
      try { this.cancel("장면을 닫아 촬영이 취소되었어요."); }
      finally {
        root.removeEventListener("forest-memory-start", this.onStart);
        root.removeEventListener("forest-memory-cancel", this.onCancel);
      }
    }
  }

  const api = Object.freeze({ NICKNAMES, CAMERA, FRAME, POSITIONS, portraitPresets, alphaBounds, fitWithin, overlapsPortrait, labelY, trimmedTexture, fitImage, pngBlob, saveView, restoreView, Controller });
  root.ForestMemories = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof window === "object" ? window : globalThis);
