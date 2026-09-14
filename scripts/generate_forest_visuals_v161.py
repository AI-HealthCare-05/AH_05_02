from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "frontend" / "assets"
OUT_DIR = ASSETS / "furniture-v161"
OUT_DIR.mkdir(exist_ok=True)


def shadow(draw, cx, cy, rx, ry, alpha=58):
    draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=(31, 49, 35, alpha))


def draw_integrated_record_player(draw):
    # Coordinates are on the 1536x1024 room background. This places the player
    # on the right-side cabinet so it reads as part of the painted room.
    x, y = 1218, 324
    shadow(draw, x + 42, y + 53, 48, 8, 18)
    draw.rounded_rectangle((x + 8, y + 34, x + 88, y + 62), radius=7, fill=(112, 75, 47), outline=(83, 54, 36), width=2)
    draw.rounded_rectangle(
        (x + 18, y + 42, x + 76, y + 56), radius=4, fill=(166, 111, 64), outline=(106, 70, 43), width=2
    )
    draw.line((x + 22, y + 57, x + 72, y + 57), fill=(216, 151, 78), width=2)
    draw.ellipse((x + 17, y + 5, x + 63, y + 50), fill=(64, 48, 40), outline=(89, 59, 40), width=2)
    draw.ellipse((x + 27, y + 16, x + 53, y + 41), fill=(29, 31, 26))
    draw.ellipse((x + 37, y + 26, x + 46, y + 34), fill=(226, 180, 94), outline=(100, 68, 42), width=1)
    draw.arc((x + 58, y + 14, x + 91, y + 48), 198, 312, fill=(225, 185, 111), width=3)
    draw.line((x + 78, y + 33, x + 59, y + 44), fill=(81, 60, 41), width=2)
    draw.ellipse((x + 56, y + 42, x + 63, y + 49), fill=(225, 184, 103), outline=(81, 60, 41), width=1)


def make_home():
    home = Image.open(ASSETS / "carrot-forest-home-v3.png").convert("RGBA")
    draw = ImageDraw.Draw(home)
    draw_integrated_record_player(draw)
    home.save(ASSETS / "carrot-forest-home-v5.png")


def alpha_crop(image):
    alpha = image.getchannel("A")
    bounds = alpha.getbbox()
    return image.crop(bounds) if bounds else image


def paste_grounded(background, sprite, world_x, world_y, world_width, world_height):
    body = alpha_crop(sprite).resize((world_width * 2, world_height * 2), Image.Resampling.LANCZOS)
    x = int(world_x * 2 - body.width / 2)
    y = int(world_y * 2 - body.height)
    background.alpha_composite(body, (x, y))


def make_world():
    world = Image.open(ASSETS / "carrot-forest-world-v6.png").convert("RGBA")
    draw = ImageDraw.Draw(world)
    draw_integrated_field_lantern(draw, 350 * 2, 304 * 2)
    draw_integrated_field_lantern(draw, 632 * 2, 324 * 2)
    draw_integrated_field_camera(draw, 696 * 2, 344 * 2)
    world.save(ASSETS / "carrot-forest-world-v7.png")


def draw_integrated_field_lantern(draw, cx, ground_y):
    shadow(draw, cx + 2, ground_y + 5, 24, 6, 18)
    draw.line((cx - 3, ground_y - 49, cx - 3, ground_y - 7), fill=(104, 82, 45, 245), width=4)
    draw.line((cx - 3, ground_y - 47, cx + 16, ground_y - 47), fill=(117, 91, 50, 245), width=3)
    draw.line((cx + 15, ground_y - 46, cx + 15, ground_y - 38), fill=(86, 77, 45, 245), width=2)
    draw.rounded_rectangle(
        (cx + 6, ground_y - 37, cx + 26, ground_y - 13), radius=4, fill=(116, 82, 45), outline=(97, 74, 42), width=1
    )
    draw.rounded_rectangle(
        (cx + 10, ground_y - 31, cx + 22, ground_y - 17), radius=2, fill=(223, 166, 75), outline=(143, 91, 43), width=1
    )
    draw.rectangle((cx - 5, ground_y - 7, cx + 1, ground_y + 1), fill=(82, 112, 51))
    for px, py, rx, ry, color in [
        (-15, -1, 10, 6, (86, 132, 60, 205)),
        (5, 0, 9, 5, (96, 144, 64, 190)),
        (20, -2, 7, 5, (74, 118, 54, 195)),
    ]:
        draw.ellipse((cx + px - rx, ground_y + py - ry, cx + px + rx, ground_y + py + ry), fill=color)


