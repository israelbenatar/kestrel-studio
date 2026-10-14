"""Film finish: a post-pass that gives a flat render light, air and texture.

    python -m kit.finish in.mp4 out.mp4 [--leak 0.16] [--glow 0.08] [--grain 5] [--vignette 0.22]
                                        [--warmth 0.0] [--flash 2.6,15.4,...]

What it adds, cheapest first:
- **grade**: a touch of warmth and contrast, kept in YUV (an RGB colour-balance pass costs ~3x);
- **glow**: a blurred copy screened back on, so highlights bloom softly;
- **light leak**: slow warm light drifting in from the frame edges, brightening briefly at each
  *flash* time (put them on your cuts);
- **grain** and **vignette**.

The light field is computed in numpy at 1/8 resolution and streamed into FFmpeg, which scales it
up (it is smooth, so nothing is lost) and screens it on. Doing the same as a full-frame shader on
the CPU costs ~1 s per 1080p frame; this costs a few ms.

The light-leak and glow maths are ported from the MIT-licensed shader library
github.com/shader-effects-inc/shaders (LightLeak, Glow, FilmGrain, Vignette), (c) 2026 Shader
Effects Inc.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

import numpy as np

# warm leak palette: amber, rose, honey (linear-ish RGB, 0..1)
LEAK_COLORS = np.array([[1.00, 0.62, 0.42], [1.00, 0.45, 0.42], [1.00, 0.78, 0.60]], dtype=np.float32)


def probe(path) -> tuple[int, int, float, float]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    s = d["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return s["width"], s["height"], float(num) / float(den), float(d["format"]["duration"])


def _smooth(x):
    return x * x * (3 - 2 * x)


def leak_frame(t: float, w: int, h: int, flashes: list[float], strength: float, seed: int = 7) -> np.ndarray:
    """The light field at time t, (h, w, 3) float32 in 0..1. Three soft lobes orbit just outside
    the frame edges; their sum is shaped so it never covers the middle of the frame."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / w, yy / h
    aspect = w / h
    field = np.zeros((h, w, 3), np.float32)
    rng = np.random.default_rng(seed)
    phases = rng.uniform(0, 2 * math.pi, size=(3, 3))
    for i in range(3):
        # each lobe drifts around the frame's rim on its own slow orbit
        a = phases[i, 0] + t * (0.09 + 0.04 * i)
        cx = 0.5 + 0.72 * math.cos(a) + 0.05 * math.sin(t * 0.31 + phases[i, 1])
        cy = 0.5 + 0.72 * math.sin(a * 1.13) + 0.05 * math.cos(t * 0.27 + phases[i, 2])
        r = 0.55 + 0.12 * math.sin(t * 0.21 + i)
        d2 = ((u - cx) * aspect) ** 2 + (v - cy) ** 2
        lobe = np.exp(-d2 / (2 * (r * 0.5) ** 2))
        breathe = 0.65 + 0.35 * math.sin(t * (0.35 + 0.1 * i) + phases[i, 1])
        field += lobe[..., None] * LEAK_COLORS[i] * breathe
    # a flash at each cut: the leak swells for ~0.9 s, peaking 0.25 s in
    boost = 0.0
    for ft in flashes:
        dt = t - ft + 0.25
        if 0 <= dt <= 0.9:
            boost = max(boost, math.sin(math.pi * dt / 0.9) ** 2)
    # keep the centre clear: light lives at the edges
    edge = np.clip(((u - 0.5) * 2) ** 2 + ((v - 0.5) * 2) ** 2, 0, 1) ** 0.8
    gain = strength * (0.55 + 1.6 * boost)
    return np.clip(field * (0.25 + 0.75 * edge)[..., None] * gain, 0, 1)


def finish(src, dst, *, leak=0.16, glow=0.08, grain=5, vignette=0.22, warmth=0.0, flashes=(), scale=8,
           crf=18, preset="medium"):
    w, h, fps, dur = probe(src)
    lw, lh = max(8, w // scale), max(8, h // scale)
    n = math.ceil(dur * fps)
    graph = [
        # grade in YUV: warmth = a little less blue, a little more red in the chroma planes
        f"[0:v]eq=contrast=1.04:saturation=1.06:gamma=0.985,"
        f"lutyuv=u='val-{warmth * 60:.1f}':v='val+{warmth * 40:.1f}',format=gbrp,split=2[base][g]",
        f"[g]gblur=sigma={max(w, h) / 60:.1f}[blur]",
        f"[base][blur]blend=all_mode=screen:all_opacity={glow}[glowed]",
        f"[1:v]scale={w}:{h}:flags=bicubic,format=gbrp[leak]",
        "[glowed][leak]blend=all_mode=screen[lit]",
        f"[lit]format=yuv420p,vignette=angle={vignette:.3f}:mode=forward,"
        f"noise=c0s={grain}:c0f=t+u:c1s={grain // 3}:c1f=t,format=yuv420p[v]",
    ]
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", str(src),
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{lw}x{lh}", "-r", f"{fps}", "-i", "-",
           "-filter_complex", ";".join(graph), "-map", "[v]", "-map", "0:a?", "-c:a", "copy",
           "-c:v", "libx264", "-crf", str(crf), "-preset", preset, "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", str(dst)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for k in range(n):
            fr = leak_frame(k / fps, lw, lh, list(flashes), leak) if leak > 0 else np.zeros((lh, lw, 3), np.float32)
            proc.stdin.write((fr * 255).astype(np.uint8).tobytes())
    except BrokenPipeError:
        pass
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"finish: ffmpeg failed: {' '.join(cmd)}")
    return Path(dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--leak", type=float, default=0.16)
    ap.add_argument("--glow", type=float, default=0.08)
    ap.add_argument("--grain", type=int, default=5)
    ap.add_argument("--vignette", type=float, default=0.22, help="vignette angle in radians (0 = off)")
    ap.add_argument("--warmth", type=float, default=0.0)
    ap.add_argument("--flash", default="", help="comma-separated cut times (s) where the leak swells")
    a = ap.parse_args()
    flashes = [float(x) for x in a.flash.split(",") if x.strip()]
    finish(a.src, a.dst, leak=a.leak, glow=a.glow, grain=a.grain, vignette=a.vignette, warmth=a.warmth,
           flashes=flashes)
    print(a.dst)


if __name__ == "__main__":
    main()
