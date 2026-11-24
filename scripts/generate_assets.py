"""Generate high-resolution Windows icon and branding assets for FontVault."""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"

ICON_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def _load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def build_icon_image(size: int = 256) -> Image.Image:
    """Create a 256x256 RGBA rounded-square icon with typographic monogram."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    margin = int(size * 0.05)
    box_size = size - 2 * margin
    radius = int(size * 0.22)

    # Diagonal gradient from deep indigo (#312E81 / #4F46E5) to cyan (#0891B2)
    grad = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = grad.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2.0 * (size - 1))
            r = int(49 + (14 - 49) * t)
            g = int(46 + (165 - 46) * t)
            b = int(129 + (233 - 129) * t)
            px[x, y] = (r, g, b, 255)

    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        [margin, margin, margin + box_size, margin + box_size],
        radius=radius,
        fill=255,
    )
    img.paste(grad, (0, 0), mask)

    draw = ImageDraw.Draw(img)
    # Subtle glass highlight ring
    draw.rounded_rectangle(
        [margin + 2, margin + 2, margin + box_size - 2, margin + box_size - 2],
        radius=max(4, radius - 2),
        outline=(255, 255, 255, 70),
        width=max(2, size // 64),
    )

    # Inner dark typographic card accent at bottom-right
    accent_pad = int(size * 0.14)
    draw.rounded_rectangle(
        [accent_pad, accent_pad, size - accent_pad, size - accent_pad],
        radius=int(radius * 0.65),
        fill=(15, 23, 42, 65),
        outline=(255, 255, 255, 35),
        width=max(1, size // 128),
    )

    serif_font = _load_font(
        [
            r"C:\Windows\Fonts\georgiab.ttf",
            r"C:\Windows\Fonts\timesbd.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
        ],
        size=int(size * 0.48),
    )
    sans_font = _load_font(
        [
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
        ],
        size=int(size * 0.24),
    )

    # Draw shadow + crisp white "A" and cyan "a"
    main_glyph = "A"
    sub_glyph = "a"
    ax, ay = int(size * 0.21), int(size * 0.22)
    draw.text((ax + 3, ay + 4), main_glyph, font=serif_font, fill=(15, 23, 42, 130))
    draw.text((ax, ay), main_glyph, font=serif_font, fill=(248, 250, 252, 255))

    sx, sy = int(size * 0.59), int(size * 0.44)
    draw.text((sx + 2, sy + 3), sub_glyph, font=sans_font, fill=(15, 23, 42, 120))
    draw.text((sx, sy), sub_glyph, font=sans_font, fill=(165, 243, 252, 255))

    # Baseline typographic rule bar
    bar_y = int(size * 0.77)
    draw.rounded_rectangle(
        [int(size * 0.24), bar_y, int(size * 0.76), bar_y + max(4, size // 36)],
        radius=max(2, size // 64),
        fill=(103, 232, 249, 220),
    )
    return img


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    base_img = build_icon_image(256)
    png_path = ASSETS_DIR / "icon.png"
    ico_path = ASSETS_DIR / "icon.ico"

    base_img.save(png_path, format="PNG")
    base_img.save(ico_path, format="ICO", sizes=ICON_SIZES)
    print(f"Generated {png_path} ({png_path.stat().st_size} bytes)")
    print(f"Generated {ico_path} ({ico_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
