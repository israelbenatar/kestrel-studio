"""Poster titles: scene looks from editorial motion posters.

    from kit.poster import echo_rows, draw_ellipse, margin_text, pixel_cut, fit_size
    echo_rows(c, "WRITE IT · RENDER IT · ", rows=6, angle=-12, size=150, color="#D23A2C", t0=0.2, t1=3.2)
    draw_ellipse(c, 640, 820, 190, 150, t0=7.4, color="#D23A2C")     # a pen circle round a word
    margin_text(c, "KESTREL STUDIO", side="left", color="#16181F")     # spaced letters down a margin
    pixel_cut(c, 3.2, colors=["#F5D341", "#16181F"])                  # a cut made of square blocks

- echo_rows: rows of repeated text on a diagonal, each row sliding the other way from the last,
  with faded copies stepped behind it.
- draw_ellipse: a stroke that draws itself round a word, like a pen: not a perfect circle, and the
  end runs past the start.
- margin_text: one line of widely spaced letters, turned 90°, down the left or right edge.
  It is decoration (decor=True): kit.check does not hold it to the size and contrast rules.
- pixel_cut: square blocks flash on in random order before *t* and off after it. Change the
  scene under it at *t*.
kit.check cannot measure rotated text: review echo rows and margin text on stills.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

from .check import _width
from .lottie import EASE_IN_OUT, LINEAR, Comp, rgb, static

FONTS = Path(__file__).resolve().parent.parent / "fonts"

def fit_size(text, font, *, width, most, tracking=0, fonts=FONTS) -> float:
    """The largest size up to *most* at which *text* is at most *width* px wide."""
    return min(most, most * width / _width(text, font, most, tracking, fonts))

# ---------- rows of repeated text on a diagonal ----------
def echo_rows(c: Comp, text, *, rows=6, angle=-12, size=150, font="Anton-Regular", color="#D23A2C",
              t0=0.0, t1=None, speed=90, gap=1.05, echoes=2, echo_step=0.16, echo_opacity=(28, 12),
              stagger=0.08, tracking=0, cx=None, cy=None, fonts=FONTS):
    """*rows* rows of *text* repeated, turned by *angle* degrees and centred on (cx, cy) (the frame
    centre by default). Row n slides at *speed* px/s, every second row the other way. Each row has
    *echoes* faded copies stepped up behind it by *echo_step* × size, at *echo_opacity*.
    Rows come in one after the other (*stagger* s) from t0; the group ends at t1."""
    t1 = c.duration if t1 is None else t1
    cx, cy = (c.w / 2 if cx is None else cx), (c.h / 2 if cy is None else cy)
    side = math.ceil(math.hypot(c.w, c.h)) + 40          # covers the frame at any angle
    g = c.precomp(cx - side / 2, cy - side / 2, side, side, ip=t0, op=t1, name="echo rows")
    c.layers[-1]["ks"]["r"] = static(angle)
    period = _width(text, font, size, tracking, fonts)
    travel = speed * (t1 - t0)
    reps = math.ceil((side + travel + period) / period) + 1
    line = text * reps
    step = size * gap
    top = side / 2 - step * (rows - 1) / 2 + size * 0.36  # baseline of row 0: the block sits centred
    for n in range(rows):
        sign = 1 if n % 2 == 0 else -1
        x0 = -(n * period * 0.37) % period - period      # each row starts at another place in the text
        xa, xb = (x0, x0 - travel) if sign > 0 else (x0 - travel, x0)
        y = top + n * step
        ti = t0 + n * stagger
        copies = [(echoes - e, echo_opacity[min(e, len(echo_opacity)) - 1]) for e in range(echoes, 0, -1)] + [(0, 100)]
        for lift, op in copies:
            yy = y - lift * size * echo_step
            lay = g.text(line, font=font, size=size, x=0, y=yy, color=color, tracking=tracking, ip=ti,
                         name=f"row {n}" + (f" echo {lift}" if lift else ""), decor=True)
            lay["ks"]["p"] = g.keys((t0, [xa, yy, 0]), (t1, [xb, yy, 0]), ease=LINEAR)
            lay["ks"]["o"] = g.keys((ti, 0), (ti + 0.25, op))
    return g

# ---------- a pen circle that draws itself ----------
def draw_ellipse(c: Comp, cx, cy, rx, ry, *, t0, dur=0.55, color="#D23A2C", stroke=9, overshoot=0.14,
                 tilt=-8, wobble=0.04, seed=3, op=None, name="pen circle"):
    """A hand-drawn ellipse of radii (rx, ry) round (cx, cy), drawn on from t0 over *dur* s.
    The line goes round 1 + *overshoot* times, a little wider on the second pass, and the radius
    wobbles by *wobble*: a pen, not a tool."""
    rnd = random.Random(seed)
    n = 40
    turns = 1 + overshoot
    phase = [rnd.uniform(0, 2 * math.pi) for _ in range(2)]
    pts = []
    for k in range(int(n * turns) + 1):
        a = -math.pi * 0.6 + 2 * math.pi * k / n
        grow = 1 + 0.05 * k / (n * turns)               # the second pass runs a little wide
        w = 1 + wobble * (math.sin(2 * a + phase[0]) + 0.5 * math.sin(3 * a + phase[1]))
        pts.append((math.cos(a) * rx * w * grow, math.sin(a) * ry * w * grow))
    # smooth curve through the points (Catmull-Rom as Bézier tangents, relative to each point)
    tin, tout = [], []
    for k, p in enumerate(pts):
        a, b = pts[max(0, k - 1)], pts[min(len(pts) - 1, k + 1)]
        d = ((b[0] - a[0]) / 6, (b[1] - a[1]) / 6)
        tin.append([-d[0], -d[1]])
        tout.append([d[0], d[1]])
    path = {"c": False, "v": [list(p) for p in pts], "i": tin, "o": tout}
    ks = c._transform(cx, cy, rot=static(tilt))
    shape = {"ty": "gr", "nm": name, "it": [
        {"ty": "sh", "nm": "Path", "ks": static(path)},
        {"ty": "tm", "nm": "Draw", "s": static(0), "e": c.keys((t0, 0), (t0 + dur, 100), ease=EASE_IN_OUT),
         "o": static(0), "m": 1},
        {"ty": "st", "nm": "Pen", "c": static(rgb(color) + [1]), "o": static(100), "w": static(stroke),
         "lc": 2, "lj": 2},
        {"ty": "tr", "p": static([0, 0]), "a": static([0, 0]), "s": static([100, 100]), "r": static(0),
         "o": static(100), "sk": static(0), "sa": static(0)}]}
    return c._layer(4, name, t0, op, ks, shapes=[shape])

# ---------- spaced letters down a margin ----------
def margin_text(c: Comp, text, *, side="left", inset=58, size=30, font="Inter-Bold", color="#16181F",
                tracking=600, ip=0, op=None, fade=(0.3, 0.9)):
    """*text* in widely spaced letters, turned to run down the left (bottom to top) or right (top to
    bottom) edge, centred on the frame's height. Decoration: kit.check skips it."""
    x = inset if side == "left" else c.w - inset
    lay = c.text(text, font=font, size=size, x=x, y=c.h / 2, color=color, align="center", tracking=tracking,
                 ip=ip, op=op, fade=fade, decor=True, name=f"margin {side}")
    lay["ks"]["r"] = static(-90 if side == "left" else 90)
    return lay

# ---------- a cut made of square blocks ----------
def pixel_cut(c: Comp, t, *, colors=("#16181F",), cell=90, dur=0.36, seed=7, fill=0.9):
    """Square blocks of *cell* px in *colors* switch on in random order over the *dur* s before *t*
    and off over the *dur* s after it; at *t* about *fill* of the frame is covered. Change the scene
    under it at *t*. Each block is a hard on/off (no fade), at whole frames."""
    rnd = random.Random(seed)
    cols, rows = math.ceil(c.w / cell), math.ceil(c.h / cell)
    frame = 1 / c.fps
    for r in range(rows):
        for q in range(cols):
            if rnd.random() > fill:
                continue
            on = t - rnd.uniform(frame, dur)
            off = t + rnd.uniform(frame, dur)
            lay = c.rect(q * cell, r * cell, cell, cell, rnd.choice(colors), ip=on, op=off, name="cut block")
            # snap to whole frames, so a block is never half there
            lay["ip"], lay["op"] = math.floor(lay["ip"]), math.ceil(lay["op"])
