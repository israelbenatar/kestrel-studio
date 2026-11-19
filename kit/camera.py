"""Frame a screen capture on what the viewer should look at: smooth zooms in and out, driven by the
focus log the capture script wrote (kit/capture.cjs), not by guessing from pixels.

    from kit.camera import load, screen
    focus = load("assets/captures/02-reply.focus.json")
    shots = screen(c, "assets/captures/02-reply.webm", focus, 90, 220, 900, 560,
                   start=4.0, ip=4.0, op=12.0, radius=24)
    for s in shots: print(s)          # when each move starts, on what, at what zoom

The rules:
- Every change of subject is one smooth move that starts as the subject comes up and settles in
  about *move* seconds, easing in and out. A zoom out is as smooth as a zoom in.
- Each frame holds at least *hold* seconds. Subjects that come faster than that share one frame
  wide enough to hold them all, instead of the camera hopping between them.
- Small changes of the subject (a box that grows by a line, a pointer move) don't move the camera.
- The picture always fills the frame: no zoom wider than the recording, no empty background.
- Never tighter than *max_scale* output pixels per recorded pixel, where the capture goes soft.
The capture is placed in a precomp, so the zoom stays inside its card (and its corner radius).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from kit.lottie import LINEAR, Comp


@dataclass
class Shot:
    t: float                         # clip seconds when the move to this frame starts
    names: list[str]
    box: tuple | None                # subject in recording pixels (x, y, w, h); None = the whole recording
    cx: float = 0.0
    cy: float = 0.0
    scale: float = 1.0               # output pixels per recording pixel once settled
    limited: bool = False            # the subject wanted a tighter frame than max_scale allows

    def __str__(self):
        what = "+".join(dict.fromkeys(self.names))
        tight = " (held at max_scale: the subject is smaller than the capture can show sharply)" if self.limited else ""
        return f"{self.t:7.2f}s  {what:<28} x{self.scale:.2f}{tight}"


def load(path) -> dict:
    """The focus log, with boxes scaled from viewport CSS pixels to video pixels."""
    d = json.loads(Path(path).read_text())
    kx = d["video"][0] / d["viewport"][0]
    ky = d["video"][1] / d["viewport"][1]
    ev = [(t, n, None if b is None else (b[0] * kx, b[1] * ky, b[2] * kx, b[3] * ky)) for t, n, b in d["events"]]
    return {"size": tuple(d["video"]), "events": ev, "marks": [tuple(m) for m in d.get("marks", [])]}


def _union(a, b):
    if a is None or b is None:
        return None
    x0, y0 = min(a[0], b[0]), min(a[1], b[1])
    x1, y1 = max(a[0] + a[2], b[0] + b[2]), max(a[1] + a[3], b[1] + b[3])
    return (x0, y0, x1 - x0, y1 - y0)


def _fit(box, src, view, pad, max_scale):
    """Centre and scale that show *box* whole in a frame of *view*, inside the recording."""
    sw, sh = src
    vw, vh = view
    cover = max(vw / sw, vh / sh)                    # widest frame that still fills the view
    if box is None:
        return sw / 2, sh / 2, cover, False
    x, y, w, h = box[0] - pad, box[1] - pad, box[2] + 2 * pad, box[3] + 2 * pad
    s = min(vw / w, vh / h)
    limited = s > max_scale
    s = min(max(s, cover), max(max_scale, cover))
    fw, fh = vw / s, vh / s                          # frame size in recording pixels
    cx = min(max(x + w / 2, fw / 2), sw - fw / 2)
    cy = min(max(y + h / 2, fh / 2), sh - fh / 2)
    return cx, cy, s, limited


def plan(events, src, view, *, move=0.9, hold=2.0, pad=16, max_scale=2.0, start_wide=True) -> list[Shot]:
    """The camera's frames for a list of (t, name, box) focus events, after the rules above."""
    shots: list[Shot] = []
    if start_wide and (not events or events[0][0] > 0.3):
        shots.append(Shot(0.0, ["start"], None))
    for t, name, box in sorted(events, key=lambda e: e[0]):
        if shots and shots[-1].names == ["start"] and t < hold:
            shots[-1] = Shot(0.0, [name], box)       # a subject this early: open on it, no move
            continue
        if shots and shots[-1].names != ["start"] and t - shots[-1].t < hold + move:
            last = shots[-1]                         # too soon to move again: widen to hold both
            last.box = _union(last.box, box)
            last.names.append(name)
            continue
        shots.append(Shot(t, [name], box))
    for s in shots:
        s.cx, s.cy, s.scale, s.limited = _fit(s.box, src, view, pad, max_scale)
    # hold still through small changes: a new frame within 6% of the last is not a move
    kept: list[Shot] = []
    for s in shots:
        if kept:
            p = kept[-1]
            fw = view[0] / p.scale
            if (abs(math.log(s.scale / p.scale)) < 0.06 and abs(s.cx - p.cx) < 0.06 * fw
                    and abs(s.cy - p.cy) < 0.06 * fw):
                continue
        kept.append(s)
    return kept


