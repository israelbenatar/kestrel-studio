"""Track a person from their matte, and pin words to the body.

    from kit.track import silhouette, pin, along
    tr = silhouette("media/person-alpha.mov", fps=24, cache="track.json")   # head and shoulders, per frame
    pin(c, "Now I just write", tr, "head_right", t0=2.4, t1=4.5, ...)       # a word beside the head
    along(c, "CAPTIONS", tr, "shoulders", t0=6.7, t1=8.6, at=0.2, ...)      # a word on the shoulder line

The matte (the alpha channel of `hyperframes remove-background`) gives the person's outline in
each frame; this module measures it: no pose model and no network. It finds:
  head        the middle of the head (x, y), and head_top
  head_right  / head_left: just beside the head, at eye height
  shoulders   the line from the left shoulder top to the right one (two points)
Arms and hands are not in a head-and-shoulders matte: words along an arm need a pose model.
The points are smoothed over a few frames, so a word moves with the person and does not shake.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import numpy as np

from .lottie import LINEAR, Comp, rgb, static


def _frames(video, w, h, fps):
    cmd = ["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps={fps},alphaextract,scale={w}:{h}",
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    while True:
        buf = p.stdout.read(w * h)
        if len(buf) < w * h:
            break
        yield np.frombuffer(buf, np.uint8).reshape(h, w) > 127
    p.wait()


def _smooth(xs, k=5):
    xs = np.asarray(xs, float)
    pad = np.pad(xs, ((k // 2, k // 2), (0, 0)), mode="edge")
    return np.array([pad[i:i + k].mean(0) for i in range(len(xs))])


def _median(xs, k):
    xs = np.asarray(xs, float)
    pad = np.pad(xs, ((k // 2, k // 2), (0, 0)), mode="edge")
    return np.array([np.median(pad[i:i + k], 0) for i in range(len(xs))])


def silhouette(matte, *, fps, size=(1080, 1350), scale=4, shoulder=0.3, cache=None) -> dict:
    """Head and shoulder points of the person in *matte*, one set per frame at *fps*, in frame
    pixels (*size*). *shoulder*: where to look for each shoulder top when the body's bottom edge is not
    in the frame, as a share of the frame width out from the head's middle. *cache*: a JSON file; read it when it exists, else write it."""
    if cache and Path(cache).exists():
        return json.loads(Path(cache).read_text())
    W, H = size
    w, h = W // scale, H // scale
    rows = []
    for m in _frames(matte, w, h, fps):
        ys = np.nonzero(m.any(1))[0]
        if len(ys) == 0:
            rows.append(rows[-1] if rows else [W / 2, H / 3, H / 4, W / 2 - 300, H / 2, W / 2 + 300, H / 2, W / 8])
            continue
        top = ys[0]
        xs = np.nonzero(m[min(top + 8, h - 1)])[0]
        cx0 = xs.mean() if len(xs) else w / 2
        sh = []
        # the shoulder columns come from the body (the bottom row of the matte), not the head, so
        # hair that swings does not move them
        bx = np.nonzero(m[-2])[0]
        bc, bh = (bx.mean(), (bx[-1] - bx[0]) / 2) if len(bx) > 4 else (cx0, shoulder * w)
        for side in (-1, 1):
            col = int(np.clip(bc + side * bh * 0.8, 0, w - 1))
            hit = np.nonzero(m[:, col])[0]
            sh.append((col, hit[0] if len(hit) else h - 1))
        if abs(sh[0][1] - sh[1][1]) > 0.06 * h:               # one column hit hair: shoulders are near level
            low = max(sh[0][1], sh[1][1])
            sh = [(col, low) for col, _ in sh]
        neck = min(s[1] for s in sh)
        head = m[top:max(top + 1, int(top + (neck - top) * 0.75))]
        hy, hx = np.nonzero(head)
        cx, cy = (hx.mean(), top + hy.mean()) if len(hx) else (cx0, top + 20)
        half = (np.percentile(hx, 98) - np.percentile(hx, 2)) / 2 if len(hx) else w / 8   # hair included
        rows.append([cx * scale, cy * scale, top * scale, sh[0][0] * scale, sh[0][1] * scale,
                     sh[1][0] * scale, sh[1][1] * scale, half * scale])
    s = _smooth(_median(rows, 9), 7)
    out = {"fps": fps, "frames": [[round(float(v), 1) for v in r] for r in s]}
    if cache:
        Path(cache).write_text(json.dumps(out))
    return out


