from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "frontend" / "assets" / "animals" / "riverduck-v161"
OUT.mkdir(parents=True, exist_ok=True)


def frame(name, wing=0, foot=0, eye=0, lean=0):
    img = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ox, oy = 9 + lean, 20
    # Shadow and water contact.
    d.ellipse((22, 76, 73, 84), fill=(24, 65, 61, 70))
    d.arc((18, 67, 79, 91), 8, 173, fill=(160, 230, 238, 170), width=2)
    # Feet remain below WATERLINE in the renderer crop.
    d.polygon([(36, 82 + foot), (42, 86 + foot), (35, 89 + foot)], fill=(225, 133, 43, 255))
    d.polygon([(54, 82 - foot), (62, 86 - foot), (55, 90 - foot)], fill=(225, 133, 43, 255))
    # Body.
    d.ellipse((ox + 22, oy + 28, ox + 63, oy + 66), fill=(255, 220, 74, 255), outline=(95, 92, 48, 255), width=3)
    d.ellipse((ox + 17, oy + 11, ox + 52, oy + 45), fill=(255, 228, 92, 255), outline=(95, 92, 48, 255), width=3)
    d.polygon(
        [(ox + 12, oy + 27), (ox + 0, oy + 32), (ox + 13, oy + 38)],
        fill=(236, 141, 43, 255),
        outline=(118, 77, 35, 255),
    )
    d.line((ox + 2, oy + 33, ox + 13, oy + 33), fill=(255, 180, 67, 255), width=2)
    d.ellipse((ox + 38, oy + 22 + eye, ox + 43, oy + 27 + eye), fill=(34, 42, 32, 255))
    d.point((ox + 40, oy + 23 + eye), fill=(255, 255, 240, 255))
    d.arc((ox + 28, oy + 20, ox + 38, oy + 31), 205, 330, fill=(105, 88, 45, 255), width=2)
    # Wing.
    d.ellipse(
        (ox + 42, oy + 40 + wing, ox + 69, oy + 60 + wing),
        fill=(237, 187, 55, 255),
        outline=(112, 91, 43, 255),
        width=2,
    )
    d.arc((ox + 47, oy + 44 + wing, ox + 66, oy + 61 + wing), 205, 342, fill=(255, 231, 99, 255), width=2)
    # Tail.
    d.polygon(
        [(ox + 61, oy + 43), (ox + 76, oy + 36), (ox + 68, oy + 54)],
        fill=(255, 226, 86, 255),
        outline=(95, 92, 48, 255),
    )
    d.rectangle((0, 87, 96, 96), fill=(0, 0, 0, 0))
    img.save(OUT / f"{name}.png")


if __name__ == "__main__":
    frame("riverduck", wing=0, foot=0, eye=0)
    frame("idle-2", wing=1, foot=1, eye=1)
    frame("swim-1", wing=-1, foot=1, lean=1)
    frame("swim-2", wing=2, foot=-1, lean=-1)
    frame("flee-1", wing=-3, foot=2, lean=3)
    frame("flee-2", wing=4, foot=-2, lean=-2)
