"""Generated art for the launch video, all from brand/brand.json (the site's own tokens).

- aurora(): the site's ground — dark base, rufous / slate / amber radial washes — as one PNG that both
  HyperFrames and kestrel use, so the hand-off between engines is invisible.
- glass(): a glass panel as a PNG in the site's recipe (two-stop fill, hairline edge, top highlight,
  soft lift). Over the smooth aurora a real backdrop blur would be invisible, so a still is exact.
- mark_svg(): the logo mark, for kestrel's SVG layers.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
ART = HERE / "media" / "art"
BRAND = json.loads((HERE / "brand" / "brand.json").read_text())
W, H = 1080, 1350


def hexrgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


def aurora(path: Path = None) -> Path:
    path = path or ART / "aurora.png"
    if path.exists():
        return path
    ART.mkdir(parents=True, exist_ok=True)
    y, x = np.mgrid[0:H, 0:W].astype(float)
    p = BRAND["palette"]
    img = np.zeros((H, W, 3)) + hexrgb(p["background"])
    img += (hexrgb("#121218") - hexrgb(p["background"])) * np.clip(1 - y / (H * .6), 0, 1)[..., None]

    def wash(cx, cy, rx, ry, color, a):
        d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
        return (np.clip(1 - np.sqrt(d), 0, 1) ** 1.6 * a)[..., None] * hexrgb(color)

    img += wash(W * .82, H * .02, W * .75, H * .5, p["accent"], .50)      # rufous, top right
    img += wash(W * .02, H * .40, W * .70, H * .45, "#5E7BFF", .32)        # slate, left
    img += wash(W * .55, H * 1.02, W * .80, H * .42, p["accent2"], .26)    # amber, bottom
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(path)
    return path


def glass(w: int, h: int, r: int, name: str, *, tint=(255, 246, 236), fill=(.11, .04), pad=60) -> tuple[Path, int]:
    """Glass panel w x h (radius r) on a transparent canvas with `pad` px around for the shadow.
    Returns (path, pad): place the image at (x - pad, y - pad) with size (w + 2 pad, h + 2 pad)."""
    path = ART / f"glass-{name}-{w}x{h}.png"
    if path.exists():
        return path, pad
    ART.mkdir(parents=True, exist_ok=True)
    s = 2                                                   # supersample for clean edges
    cw, ch, P, R = (w + 2 * pad) * s, (h + 2 * pad) * s, pad * s, r * s
    box = (P, P, P + w * s - 1, P + h * s - 1)
    shadow = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(shadow).rounded_rectangle((P, P + 24 * s, P + w * s, P + h * s + 24 * s), R, fill=int(255 * .42))
    shadow = shadow.filter(ImageFilter.GaussianBlur(26 * s))
    # fill: 135deg two-stop gradient of the tint
    yy, xx = np.mgrid[0:ch, 0:cw].astype(float)
    t = np.clip(((xx - P) + (yy - P)) / (w * s + h * s), 0, 1)
    a = (fill[0] + (fill[1] - fill[0]) * t)
    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle(box, R, fill=255)
    m = np.asarray(mask, float) / 255
    panel = np.zeros((ch, cw, 4))
    panel[..., :3] = tint
    panel[..., 3] = a * m * 255
    # hairline edge: 140deg gradient, bright at the ends, faint in the middle
    edge = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(edge).rounded_rectangle(box, R, outline=255, width=s)
    e = np.asarray(edge, float) / 255
    te = np.clip(((xx - P) * .77 + (yy - P) * .64) / (w * s * .77 + h * s * .64), 0, 1)
    ea = (.24 - .20 * np.sin(np.pi * te)) * e
    panel[..., 3] = np.maximum(panel[..., 3], ea * 255)
    # inset top highlight
    hl = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(hl).rounded_rectangle((P + s, P + s, P + w * s - 1 - s, P + h * s - 1 - s), R - s, outline=255, width=s)
    top = (yy < P + R * .5 + 2 * s)
    panel[..., 3] = np.maximum(panel[..., 3], np.asarray(hl, float) / 255 * top * .30 * 255)
    panel[..., :3] = np.where(((np.asarray(hl) > 0) & top)[..., None], 255, panel[..., :3])
    sh = np.zeros((ch, cw, 4)); sh[..., 3] = np.asarray(shadow, float) * (1 - m)
    comp = Image.alpha_composite(Image.fromarray(sh.astype(np.uint8), "RGBA"), Image.fromarray(panel.astype(np.uint8), "RGBA"))
    comp.resize((w + 2 * pad, h + 2 * pad), Image.LANCZOS).save(path)
    return path, pad


def mark_svg() -> Path:
    path = ART / "mark.svg"
    ART.mkdir(parents=True, exist_ok=True)
    path.write_text("""<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320" viewBox="0 0 32 32">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F5B544"/><stop offset=".6" stop-color="#E8743B"/><stop offset="1" stop-color="#C9473F"/></linearGradient></defs>