def draw_integrated_field_camera(draw, cx, ground_y):
    shadow(draw, cx, ground_y + 5, 38, 8, 18)
    for x2, y2 in [(cx - 26, ground_y + 3), (cx + 27, ground_y + 3), (cx + 1, ground_y + 4)]:
        draw.line((cx, ground_y - 29, x2, y2), fill=(91, 69, 42), width=3)
        draw.line((cx, ground_y - 29, x2, y2), fill=(143, 96, 54), width=1)
    draw.rounded_rectangle(
        (cx - 32, ground_y - 62, cx + 31, ground_y - 29), radius=6, fill=(124, 82, 49), outline=(99, 80, 45), width=2
    )
    draw.rounded_rectangle(
        (cx - 24, ground_y - 56, cx + 23, ground_y - 35), radius=4, fill=(171, 112, 63), outline=(116, 71, 39), width=1
    )
    draw.ellipse((cx - 16, ground_y - 57, cx + 15, ground_y - 26), fill=(65, 63, 48), outline=(86, 81, 47), width=2)
    draw.ellipse((cx - 8, ground_y - 49, cx + 8, ground_y - 33), fill=(91, 117, 95), outline=(54, 63, 40), width=1)
    draw.ellipse((cx, ground_y - 44, cx + 5, ground_y - 39), fill=(213, 229, 202, 145))
    draw.rounded_rectangle(
        (cx - 22, ground_y - 70, cx + 6, ground_y - 60), radius=4, fill=(132, 84, 49), outline=(99, 80, 45), width=1
    )
    draw.rounded_rectangle(
        (cx + 11, ground_y - 66, cx + 27, ground_y - 57), radius=3, fill=(174, 116, 63), outline=(99, 80, 45), width=1
    )
    for px, py, rx, ry in [(-35, 0, 8, 5), (31, 0, 7, 5), (0, 2, 7, 5)]:
        draw.ellipse((cx + px - rx, ground_y + py - ry, cx + px + rx, ground_y + py + ry), fill=(77, 120, 55, 190))


