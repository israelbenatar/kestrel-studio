"""Delivery checks that code can measure, so the review loop doesn't estimate them by eye.

    python -m kit.check scene.json                         # rules read from the scene
    python -m kit.check scene.json --video out/final.mp4   # + text contrast on the rendered frames
    python -m kit.check scene.json --channel reels         # 9:16 safe area of Reels/TikTok/Shorts

Each problem prints with a rule id from skill/LEDGER.md. Exit code 1 when any check fails, so a
build can stop on it. Text marked `decor=True` in Comp.text() is skipped: nobody has to read it.

The rules:
- text-height   text a viewer must read is at least 3% of the frame height (at 1350 px: 40 px), the
                smallest that reads on a phone. The main line of a beat should be 5% (68 px); which
                line is the main one is the review's call, not this script's.
- safe-area     text sits inside the frame's margins, and on 9:16 clear of the platform's buttons
                and caption area (nothing below about 82% of the height, nor in the right rail).
- contrast      (with --video) on the frame where the text is fully in, the text holds at least
                3:1 against the brightest or busiest part of the picture behind it.
Text widths are measured with the scene's own font files (--fonts, default the repo's fonts/);
a font that isn't found falls back to about 0.55 em a character, which can be a little wide.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

SAFE = {   # (left, top, right, bottom) margins as a share of the frame
    "default": (0.04, 0.04, 0.04, 0.04),
    "reels": (0.06, 0.10, 0.15, 0.18),      # 9:16: top bar, right action rail, caption and buttons
}


def _val(prop, last=True):
    """A Lottie property's value: static, or its last (or first) keyframe."""
    k = prop["k"]
    if prop.get("a"):
        return k[-1 if last else 0]["s"]
    return k


def _settled(layer) -> float:
    """The frame by which the layer has arrived: opacity at its peak, a rise or spring landed, a
    text reveal finished. A fade out after that doesn't count."""
    t = layer["ip"]
    ks = layer["ks"]
    o = ks.get("o", {})
    if o.get("a"):
        peak = max(k["s"][0] for k in o["k"])
        t = max(t, next(k["t"] for k in o["k"] if k["s"][0] >= peak))
    for key in ("p", "s"):
        p = ks.get(key, {})
        if p.get("a") and len(p["k"]) > 1:
            keys = p["k"]
            # two keys: an eased rise or slide (a slow zoom over the whole life isn't an arrival);
            # more: a baked spring, landed on its last key
            if len(keys) > 2 or keys[1]["t"] - keys[0]["t"] < 3 * 30:
                t = max(t, keys[-1]["t"] if len(keys) > 2 else keys[1]["t"])
    for an in layer.get("t", {}).get("a", []):
        for side in ("s", "e"):
            p = an["s"].get(side)
            if p and p.get("a"):
                t = max(t, p["k"][-1]["t"])
    return t


_FONTS: dict = {}


def _width(line: str, font: str, size: float, tracking: float, fonts: Path | None) -> float:
    from PIL import ImageFont
    key = (font, round(size))
    if key not in _FONTS:
        f = next((fonts / f"{font}{ext}" for ext in (".ttf", ".otf") if fonts and (fonts / f"{font}{ext}").exists()), None)
        _FONTS[key] = ImageFont.truetype(str(f), round(size)) if f else None
    ft = _FONTS[key]
    w = ft.getlength(line) if ft else len(line) * size * 0.55
    return w + tracking / 1000 * size * max(0, len(line) - 1)


def texts(scene: dict, fonts: Path | None = None):
    """Every text layer with its box in frame pixels: (layer, x0, y0, x1, y1, size, colour, ip, op)."""
    comps = {a["id"]: a["layers"] for a in scene["assets"] if "layers" in a}

    def walk(layers, ox, oy, ip, op):
        for L in layers:
            if L["ty"] == 0 and L.get("refId") in comps:
                p, a = _val(L["ks"]["p"]), _val(L["ks"]["a"])
                yield from walk(comps[L["refId"]], ox + p[0] - a[0], oy + p[1] - a[1],
                                max(ip, L["ip"]), min(op, L["op"]))
            elif L["ty"] == 5:
                doc = L["t"]["d"]["k"][0]["s"]
                size, lh = doc["s"], doc.get("lh", doc["s"] * 1.2)
                lines = doc["t"].split("\r")
                w = max(_width(s, doc["f"], size, doc.get("tr", 0), fonts) for s in lines)
                x, y = _val(L["ks"]["p"])[:2]
                x, y = ox + x, oy + y
                x0 = {0: x, 1: x - w, 2: x - w / 2}[doc.get("j", 0)]
                y0 = y - size * 0.75
                y1 = y + (len(lines) - 1) * lh + size * 0.25
                yield L, x0, y0, x0 + w, y1, size, doc["fc"], max(ip, L["ip"]), min(op, L["op"])

    yield from walk(scene["layers"], 0, 0, 0, scene["op"])


