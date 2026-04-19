"""Generate the Focus Mode app icon (.ico) with smooth rounded rectangle, circle and text."""
from PIL import Image, ImageDraw, ImageFont
import os

# Colors
BG_BLUE = (15, 82, 220)       # Rounded rectangle background
CIRCLE_GOLD = (255, 214, 10)  # Circle
TEXT_DARK = (15, 82, 220)     # Text inside circle

SIZES = [256, 128, 64, 48, 32, 24, 16]
SUPERSAMPLE = 4  # Render at 4x then downscale for smooth anti-aliasing


def _best_font(size):
    """Try common Windows fonts, fall back to default."""
    for name in ("segoeuib.ttf", "segoeui.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_icon(size):
    # Render at higher resolution for smooth edges
    s = size * SUPERSAMPLE
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded rectangle background with generous corner radius
    corner = int(s * 0.22)
    draw.rounded_rectangle([0, 0, s - 1, s - 1], radius=corner, fill=(*BG_BLUE, 255))

    # Circle with padding from edges (18% margin)
    margin = int(s * 0.18)
    draw.ellipse([margin, margin, s - margin, s - margin], fill=(*CIRCLE_GOLD, 255))

    # Text "Focus" centered in the circle
    if size >= 32:
        fs = max(int(s * 0.19), 8)
        font = _best_font(fs)
        text = "Focus"
        bb = draw.textbbox((0, 0), text, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        tx = (s - tw) // 2
        ty = (s - th) // 2 - bb[1]
        draw.text((tx, ty), text, fill=(*TEXT_DARK, 255), font=font)
    elif size >= 24:
        fs = max(int(s * 0.32), 8)
        font = _best_font(fs)
        text = "F"
        bb = draw.textbbox((0, 0), text, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        draw.text(((s - tw) // 2, (s - th) // 2 - bb[1]), text,
                  fill=(*TEXT_DARK, 255), font=font)
    # 16px: just circle on rounded rect, no text

    # Downscale with high-quality resampling for smooth result
    img = img.resize((size, size), Image.LANCZOS)
    return img


def create_icon():
    os.makedirs("assets", exist_ok=True)
    images = [_draw_icon(s) for s in SIZES]
    # Also save a preview PNG
    images[0].save("assets/icon_preview.png")
    images[0].save(
        "assets/icon.ico",
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=images[1:],
    )
    print("Created assets/icon.ico + icon_preview.png")


if __name__ == "__main__":
    create_icon()
