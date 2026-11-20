"""kestrel studio — poster titles (4:5, 13.6 s): four title scenes in the editorial poster style, each
with its own look, joined by cuts made of square blocks. No media, no voice: text and shapes only.

    python build.py
    kestrel render scene.json -o out/poster-titles.mp4 --fonts ../../fonts

1. Red rows of repeated text on a diagonal, with faded copies behind (kit.poster.echo_rows).
2. Black poster words in stepped sizes on yellow.
3. A calendar: a pen circle draws itself round the date, then "SHIP." lands (kit.poster.draw_ellipse).
4. A heavy italic word ("AWAY.", Barlow Black Italic) flies in out of a blur on red.
Spaced letters run down the margins (margin_text); a small italic note sits in a corner.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from kit.lottie import Comp  # noqa: E402
from kit.poster import draw_ellipse, echo_rows, fit_size, margin_text, pixel_cut  # noqa: E402

W, H, FPS, DUR = 1080, 1350, 30, 13.6
PAPER, INK, RED, YELLOW, MUSTARD = "#F3EEE4", "#16181F", "#C8321F", "#F5D341", "#9A6A08"
CUT1, CUT2, CUT3 = 3.3, 6.6, 10.0

c = Comp(W, H, fps=FPS, duration=DUR, name="kestrel-studio-poster-titles")

# ---------- 1. rows on a diagonal ----------
c.solid(PAPER, op=CUT1)
echo_rows(c, "WRITE IT · RENDER IT · ", rows=7, angle=-12, size=150, color=RED, t0=0.1, t1=CUT1, speed=110)
for x in (0, W - 104):                                    # clear margins, so the spaced letters read
    c.rect(x, 0, 104, H, PAPER, op=CUT1, name="margin")
margin_text(c, "KESTREL STUDIO", side="left", color=INK, op=CUT1)
margin_text(c, "KIT.POSTER", side="right", color=INK, op=CUT1)

# ---------- 2. stepped sizes on yellow ----------
c.solid(YELLOW, ip=CUT1, op=CUT2)
x0, y = 90, 330
for n, (word, most) in enumerate([("EVERY", 170), ("FRAME", 260), ("IS CODE.", 400)]):
    size = fit_size(word, "Anton-Regular", width=W - 2 * x0, most=most)
    y += size * 0.92
    t = CUT1 + 0.25 + n * 0.32
    c.text(word, font="Anton-Regular", size=size, x=x0, y=y, color=INK, ip=t, op=CUT2, pop=t, fade=(t, t + 0.12))
c.text("Text, shapes and clips, written as a scene.", font="InstrumentSerif-Italic", size=46, x=x0, y=1180,
       color=INK, ip=CUT1, op=CUT2, fade=(CUT1 + 1.4, CUT1 + 1.9))
margin_text(c, "EVERY FRAME", side="right", color=INK, ip=CUT1, op=CUT2, fade=(CUT1 + 0.2, CUT1 + 0.7))

# ---------- 3. calendar ----------
c.solid(PAPER, ip=CUT2, op=CUT3)
gx, gy, cw, ch = 110, 430, 125, 118                      # the grid: 7 columns from (gx, gy)
c.text("NOVEMBER", font="Anton-Regular", size=120, x=gx - 6, y=330, color=INK, ip=CUT2,
       fade=(CUT2 + 0.05, CUT2 + 0.3), rise=24)
for d, name in enumerate("SMTWTFS"):
    c.text(name, font="Inter-Bold", size=40, x=gx + d * cw + cw / 2, y=gy, color=RED, align="center", ip=CUT2,
           fade=(CUT2 + 0.15, CUT2 + 0.4))
for day in range(1, 31):                                  # 1 November 2026 is a Sunday
    col, row = (day - 1) % 7, (day - 1) // 7
    t = CUT2 + 0.2 + day * 0.012
    c.text(str(day), font="InterTight-SemiBold", size=56, x=gx + col * cw + cw / 2, y=gy + 110 + row * ch,
           color=INK, align="center", ip=CUT2, fade=(t, t + 0.25))
cx, cy = gx + 5 * cw + cw / 2, gy + 110 + 2 * ch - 20     # Friday the 20th
draw_ellipse(c, cx, cy, 70, 54, t0=CUT2 + 1.0, dur=0.55, color=RED, stroke=8)
c.text("SHIP.", font="Anton-Regular", size=230, x=560, y=1210, color=MUSTARD, ip=CUT2 + 1.7, op=CUT3,
       pop=CUT2 + 1.7, fade=(CUT2 + 1.7, CUT2 + 1.82))
c.layers[-1]["ks"]["r"] = {"a": 0, "k": -6}
c.text("the cut is due friday.", font="InstrumentSerif-Italic", size=46, x=gx, y=1170, color=INK, ip=CUT2,
       op=CUT3, fade=(CUT2 + 2.0, CUT2 + 2.5))
margin_text(c, "KESTREL STUDIO", side="left", color=INK, ip=CUT2, op=CUT3, fade=(CUT2 + 0.2, CUT2 + 0.7))

# ---------- 4. the heavy italic ----------
c.solid(RED, ip=CUT3)
x0 = 90
for n, word in enumerate(["PUT THE", "TIMELINE"]):
    t = CUT3 + 0.2 + n * 0.25
    c.text(word, font="Anton-Regular", size=150, x=x0, y=520 + n * 150, color=INK, ip=CUT3, fade=(t, t + 0.2),
           rise=30)
size = fit_size("AWAY.", "Barlow-BlackItalic", width=W - 2 * x0, most=380)
t = CUT3 + 0.95                                           # it flies in from the right, out of a blur
away = c.text("AWAY.", font="Barlow-BlackItalic", size=size, x=x0, y=950, color=PAPER, ip=t,
              fade=(t, t + 0.08), slide=(900, 0), spring=True)
c.blur(away, c.keys((t, 40), (t + 0.3, 0)))
c.text("Leave the frames to the code.", font="InstrumentSerif-Italic", size=46, x=x0, y=1180, color=PAPER,
       ip=CUT3, fade=(CUT3 + 2.0, CUT3 + 2.5))
margin_text(c, "KIT.POSTER", side="right", color=INK, ip=CUT3, fade=(CUT3 + 0.2, CUT3 + 0.7))

# ---------- the cuts (on top of everything) ----------
pixel_cut(c, CUT1, colors=[YELLOW, YELLOW, INK, RED], seed=4)
pixel_cut(c, CUT2, colors=[PAPER, PAPER, INK], seed=9)
pixel_cut(c, CUT3, colors=[RED, RED, INK, PAPER], seed=12)

c.save(HERE / "scene.json")
print("scene.json", DUR, "s")