def _lum(rgb):
    c = np.asarray(rgb, float)
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return c[..., 0] * 0.2126 + c[..., 1] * 0.7152 + c[..., 2] * 0.0722


def frame(video, t, w, h) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                          "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3) / 255.0


def contrast(img, box, colour, size) -> float | None:
    """The worst-case ratio of the text colour against the picture behind the box: the 10th
    percentile over the pixels that are clear of the letters. The letters' soft edges blend text
    and background, so a band of about 8% of the font size around them is left out."""
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(img.shape[1], x1), min(img.shape[0], y1)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    px = img[y0:y1, x0:x1]
    ink = np.abs(px - np.asarray(colour[:3])).max(axis=2) < 0.25
    r = max(2, int(size * 0.08))
    near = np.zeros_like(ink)
    pad = np.pad(ink, r)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            near |= pad[r + dy:r + dy + ink.shape[0], r + dx:r + dx + ink.shape[1]]
    bg = px[~near]
    if len(bg) < 0.1 * ink.size:
        return None                                  # the box is all text-coloured: nothing to compare
    lt, lb = _lum(colour[:3]), _lum(bg)
    ratio = (np.maximum(lt, lb) + 0.05) / (np.minimum(lt, lb) + 0.05)
    return float(np.percentile(ratio, 10))


def run(scene_path, video=None, channel="default", min_height=0.03, min_contrast=3.0, fonts=None) -> list[str]:
    scene = json.loads(Path(scene_path).read_text())
    W, H, fps = scene["w"], scene["h"], scene["fr"]
    tall = H / W > 1.6
    ml, mt, mr, mb = SAFE["reels" if channel == "reels" or (channel == "default" and tall) else "default"]
    problems = []
    fonts = Path(fonts) if fonts else Path(__file__).resolve().parent.parent / "fonts"
    for L, x0, y0, x1, y1, size, colour, ip, op in texts(scene, fonts):
        if L.get("cl") == "decor" or op <= 0 or ip >= scene["op"]:
            continue
        name = L["nm"]
        if size < round(min_height * H):
            problems.append(f"text-height  {name!r}: {size:.0f} px, needs {round(min_height * H)} px "
                            f"({min_height:.0%} of {H}); mark it decor=True if no one has to read it")
        if x0 < ml * W or x1 > (1 - mr) * W or y0 < mt * H or y1 > (1 - mb) * H:
            problems.append(f"safe-area    {name!r}: box {x0:.0f},{y0:.0f}-{x1:.0f},{y1:.0f} leaves the safe area "
                            f"{ml * W:.0f},{mt * H:.0f}-{(1 - mr) * W:.0f},{(1 - mb) * H:.0f}")
        if video:
            t = min(_settled(L) + 0.1 * fps, op - 1) / fps
            r = contrast(frame(video, t, W, H), (x0, y0, x1, y1), colour, size)
            if r is not None and r < min_contrast:
                problems.append(f"contrast     {name!r}: {r:.1f}:1 at {t:.2f}s, needs {min_contrast}:1; "
                                f"add a backing panel or a soft shade, or move it")
    return problems


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("scene")
    ap.add_argument("--video", help="the render, for the contrast check")
    ap.add_argument("--channel", default="default", choices=["default", "reels", "web"],
                    help="reels: 9:16 platform UI margins (the default for any tall frame); web: plain margins")
    ap.add_argument("--min-height", type=float, default=0.03)
    ap.add_argument("--min-contrast", type=float, default=3.0)
    ap.add_argument("--fonts", help="folder of the scene's fonts (default: the repo's fonts/)")
    a = ap.parse_args()
    probs = run(a.scene, a.video, a.channel, a.min_height, a.min_contrast, a.fonts)
    for p in probs:
        print(p)
    print(f"{len(probs)} problem(s)" if probs else "all checks pass")
    sys.exit(1 if probs else 0)