<rect width="32" height="32" rx="9" fill="url(#g)"/>
<path d="M6 19.5c4.5-1 8.3-3.6 10.2-8.3 1.4 3.3 4.3 5.5 9.8 6.1-3.9 1.2-6.6 3.1-8.1 6.2-1.6-2.6-5.4-4-11.9-4z" fill="#1A0F08"/>
<circle cx="18.9" cy="14.6" r="1.05" fill="#F6E7CF"/></svg>""")
    return path


if __name__ == "__main__":
    print(aurora())
    print(glass(920, 330, 30, "terminal"))
    print(mark_svg())


FILM = HERE.parent / "chat-sorting" / "out" / "combined.mp4"
FILM_STILL_T = 15.5


def hero_with_film() -> Path:
    """The site's hero capture with the real film frame laid into its stage. Headless Chromium doesn't
    paint a seeked <video>, so the capture shows a blank stage; the film frame goes in at the
    rectangle Playwright measured (assets/captures/rects.json)."""
    import subprocess
    path = ART / "hero-film.png"
    rects = json.loads((HERE / "assets/captures/rects.json").read_text())
    s, f = rects["scale"], rects["film"]
    frame = ART / "film-still.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(FILM_STILL_T), "-i", str(FILM), "-frames:v", "1", str(frame)], check=True)
    hero = Image.open(HERE / "assets/captures/hero.png").convert("RGB")
    still = Image.open(frame).convert("RGB").resize((round(f["w"] * s), round(f["h"] * s)), Image.LANCZOS)
    # the badge and sound button sit above the film on the page: keep them on top
    keep = [(r, hero.crop(box)) for r in (rects["badge"], rects["sound"])
            for box in [(round(r["x"] * s), round(r["y"] * s), round((r["x"] + r["w"]) * s), round((r["y"] + r["h"]) * s))]]
    hero.paste(still, (round(f["x"] * s), round(f["y"] * s)))
    for r, im in keep:
        hero.paste(im, (round(r["x"] * s), round(r["y"] * s)))
    hero.save(path)
    return path


def shadow(w: int, h: int, r: int, name: str, *, dy=40, blur=45, alpha=.55, edge=.18, pad=120) -> tuple[Path, int]:
    """A soft drop shadow plus a faint hairline for a w x h card, matching the HyperFrames
    `box-shadow: 0 40px 90px rgba(0,0,0,.55), 0 0 0 1px rgba(255,240,225,.18)`. Same (path, pad) contract
    as glass(); draw the card itself on top."""
    path = ART / f"shadow-{name}-{w}x{h}.png"
    if path.exists():
        return path, pad
    ART.mkdir(parents=True, exist_ok=True)
    cw, ch = w + 2 * pad, h + 2 * pad
    sh = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(sh).rounded_rectangle((pad, pad + dy, pad + w, pad + h + dy), r, fill=int(255 * alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); out.putalpha(sh)
    ring = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    ImageDraw.Draw(ring).rounded_rectangle((pad - 1, pad - 1, pad + w, pad + h), r + 1, outline=(255, 240, 225, int(255 * edge)), width=1)
    Image.alpha_composite(out, ring).save(path)
    return path, pad


def measure(text: str, font: str, size: int) -> float:
    """Advance width of `text` in px, from the same font file kestrel draws with."""
    from PIL import ImageFont
    return ImageFont.truetype(str(HERE.parent.parent / "fonts" / f"{font}.ttf"), size).getlength(text)
