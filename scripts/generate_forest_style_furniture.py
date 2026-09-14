from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "frontend" / "assets"
OUT = ASSETS / "furniture-v160"
OUT.mkdir(parents=True, exist_ok=True)

STORAGE_CODES = [
    "tent",
    "light_tent",
    "picnic_table",
    "bbq_table",
    "chair_green",
    "chair_red",
    "picnic_blanket",
    "pond",
    "lantern",
    "fence",
    "flower_cart",
    "flower_pot",
    "mushroom",
    "bench",
    "campfire",
    "mailbox",
    "scarecrow",
    "carrot_crate",
    "watering_can",
    "wheelbarrow",
]
ANIMATED_CODES = ["duck_float", "animated_fountain", "firefly_lantern", "garden_pinwheel"]
ANIMATED_BOUNDS = {
    "duck_float": (10, 25, 129, 116),
    "animated_fountain": (13, 126, 127, 242),
    "firefly_lantern": (21, 249, 118, 370),
    "garden_pinwheel": (29, 373, 109, 487),
}
ISOLATED_WINDOWS = {
    "lantern": (0, 0, 238, 256),
    "flower_cart": (0, 44, 256, 192),
    "flower_pot": (0, 0, 256, 231),
    "mushroom": (0, 0, 256, 230),
    "bench": (0, 0, 238, 256),
    "watering_can": (0, 0, 239, 256),
}


def alpha_bbox(image, minimum_alpha=1):
    alpha = image.getchannel("A")
    if minimum_alpha <= 1:
        return alpha.getbbox()
    mask = alpha.point(lambda value: 255 if value >= minimum_alpha else 0)
    return mask.getbbox()


def fit_on_tile(source, tile_size=256, padding=14):
    bbox = alpha_bbox(source)
    tile = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
    if not bbox:
        return tile
    cropped = source.crop(bbox)
    scale = min((tile_size - padding * 2) / cropped.width, (tile_size - padding * 2) / cropped.height)
    resized = cropped.resize(
        (max(1, round(cropped.width * scale)), max(1, round(cropped.height * scale))), Image.Resampling.LANCZOS
    )
    x = (tile_size - resized.width) // 2
    y = tile_size - padding - resized.height
    tile.alpha_composite(resized, (x, y))
    return tile


def soften_foreground(image, saturation=0.92, contrast=0.96):
    rgb = image.convert("RGB")
    alpha = image.getchannel("A")
    rgb = ImageEnhance.Color(rgb).enhance(saturation)
    rgb = ImageEnhance.Contrast(rgb).enhance(contrast)
    rgb.putalpha(alpha)
    return rgb


def split_storage_atlas():
    atlas = Image.open(ASSETS / "carrot-forest-storage-atlas-v4.png").convert("RGBA")
    for index, code in enumerate(STORAGE_CODES):
        if code == "campfire":
            continue
        x = index % 5 * 256
        y = index // 5 * 256
        wx, wy, ww, wh = ISOLATED_WINDOWS.get(code, (0, 0, 256, 256))
        tile = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        tile.alpha_composite(atlas.crop((x + wx, y + wy, x + wx + ww, y + wy + wh)), (wx, wy))
        soften_foreground(tile).save(OUT / f"{code}.png")


def split_animated_atlas():
    atlas = Image.open(ASSETS / "carrot-forest-animated-objects-v2.png").convert("RGBA")
    for code in ANIMATED_CODES:
        if code == "animated_fountain":
            continue
        left, top, right, bottom = ANIMATED_BOUNDS[code]
        tile = fit_on_tile(atlas.crop((left, top, right, bottom)), 256, 18)
        soften_foreground(tile).save(OUT / f"{code}.png")


def make_pixel_sized(source_name, output_name):
    source = Image.open(ASSETS / source_name).convert("RGBA")
    fitted = fit_on_tile(source, 256, 12)
    bbox = alpha_bbox(fitted, 8)
    if not bbox:
        fitted.save(OUT / output_name)
        return
    cropped = fitted.crop(bbox)
    small = cropped.resize((max(1, cropped.width // 3), max(1, cropped.height // 3)), Image.Resampling.BOX)
    pixel = small.resize(cropped.size, Image.Resampling.NEAREST)
    tile = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    tile.alpha_composite(pixel, (bbox[0], bbox[1]))
    soften_foreground(tile, saturation=0.88, contrast=0.93).save(OUT / output_name)


def make_preview():
    names = [
        "tent",
        "light_tent",
        "picnic_table",
        "bbq_table",
        "chair_green",
        "chair_red",
        "picnic_blanket",
        "pond",
        "lantern",
        "fence",
        "flower_cart",
        "flower_pot",
        "mushroom",
        "bench",
        "mailbox",
        "scarecrow",
        "carrot_crate",
        "watering_can",
        "wheelbarrow",
        "duck_float",
        "firefly_lantern",
        "garden_pinwheel",
        "home-record-player-v160",
        "forest-memory-camera-v160",
    ]
    sheet = Image.new("RGBA", (6 * 180, 4 * 180), (221, 236, 195, 255))
    draw = ImageDraw.Draw(sheet)
    for index, name in enumerate(names):
        image = Image.open(OUT / f"{name}.png").convert("RGBA")
        image.thumbnail((132, 132), Image.Resampling.LANCZOS)
        x = (index % 6) * 180 + (180 - image.width) // 2
        y = (index // 6) * 180 + 8 + (132 - image.height) // 2
        sheet.alpha_composite(image, (x, y))
        draw.text(((index % 6) * 180 + 10, (index // 6) * 180 + 148), name, fill=(28, 70, 42, 255))
    (ROOT / "tmp").mkdir(exist_ok=True)
    sheet.convert("RGB").save(ROOT / "tmp" / "forest-furniture-v160-preview.png")


split_storage_atlas()
split_animated_atlas()
make_pixel_sized("home-record-player-v159.png", "home-record-player-v160.png")
make_pixel_sized("forest-memory-camera-v159.png", "forest-memory-camera-v160.png")
make_preview()