def _ease(u):                                        # smootherstep: eases in and out, no overshoot
    u = min(max(u, 0.0), 1.0)
    return u * u * u * (u * (6 * u - 15) + 10)


def state(shots, t, move=0.9):
    """(cx, cy, scale) at recording time *t*."""
    cur = shots[0]
    cx, cy, s = cur.cx, cur.cy, cur.scale
    for nxt in shots[1:]:
        if t < nxt.t:
            break
        u = _ease((t - nxt.t) / move)
        s = math.exp(math.log(s) + (math.log(nxt.scale) - math.log(s)) * u)
        cx, cy = cx + (nxt.cx - cx) * u, cy + (nxt.cy - cy) * u
    return cx, cy, s


def screen(c: Comp, video, focus: dict, x, y, w, h, *, start, ip, op, radius=0, timemap=None, move=0.9,
           hold=2.0, pad=16, max_scale=2.0, name=None, **motion) -> list[Shot]:
    """Place the capture *video* in a w x h card at (x, y), framed by *focus* (from load()).

    *start* is the comp time of the clip's first frame, as in Comp.video. *timemap* maps recording
    seconds to clip seconds when the clip was re-timed (kit.waits.remap); without it they are the
    same. *motion* (fade, rise, pop, ...) moves the card itself."""
    src = focus["size"]
    tm = timemap or (lambda t: t)
    # the holds are what the viewer sees, so plan on the clip's clock, after the re-timing
    events = [(tm(t), n, b) for t, n, b in focus["events"]]
    timed = plan(events, src, (w, h), move=move, hold=hold, pad=pad, max_scale=max_scale)
    sub = c.precomp(x, y, w, h, radius=radius, ip=ip, op=op, name=name or f"screen {Path(video).stem}", **motion)
    layer = sub.video(video, 0, 0, src[0], src[1], start=start, ip=ip, op=op, pivot="origin")
    pos, scl = [], []
    n0, n1 = int(round(ip * c.fps)), int(round(op * c.fps))
    for n in range(n0, n1 + 1):
        T = n / c.fps
        cx, cy, s = state(timed, T - start, move)
        pos.append([n, [w / 2 - cx * s, h / 2 - cy * s, 0]])
        scl.append([n, [s * 100, s * 100, 100]])
    layer["ks"]["p"] = _keys(pos)
    layer["ks"]["s"] = _keys(scl)
    return timed


def _keys(frames):
    """Per-frame values as linear keyframes, dropping the ones a straight line already passes through."""
    out = []
    for k, (n, v) in enumerate(frames):
        if 0 < k < len(frames) - 1 and frames[k - 1][1] == v == frames[k + 1][1]:
            continue
        out.append({"t": n, "s": [round(a, 3) for a in v], **LINEAR})
    out[-1] = {"t": out[-1]["t"], "s": out[-1]["s"]}
    return {"a": 1, "k": out}