def point(tr, name, n):
    """One named point at frame *n*: (x, y), or ((x0, y0), (x1, y1)) for "shoulders"."""
    cx, cy, top, lx, ly, rx, ry, half = tr["frames"][min(n, len(tr["frames"]) - 1)]
    return {"head": (cx, cy), "head_top": (cx, top),
            "head_right": (cx + half + 24, cy), "head_left": (cx - half - 24, cy),
            "shoulders": ((lx, ly), (rx, ry))}[name]


def _baked(c: Comp, pairs):
    out = []
    for n, (t, v) in enumerate(pairs):
        k = {"t": c.f(t), "s": v if isinstance(v, list) else [v]}
        if n < len(pairs) - 1:
            k.update(LINEAR)
        out.append(k)
    return {"a": 1, "k": out}


def _text(c: Comp, text, *, font, size, color, align, t0, t1, pos, rot, fade, name, decor=False):
    c._font(font)
    j = {"left": 0, "right": 1, "center": 2}[align]
    doc = {"s": size, "f": font, "t": text, "j": j, "tr": 0, "lh": size * 1.2, "ls": 0, "fc": rgb(color)}
    op = c.keys((t0, 0), (t0 + fade, 100), (t1 - fade, 100), (t1, 0))
    ks = c._transform(0, 0, opacity=op, pos=_baked(c, pos), rot=_baked(c, rot) if rot else None)
    extra = {"cl": "decor"} if decor else {}
    return c._layer(5, name or text[:24], t0, t1, ks, t={"d": {"k": [{"t": 0, "s": doc}]}, "p": {},
                                                         "m": {"g": 1, "a": static([0, 0])}, "a": []}, **extra)


def pin(c: Comp, text, tr, where, *, t0, t1, dx=0, dy=0, font="Inter-Bold", size=54, color="#16181F",
        align="left", fade=0.15, step=1, name=None):
    """*text* that sits at a body point (*where*: head, head_top, head_right, head_left) plus
    (dx, dy), and moves with the person from t0 to t1. *y* is the text's baseline."""
    pos = []
    for fr in range(int(c.f(t0)), int(c.f(t1)) + 1, step):
        n = round(fr / c.fps * tr["fps"])
        x, y = point(tr, where, n)
        pos.append((fr / c.fps, [x + dx, y + dy, 0]))
    return _text(c, text, font=font, size=size, color=color, align=align, t0=t0, t1=t1, pos=pos, rot=None,
                 fade=fade, name=name)


def along(c: Comp, text, tr, *, t0, t1, at=0.5, lift=12, font="Anton-Regular", size=90, color="#16181F",
          fade=0.15, step=1, name=None):
    """*text* set on the shoulder line, centred at *at* (0 = the left shoulder, 1 = the right),
    turned to the line's slope and *lift* px above it: it rides the shoulders as she moves."""
    pos, rot = [], []
    for fr in range(int(c.f(t0)), int(c.f(t1)) + 1, step):
        n = round(fr / c.fps * tr["fps"])
        (x0, y0), (x1, y1) = point(tr, "shoulders", n)
        a = math.atan2(y1 - y0, x1 - x0)
        x, y = x0 + (x1 - x0) * at, y0 + (y1 - y0) * at
        t = fr / c.fps
        pos.append((t, [x + math.sin(a) * lift, y - math.cos(a) * lift, 0]))
        rot.append((t, math.degrees(a)))
    return _text(c, text, font=font, size=size, color=color, align="center", t0=t0, t1=t1, pos=pos, rot=rot,
                 fade=fade, name=name)
