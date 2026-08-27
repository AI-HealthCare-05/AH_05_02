(() => {
  "use strict";

  const CELL_WIDTH = 224;
  const CELL_HEIGHT = 288;
  const HEAD_CUT = 166;
  const directionRows = { down: 0, up: 1, left: 2, right: 3 };
  const directionColumns = { down: 0, up: 1, left: 2, right: 3 };

  function framePosition(options, rows) {
    const direction = directionRows[options.direction] == null ? "down" : options.direction;
    if (options.mounted) {
      return {
        row: options.moving && rows === 6 ? 5 : 4,
        column: directionColumns[direction],
      };
    }
    return {
      row: directionRows[direction],
      column: options.moving ? Number(options.frame || 0) % 4 : 0,
    };
  }

  function drawSource(context, image, frame, destination) {
    context.drawImage(
      image,
      frame.column * CELL_WIDTH,
      frame.row * CELL_HEIGHT,
      CELL_WIDTH,
      CELL_HEIGHT,
      destination.x,
      destination.y,
      destination.width,
      destination.height,
    );
  }

  function drawAccessory(context, options, destination) {
    if (options.direction === "up") return;
    context.save();
    context.translate(destination.x, destination.y);
    context.scale(destination.width / CELL_WIDTH, destination.height / CELL_HEIGHT);
    context.imageSmoothingEnabled = false;
    const directionOffset = options.direction === "left" ? -7 : options.direction === "right" ? 7 : 0;
    const glasses = options.glasses !== "none" ? options.glasses : ["round_glasses", "star_glasses"].includes(options.accessory) ? options.accessory : "none";
    if (glasses !== "none") {
      context.strokeStyle = glasses === "star_glasses" || glasses === "sun" ? "#51284f" : "#27353d";
      context.lineWidth = 4;
      context.strokeRect(82 + directionOffset, 108, 24, 18);
      context.strokeRect(116 + directionOffset, 108, 24, 18);
      context.fillStyle = context.strokeStyle;
      context.fillRect(106 + directionOffset, 114, 10, 4);
    }
    if (options.accessory === "red_scarf") {
      context.fillStyle = "#b92f34";
      context.fillRect(77 + directionOffset, 157, 72, 10);
      context.fillStyle = "#e14b49";
      context.fillRect(86 + directionOffset, 156, 54, 5);
    }
    if (options.accessory === "carrot_bag" && options.direction !== "left") {
      context.fillStyle = "#b95824";
      context.fillRect(146 + directionOffset, 176, 28, 42);
      context.fillStyle = "#ef8632";
      context.fillRect(151 + directionOffset, 181, 18, 31);
    }
    if (options.accessory === "sprout_hat" || options.hat === "headband") {
      context.fillStyle = options.hat === "headband" ? "#cb3d45" : "#3a8e48";
      context.fillRect(72 + directionOffset, 61, 80, 10);
      if (options.accessory === "sprout_hat") {
        context.fillRect(107 + directionOffset, 40, 9, 22);
        context.fillRect(116 + directionOffset, 42, 20, 9);
      }
    }
    context.restore();
  }

  function drawFrame(context, sources, options, destination = {}) {
    const target = {
      x: destination.x || 0,
      y: destination.y || 0,
      width: destination.width || CELL_WIDTH,
      height: destination.height || CELL_HEIGHT,
    };
    const outfit = sources[options.outfitPreset] || sources[options.preset];
    const hair = sources[options.hairPreset] || sources[options.preset] || outfit;
    if (!outfit?.image || !hair?.image) return false;
    const outfitFrame = framePosition(options, outfit.rows);
    const hairFrame = framePosition(options, hair.rows);
    context.save();
    context.imageSmoothingEnabled = false;
    drawSource(context, outfit.image, outfitFrame, target);
    const cutHeight = target.height * HEAD_CUT / CELL_HEIGHT;
    context.clearRect(target.x, target.y, target.width, cutHeight);
    context.beginPath();
    context.rect(target.x, target.y, target.width, cutHeight + 3);
    context.clip();
    drawSource(context, hair.image, hairFrame, target);
    context.restore();
    drawAccessory(context, options, target);
    return true;
  }

  window.CarrotAvatarCompositor = { CELL_WIDTH, CELL_HEIGHT, drawFrame, framePosition };
})();
