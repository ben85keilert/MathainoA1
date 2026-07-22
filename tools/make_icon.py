

"""Erzeugt die App-Icons für „Μαθαίνω A1".

Reproduzierbar mit Pillow: griechisch-blauer Verlauf, weißes „μ" (erster
Buchstabe von Μαθαίνω) und eine goldene „A1"-Plakette. Aufruf:

    python tools/make_icon.py

Ausgabe in assets/:
- icon.png          Vollflächiges Launcher-Icon (iOS, Web, Desktop, Splash)
- icon_android.png  Adaptive-Vordergrund (transparent, Motiv in der Safe
                    Zone) — der Rest wird von android.adaptive_icon_background
                    in pyproject.toml (#1565C0) gefüllt und vom System maskiert

Flet nutzt diese Dateien beim `flet build` automatisch (assets/).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 1024
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
FONT = "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf"

# Griechisch-Blau (Flaggenblau) als Verlauf, weißes Glyph, goldene Plakette
TOP = (21, 101, 192)      # #1565C0
BOTTOM = (10, 58, 130)    # #0A3A82
WHITE = (255, 255, 255)
GOLD = (245, 197, 66)     # #F5C542
GOLD_TEXT = (13, 55, 110)


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _fit_font(text: str, target_px: int) -> ImageFont.FreeTypeFont:
    """Font-Größe so wählen, dass die Glyphenhöhe target_px erreicht."""
    size = target_px
    for _ in range(40):
        font = ImageFont.truetype(FONT, size)
        h = font.getbbox(text)[3] - font.getbbox(text)[1]
        if abs(h - target_px) <= 2 or size > 4000:
            return font
        size = max(1, round(size * target_px / max(1, h)))
    return ImageFont.truetype(FONT, size)


def _draw_centered(draw, xy, text, font, fill):
    """Zeichnet text an der optischen Mitte von xy (ignoriert Font-Ränder)."""
    l, t, r, b = font.getbbox(text)
    cx, cy = xy
    draw.text((cx - (l + r) / 2, cy - (t + b) / 2), text, font=font, fill=fill)


def _draw_motif(draw, cy_mu: float, mu_px: int, a1_px: int,
                gap_factor: float = 0.52) -> None:
    """Zeichnet das Motiv μ + goldene „A1"-Plakette, um cy_mu zentriert.
    gap_factor steuert den Abstand der Plakette unter der μ-Mitte."""
    mu_font = _fit_font("μ", mu_px)
    _draw_centered(draw, (SIZE / 2, cy_mu), "μ", mu_font, WHITE)

    a1_font = _fit_font("A1", a1_px)
    l, t, r, b = a1_font.getbbox("A1")
    tw, th = r - l, b - t
    pad_x, pad_y = a1_px * 0.40, a1_px * 0.22
    bw, bh = tw + 2 * pad_x, th + 2 * pad_y
    # Plakette unter das μ setzen (μ hat rechts eine Unterlänge)
    by = cy_mu + mu_px * gap_factor
    bx = (SIZE - bw) / 2
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=bh / 2, fill=GOLD)
    _draw_centered(draw, (bx + bw / 2, by + bh / 2), "A1", a1_font, GOLD_TEXT)


def build_full() -> Image.Image:
    """Vollflächiges Icon mit Verlauf (iOS/Web/Desktop/Splash)."""
    img = Image.new("RGB", (SIZE, SIZE), TOP)
    px = img.load()
    for y in range(SIZE):
        color = _lerp(TOP, BOTTOM, y / (SIZE - 1))
        for x in range(SIZE):
            px[x, y] = color
    _draw_motif(ImageDraw.Draw(img), cy_mu=SIZE * 0.36, mu_px=470, a1_px=150)
    return img


def build_android_foreground() -> Image.Image:
    """Adaptive-Vordergrund: transparent, Motiv kleiner in der Safe Zone
    (zentrale ~62 %), damit die System-Maske nichts Wichtiges beschneidet."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    _draw_motif(ImageDraw.Draw(img), cy_mu=SIZE * 0.44, mu_px=330, a1_px=104)
    return img


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    full = build_full()
    full.save(ASSETS / "icon.png")
    build_android_foreground().save(ASSETS / "icon_android.png")
    full.resize((256, 256), Image.LANCZOS).save(ASSETS / "icon_preview.png")
    print(f"geschrieben: {ASSETS / 'icon.png'}, icon_android.png "
          f"({full.size[0]}x{full.size[1]})")


if __name__ == "__main__":
    main()