def make_camera():
    scale = 4
    img = Image.new("RGBA", (256 * scale, 256 * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def p(box):
        return tuple(int(v * scale) for v in box)

    shadow(d, 128 * scale, 224 * scale, 76 * scale, 17 * scale, 46)
    d.line(p((114, 132, 75, 224)), fill=(70, 67, 49, 255), width=9 * scale)
    d.line(p((142, 132, 184, 224)), fill=(70, 67, 49, 255), width=9 * scale)
    d.line(p((128, 134, 128, 222)), fill=(87, 73, 49, 255), width=10 * scale)
    d.rounded_rectangle(
        p((66, 62, 190, 138)), radius=16 * scale, fill=(112, 77, 51, 255), outline=(38, 64, 42, 255), width=6 * scale
    )
    d.rounded_rectangle(
        p((78, 73, 178, 127)), radius=10 * scale, fill=(159, 108, 63, 255), outline=(80, 55, 41, 255), width=4 * scale
    )
    d.ellipse(p((98, 70, 158, 130)), fill=(54, 65, 55, 255), outline=(30, 51, 35, 255), width=6 * scale)
    d.ellipse(p((110, 82, 146, 118)), fill=(92, 128, 110, 255), outline=(28, 47, 34, 255), width=4 * scale)
    d.ellipse(p((121, 93, 134, 106)), fill=(214, 242, 221, 210))
    d.rounded_rectangle(
        p((86, 45, 143, 70)), radius=11 * scale, fill=(133, 92, 55, 255), outline=(40, 64, 42, 255), width=5 * scale
    )
    d.rounded_rectangle(
        p((151, 54, 184, 77)), radius=8 * scale, fill=(181, 127, 72, 255), outline=(40, 64, 42, 255), width=4 * scale
    )
    for x, y, r, color in [
        (72, 211, 9, (84, 131, 69, 230)),
        (186, 214, 8, (91, 143, 73, 230)),
        (124, 223, 10, (71, 116, 63, 230)),
    ]:
        d.ellipse(p((x - r, y - r, x + r, y + r)), fill=color)
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    img.save(OUT_DIR / "forest-memory-camera-v161.png")


def make_lantern():
    scale = 4
    img = Image.new("RGBA", (256 * scale, 256 * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def p(box):
        return tuple(int(v * scale) for v in box)

    shadow(d, 128 * scale, 217 * scale, 56 * scale, 15 * scale, 48)
    d.rounded_rectangle(
        p((92, 106, 164, 185)), radius=16 * scale, fill=(96, 79, 56, 255), outline=(38, 67, 43, 255), width=6 * scale
    )
    d.rounded_rectangle(
        p((104, 116, 152, 174)),
        radius=11 * scale,
        fill=(249, 210, 122, 212),
        outline=(103, 75, 43, 255),
        width=3 * scale,
    )
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse(p((72, 82, 184, 202)), fill=(255, 209, 107, 58))
    glow = glow.filter(ImageFilter.GaussianBlur(18 * scale))
    img.alpha_composite(glow)
    d = ImageDraw.Draw(img)
    d.arc(p((101, 71, 155, 123)), 190, 350, fill=(55, 69, 45, 255), width=5 * scale)
    d.rectangle(p((88, 183, 168, 204)), fill=(91, 70, 48, 255))
    d.rounded_rectangle(
        p((76, 199, 180, 219)), radius=10 * scale, fill=(84, 91, 58, 255), outline=(41, 65, 44, 255), width=4 * scale
    )
    for x, y, w, h in [(75, 196, 18, 24), (162, 195, 23, 28), (104, 205, 18, 25)]:
        d.ellipse(p((x, y, x + w, y + h)), fill=(75, 129, 63, 230))
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    img.save(OUT_DIR / "lantern.png")


def make_firefly_lantern():
    scale = 4
    img = Image.new("RGBA", (256 * scale, 256 * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def p(box):
        return tuple(int(v * scale) for v in box)

    shadow(d, 128 * scale, 224 * scale, 66 * scale, 14 * scale, 42)
    d.line(p((116, 65, 116, 212)), fill=(74, 71, 47, 255), width=13 * scale)
    d.line(p((118, 67, 173, 67)), fill=(74, 71, 47, 255), width=12 * scale)
    d.line(p((168, 69, 168, 98)), fill=(74, 71, 47, 255), width=6 * scale)
    d.rounded_rectangle(
        p((139, 92, 197, 151)), radius=12 * scale, fill=(92, 73, 53, 255), outline=(37, 66, 42, 255), width=5 * scale
    )
    d.rounded_rectangle(
        p((151, 103, 185, 140)),
        radius=8 * scale,
        fill=(253, 219, 132, 200),
        outline=(109, 78, 45, 255),
        width=3 * scale,
    )
    for x, y in [(66, 211), (91, 207), (135, 214), (188, 213)]:
        d.ellipse(p((x - 12, y - 9, x + 16, y + 15)), fill=(80, 139, 68, 230))
    for x, y in [(74, 190), (182, 76), (205, 117)]:
        d.ellipse(p((x - 3, y - 3, x + 3, y + 3)), fill=(255, 240, 151, 180))
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    img.save(OUT_DIR / "firefly_lantern.png")


def make_animated_objects():
    source = Image.open(ASSETS / "carrot-forest-animated-objects-v2.png").convert("RGBA")
    sheet = source.copy()
    fixture = Image.open(OUT_DIR / "firefly_lantern.png").convert("RGBA")
    # Replace the four firefly-lantern fixture frames in the source atlas.
    boxes = [(21, 249, 118, 370), (150, 249, 247, 370), (279, 249, 376, 370), (407, 249, 504, 370)]
    for box in boxes:
        frame = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        scaled = fixture.resize((100, 100), Image.Resampling.LANCZOS)
        frame.alpha_composite(scaled, (14, 22))
        sheet.alpha_composite(frame, (box[0] - 16, box[1] - 4))
    sheet.save(ASSETS / "carrot-forest-animated-objects-v3.png")


if __name__ == "__main__":
    make_home()
    make_camera()
    make_lantern()
    make_firefly_lantern()
    make_animated_objects()
    make_world()
