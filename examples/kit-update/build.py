"""kestrel studio — kit update film (4:5, 24.5 s): the camera, fast waits and measured checks, shown on
real footage. See STORYBOARD.md for the state list.

    ../../.venv/bin/python build.py              # media/ (the re-timed capture) + scene.json
    kestrel render scene.json -o out/raw.mp4 --fonts ../../fonts --audio ../launch-linkedin/media/music-11.flac --fade-out 2
    ../../.venv/bin/python -m kit.finish examples/kit-update/out/raw.mp4 examples/kit-update/out/kit-update.mp4 --flash 2.48,15.98,21.48   (from the repo root)
    ../../.venv/bin/python -m kit.check examples/kit-update/scene.json --video examples/kit-update/out/kit-update.mp4

Inputs not in git: the Sustain capture `chat-sorting/sources/recordings/date.webm` (a Playwright
recording of the real editor) and the chat-sorting render it checks. The focus log
(capture/date.focus.json) is written by hand for this old capture; a new one writes its own with
kit/capture.cjs.
"""
import sys
from functools import partial
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
LAUNCH = HERE.parent / "launch-linkedin"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(LAUNCH))
from art import BRAND, aurora, glass, measure, shadow  # noqa: E402
from kit import check, waits  # noqa: E402
from kit.camera import load, screen  # noqa: E402
from kit.lottie import Comp  # noqa: E402

W, H, FPS = 1080, 1350, 30
DUR = 24.48
P = BRAND["palette"]
INK, INK2, RUF, AMB, SLATE = P["ink"], P["ink2"], P["accent"], P["accent2"], P["counter"]
SANS, SANS_R, SERIF, MONO = "InterTight-SemiBold", "InterTight-Regular", "InstrumentSerif-Italic", "JetBrainsMono-Medium"
REC = HERE.parent / "chat-sorting" / "sources" / "recordings" / "date.webm"
MEDIA = HERE / "media"
MEDIA.mkdir(exist_ok=True)

T_SEQ, T_CHECK, T_POST = 2.48, 15.98, 21.48     # cuts, on beats
CARD = (40, 330, 1000, 625)                      # the capture card: 1440 x 900 at 16:10


def beat(t):
    return round(0.48 + round((t - 0.48) / 0.5) * 0.5, 2)


# ---------------------------------------------------------------- the capture, re-timed by kit.waits
WAITS = [(13.6, 33.6), (37.1, 115.2)]            # sent -> reply; confirmed -> album reloads
start_len = waits.length(waits.plan(str(REC), WAITS, keep=(10.0, 115.2)))
PIECES = waits.plan(str(REC), WAITS, keep=(10.0, 115.2 + (T_CHECK - T_SEQ + 0.2 - start_len)))
CLIP = MEDIA / "capture.mp4"
if not CLIP.exists():
    waits.render(str(REC), PIECES, str(CLIP), fps=FPS)
fast = [p for p in PIECES if p[2] > 1]
FAST_IN = T_SEQ + waits.remap(PIECES, fast[0][0])
FAST_OUT = T_SEQ + waits.remap(PIECES, fast[-1][1])
WAITED = WAITS[1][1] - WAITS[1][0]              # the whole rebuild wait, still parts (cut) included
SPEED = fast[0][2]
for p in PIECES:
    print(f"piece {p[0]:7.2f}-{p[1]:7.2f} x{p[2]}")
print(f"fast: comp {FAST_IN:.2f}-{FAST_OUT:.2f}: a {WAITED:.0f} s wait in {FAST_OUT - FAST_IN:.1f} s, moving parts at x{SPEED}")

c = Comp(W, H, fps=FPS, duration=DUR, name="kestrel-studio-kit-update")
c.image(aurora(), 0, 0, W, H, zoom=((0, DUR), (100, 106)), name="aurora")


def glass_box(x, y, w, h, r, name, **motion):
    path, pad = glass(w, h, r, name)
    return c.image(path, x - pad, y - pad, w + 2 * pad, h + 2 * pad, name=f"glass {name}", **motion)


def chip(num, label, t0, t1):
    """The beat's title: a glass pill at the top with a mono number and the claim."""
    size, nsize = 44, 40
    tw = measure(label, SANS, size) + measure(num, MONO, nsize) + 26
    w, h = round(tw + 84), 96
    x, y = (W - w) / 2, 150
    m = dict(ip=t0, op=t1, fade=(t0, t0 + 0.3), fade_out=(t1 - 0.25, t1))
    glass_box(x, y, w, h, h // 2, f"chip{num}{t0}", rise=14, **m)
    c.text(num, font=MONO, size=nsize, x=x + 42, y=y + 62, color=AMB, rise=14, **m)
    c.text(label, font=SANS, size=size, x=x + 42 + measure(num, MONO, nsize) + 26, y=y + 63, color=INK, rise=14, **m)


def caption(text, t0, t1, y=1060):
    c.text(text, font=SANS_R, size=40, x=W / 2, y=y, align="center", color=INK2, ip=t0, op=t1,
           fade=(t0, t0 + 0.3), rise=12, fade_out=(t1 - 0.25, t1))


# ---------------------------------------------------------------- 0.0–2.48  title
c.text("The capture", font=SANS, size=96, x=90, y=560, color=INK, ip=0.48, op=T_SEQ, tracking=-25,
       fade=(0.48, 0.8), rise=30, fade_out=(2.2, T_SEQ))
c.text("now edits itself.", font=SERIF, size=150, x=86, y=730, color=AMB, ip=0.98, op=T_SEQ,
       fade=(0.98, 1.3), rise=36, spring=True, fade_out=(2.2, T_SEQ))
c.text("kestrel studio · kit update", font=MONO, size=40, x=90, y=420, color=INK2, ip=0.48, op=T_SEQ,
       fade=(0.48, 0.8), fade_out=(2.2, T_SEQ))

# ---------------------------------------------------------------- 2.48–15.98  camera + waits on the real capture
x, y, w, h = CARD
spath, spad = shadow(w, h, 28, "card")
card_in = dict(fade=(T_SEQ, T_SEQ + 0.35), rise=40)
c.image(spath, x - spad, y - spad + 40, w + 2 * spad, h + 2 * spad, ip=T_SEQ, op=T_CHECK, name="card shadow",
        fade_out=(T_CHECK - 0.25, T_CHECK), **card_in)
shots = screen(c, CLIP, load(HERE / "capture" / "date.focus.json"), x, y, w, h, start=T_SEQ, ip=T_SEQ, op=T_CHECK,
               radius=28, timemap=partial(waits.remap, PIECES), max_scale=1.6, name="capture",
               fade_out=(T_CHECK - 0.25, T_CHECK), **card_in)
for s in shots:
    print("shot", s)

t_fast0, t_fast1 = beat(FAST_IN), beat(FAST_OUT)
chip("01", "The camera follows the subject", T_SEQ + 0.5, t_fast0)
caption("kit/camera.py · framed from the capture's focus log", T_SEQ + 0.5, t_fast0)
chip("02", "Waits play fast", t_fast0, t_fast1)
caption(f"kit/waits.py · a {WAITED:.0f} s wait in {FAST_OUT - FAST_IN:.1f} s", t_fast0, t_fast1)
bw = round(measure(f"×{SPEED:.0f}", MONO, 72) + 64)
c.rect(x + w - bw - 24, y + 24, bw, 104, P["background"], radius=52, opacity=88, name="speed pill", ip=t_fast0,
       op=t_fast1, pop=t_fast0, fade=(t_fast0, t_fast0 + 0.15), fade_out=(t_fast1 - 0.2, t_fast1))
c.text(f"×{SPEED:.0f}", font=MONO, size=72, x=x + w - 24 - bw / 2, y=y + 24 + 78, align="center", color=AMB,
       ip=t_fast0, op=t_fast1, fade=(t_fast0, t_fast0 + 0.15), fade_out=(t_fast1 - 0.2, t_fast1))
chip("01", "…and pulls back for the result", t_fast1, T_CHECK)
caption("a zoom out is as smooth as a zoom in", t_fast1, T_CHECK)

# ---------------------------------------------------------------- 15.98–21.48  measured checks on a real frame
SRC_SCENE = HERE.parent / "chat-sorting" / "scene.json"
SRC_VIDEO = HERE.parent / "chat-sorting" / "out" / "finished.mp4"
LABEL = "1 · By date"
found = check.run(SRC_SCENE, SRC_VIDEO)
mine = [f for f in found if f"'{LABEL}'" in f]
contrast = next(f for f in mine if f.startswith("contrast")).split(": ")[1].split(" at")[0]   # e.g. 2.7:1
height = next(f for f in mine if f.startswith("text-height")).split(": ")[1].split(",")[0]    # e.g. 26 px
print("checked:", contrast, height)

frame = MEDIA / "check-frame.png"
crop = MEDIA / "check-crop.png"
CROP_H = 620
k = 1000 / 1080
Image.open(frame).convert("RGB").crop((0, 0, 1080, CROP_H)).resize((1000, round(CROP_H * k)), Image.LANCZOS).save(crop)
fy, fh = 330, round(CROP_H * k)
m = dict(op=T_POST, fade_out=(T_POST - 0.3, T_POST))
spath2, spad2 = shadow(1000, fh, 28, "frame")
c.image(spath2, 40 - spad2, fy - spad2 + 40, 1000 + 2 * spad2, fh + 2 * spad2, name="frame shadow",
        ip=T_CHECK, fade=(T_CHECK, T_CHECK + 0.35), rise=40, **m)
c.image(crop, 40, fy, 1000, fh, radius=28, name="checked frame", ip=T_CHECK, fade=(T_CHECK, T_CHECK + 0.35), rise=40, **m)
chip("03", "Checks it can measure", T_CHECK, T_POST)

# the label's box, from the same estimate kit.check used
import json  # noqa: E402
box = next((b for b in check.texts(json.loads(SRC_SCENE.read_text()), ROOT / "fonts") if b[0]["nm"] == LABEL))
bx0, by0, bx1, by1 = (40 + box[1] * k - 14, fy + box[2] * k - 12, 40 + box[3] * k + 14, fy + box[4] * k + 12)
t_box = 17.48
for nm, (rx, ry, rw, rh) in {"top": (bx0, by0, bx1 - bx0, 5), "bottom": (bx0, by1 - 5, bx1 - bx0, 5),
                             "left": (bx0, by0, 5, by1 - by0), "right": (bx1 - 5, by0, 5, by1 - by0)}.items():
    c.rect(rx, ry, rw, rh, RUF, radius=2, name=f"mark {nm}", ip=t_box, fade=(t_box, t_box + 0.2), **m)
tag = f"{contrast} contrast · needs 3:1"
tw = measure(tag, SANS, 40) + 48
c.rect(bx0, by1 + 14, tw, 64, RUF, radius=32, name="tag", ip=t_box + 0.5, fade=(t_box + 0.5, t_box + 0.7),
       slide=(-20, 0), **m)
c.text(tag, font=SANS, size=40, x=bx0 + 24, y=by1 + 60, color=P["background"], ip=t_box + 0.5,
       fade=(t_box + 0.5, t_box + 0.7), slide=(-20, 0), **m)

# the real output, line by line
ty = fy + fh + 50
glass_box(40, ty, 1000, 300, 28, "terminal", ip=17.98, fade=(17.98, 18.3), rise=20, **m)
c.text("$ python -m kit.check", font=MONO, size=40, x=88, y=ty + 70, color=INK2, ip=17.98,
       typewriter=(18.1, 18.9), **m)
for i, (mark, text, colour) in enumerate([("✗", f"contrast     {contrast}", RUF),
                                          ("✗", f"text-height  {height}", RUF),
                                          ("✓", "safe-area", SLATE)]):
    t = 18.98 + i * 0.5
    c.text(mark, font=SANS, size=44, x=88, y=ty + 140 + i * 62, color=colour, ip=t, fade=(t, t + 0.15), **m)
    c.text(text, font=MONO, size=40, x=140, y=ty + 140 + i * 62, color=INK, ip=t, fade=(t, t + 0.15), **m)

# ---------------------------------------------------------------- 21.48–24.48  postroll v1, unchanged
c.video(LAUNCH / "brand" / "postroll-4x5.mp4", 0, 0, W, H, start=T_POST, ip=T_POST, op=DUR,
        fade=(T_POST, T_POST + 0.3), name="postroll v1")

c.save(HERE / "scene.json")
print("wrote scene.json")
