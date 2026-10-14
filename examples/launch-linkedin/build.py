"""kestrel studio — LinkedIn launch film (4:5, 33 s). See STORYBOARD.md for the state list.

    node capture/shoot.mjs                       # site captures + brand/brand.json (site served on :8765)
    ../../.venv/bin/python art.py                # aurora, glass, mark; then art.hero_with_film()
    (cd hf/unfold && npx hyperframes render . -o ../unfold.mp4 --quality high)   # global 4–12 s
    ../../.venv/bin/python postroll.py && kestrel render brand/postroll.json -o brand/postroll-4x5.mp4 --fonts ../../fonts
    ../../.venv/bin/python build.py
    kestrel render scene.json -o out/raw.mp4 --fonts ../../fonts --audio media/music-11.flac
    ../../.venv/bin/python -m kit.finish out/raw.mp4 out/launch.mp4 --flash 12,16,25.5,30   (from the repo root)

Timing follows the track (music-11, ACE-Step, 120 BPM): quiet 0–14, a breath at 14–15, a riser into
the drop at 16.0, full energy to ~29.5, tail out by 31.5. Every landing below is on a beat.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE))
from art import ART, BRAND, FILM, FILM_STILL_T, aurora, glass, hero_with_film, mark_svg, measure, shadow  # noqa: E402
from kit.beats import SR, load  # noqa: E402
from kit.lottie import EASE_IN_OUT, LINEAR, Comp, static  # noqa: E402
from kit.shaders import GLINT, PAPER  # noqa: E402

W, H, FPS = 1080, 1350, 30
DUR = 33.0
P = BRAND["palette"]
INK, INK2, MUTED, RUF, AMB, SLATE, CREAM = P["ink"], P["ink2"], P["muted"], P["accent"], P["accent2"], P["counter"], P["cream"]
SANS, SANS_R, SERIF, MONO = "InterTight-SemiBold", "InterTight-Regular", "InstrumentSerif-Italic", "JetBrainsMono-Medium"
SITE = (40, 300, 1000, 625)                       # where the HyperFrames unfold lands; kestrel continues here
MUSIC = HERE / "media" / "music-11.flac"
URL = "github.com/israelbenatar/kestrel-studio"

c = Comp(W, H, fps=FPS, duration=DUR, name="kestrel-studio-launch")
c.image(aurora(), 0, 0, W, H, zoom=((0, DUR), (100, 106)), name="aurora")


def glass_box(x, y, w, h, r, name, **motion):
    path, pad = glass(w, h, r, name)
    return c.image(path, x - pad, y - pad, w + 2 * pad, h + 2 * pad, name=f"glass {name}", **motion)


def chip(num, label, t0, t1):
    """The beat's title: a glass pill at the top with a mono number and the claim."""
    size, nsize = 44, 30
    tw = measure(label, SANS, size) + measure(num, MONO, nsize) + 26
    w, h = round(tw + 84), 92
    x, y = (W - w) / 2, 150
    m = dict(ip=t0, op=t1, fade=(t0, t0 + 0.3), fade_out=(t1 - 0.25, t1))
    glass_box(x, y, w, h, h // 2, f"chip{num}", rise=14, **m)
    c.text(num, font=MONO, size=nsize, x=x + 42, y=y + 57, color=AMB, rise=14, **m)
    c.text(label, font=SANS, size=size, x=x + 42 + measure(num, MONO, nsize) + 26, y=y + 61, color=INK, rise=14, **m)


def out_at(layer, t, dur=0.2):
    """Quick exit for a layer that is already on screen."""
    o = layer["ks"]["o"]
    v = o["k"] if not o.get("a") else 100
    layer["ks"]["o"] = c.keys((t - dur, 100), (t, 0)) if not o.get("a") else {"a": 1, "k": o["k"] + c.keys((t - dur, 100), (t, 0))["k"]}
    layer["op"] = c.f(t)


# ---------------------------------------------------------------- 1–2 · 0.0–4.0  the pain → the promise
for i, (line, t) in enumerate([("A launch video", 0.5), ("used to take", 1.0)]):
    c.text(line, font=SANS, size=96, x=90, y=470 + i * 112, color=INK, ip=t, op=4.0, tracking=-25,
           fade=(t, t + 0.35), rise=30, fade_out=(3.7, 4.0))
week = c.text("a week.", font=SANS, size=96, x=90, y=694, color=INK, ip=1.5, op=4.0, tracking=-25,
              fade=(1.5, 1.85), rise=30, fade_out=(3.7, 4.0))
ww = measure("a week.", SANS, 96) * 0.975
strike = c.rect(90, 660, ww, 9, RUF, radius=4, ip=2.0, op=4.0, pivot="origin", fade_out=(3.7, 4.0), name="strike")
strike["ks"]["s"] = c.keys((2.0, [0, 100, 100]), (2.3, [100, 100, 100]))
week["ks"]["o"] = c.keys((1.5, 0), (1.85, 100), (2.3, 100), (2.5, 38), (3.7, 38), (4.0, 0))
c.text("a prompt.", font=SERIF, size=150, x=86, y=900, color=AMB, ip=2.5, op=4.0,
       fade=(2.5, 2.8), rise=36, spring=True, fade_out=(3.7, 4.0))

# ---------------------------------------------------------------- 3–4 · 4.0–12.0  HyperFrames: prompt, 3D unfold
c.video(HERE / "hf" / "unfold.mp4", 0, 0, W, H, start=4.0, ip=4.0, op=12.0, name="hf unfold")

# ---------------------------------------------------------------- 5 · 12.0–16.0  ① takes your look
sx, sy, sw, sh = SITE
rects = json.loads((HERE / "assets/captures/rects.json").read_text())
k = sw / rects["viewport"]["w"]
f = rects["film"]
fx, fy, fw, fh = sx + f["x"] * k, sy + f["y"] * k, f["w"] * k, f["h"] * k
spath, spad = shadow(sw, sh, 18, "site")
site_layers = [
    c.image(spath, sx - spad, sy - spad, sw + 2 * spad, sh + 2 * spad, ip=12.0, op=16.0, name="site shadow"),
    c.image(hero_with_film(), sx, sy, sw, sh, radius=18, ip=12.0, op=16.0, name="site"),
    # the real film, playing inside the site's stage (frame FILM_STILL_T lines up with the capture)
    c.video(FILM, fx, fy, fw, fh, start=12.0 - FILM_STILL_T, ip=12.0, op=16.0, name="site film"),
]
for L in site_layers:
    out_at(L, 16.0, 0.15)
chip("01", "Takes the look from your site", 12.0, 16.0)
sw_y, tile, gapx = 1000, 132, 26
names = [("background", "#0E0F13"), ("ink", INK), ("accent", RUF), ("accent 2", AMB), ("counter", SLATE)]
x0 = (W - (5 * tile + 4 * gapx)) / 2
for i, (nm, col) in enumerate(names):
    t = 12.5 + i * 0.25
    x = x0 + i * (tile + gapx)
    m = dict(ip=t, op=16.0, fade=(t, t + 0.2), pop=t)
    glass_box(x, sw_y, tile, tile, 24, "swatch", **m)
    c.rect(x + 16, sw_y + 16, tile - 32, tile - 32, col, radius=14, **m)
    c.text(col.upper(), font=MONO, size=19, x=x + tile / 2, y=sw_y + tile + 34, color=MUTED, align="center", **m)
c.text("Inter Tight", font=SANS, size=46, x=x0, y=1250, color=INK, ip=14.0, op=16.0, fade=(14.0, 14.3), rise=14)
c.text("Instrument Serif", font=SERIF, size=54, x=x0 + measure("Inter Tight", SANS, 46) + 26, y=1250, color=AMB,
       ip=14.0, op=16.0, fade=(14.25, 14.55), rise=14)
c.text("→ brand.json", font=MONO, size=28, x=W - x0, y=1306, color=INK2, align="right", ip=15.0, op=16.0,
       fade=(15.0, 15.3), rise=10)

# ---------------------------------------------------------------- 6 · 16.0–19.0  ② the real product (the drop)
chip("02", "Shows your real product", 16.0, 19.0)
cw_, ch_ = 760, 950
cx_, cy_ = (W - cw_) / 2, 285
fpath, fpad = shadow(cw_, ch_, 28, "film")
c.image(fpath, cx_ - fpad, cy_ - fpad, cw_ + 2 * fpad, ch_ + 2 * fpad, ip=16.0, op=19.0, fade=(16.0, 16.15),
        fade_out=(18.8, 19.0), name="film shadow")
FILM_FROM = 14.3                                  # "Oldest to newest" builds photo by photo from the drop
c.video(FILM, cx_, cy_, cw_, ch_, start=16.0 - FILM_FROM, radius=28, ip=16.0, op=19.0, fade=(16.0, 16.15),
        pop=16.0, fade_out=(18.8, 19.0), name="real product")

# ---------------------------------------------------------------- 7 · 19.0–22.0  ③ music on the beat
chip("03", "Scores it to music, on the beat", 19.0, 22.0)
CW, CH = 640, 400
X, Y = (W - CW) / 2, 340
card = c.rect(X, Y, CW, CH, "#C9A45C", radius=30, ip=19.0, op=22.0, fade=(19.0, 19.3), rise=70, spring=True,
              fade_out=(21.8, 22.0), name="card")
c.shader(card, PAPER, {"uScale": 2.0, "uAmount": 0.12, "uSeed": 3.0}, name="paper")
c.shader(card, GLINT, {"uSize": [CW, CH], "uWidth": 0.06, "uGain": 0.55,
                       "uPos": c.keys((20.5, -0.3), (21.5, 1.3), ease=EASE_IN_OUT)}, name="glint")   # centre on 21.0
cm = dict(ip=19.0, op=22.0, fade=(19.3, 19.6), fade_out=(21.8, 22.0))
c.text("♩ 120 BPM", font=MONO, size=28, x=X + 44, y=Y + 74, color="#3A2E1A", **cm)
c.text("On the beat.", font=SERIF, size=78, x=X + 44, y=Y + CH - 56, color="#2A2112", **cm)
# the real waveform of this film's own track, 19–22 s, with the beats lit as the playhead passes
x = load(str(MUSIC))
bars, wx0, wx1, wy = 48, 110, 970, 1040
seg = x[int(19.0 * SR):int(22.0 * SR)]
rms = np.array([np.sqrt(np.mean(b ** 2)) for b in np.array_split(seg, bars)])
rms = rms / rms.max()
bw = (wx1 - wx0) / bars
for i, v in enumerate(rms):
    t_bar = 19.0 + 3.0 * i / bars
    on_beat = abs((t_bar * 2) - round(t_bar * 2)) < 0.5 * 3.0 / bars * 2
    hgt = float(30 + 150 * v)
    col = AMB if on_beat else "#6F675E"
    bar = c.rect(wx0 + i * bw + 2, wy - hgt / 2, bw - 4, hgt, col, radius=3, ip=19.2, op=22.0,
                 fade=(19.2 + i * 0.01, 19.4 + i * 0.01), fade_out=(21.8, 22.0), name="wave")
head = c.rect(wx0, wy - 110, 4, 220, CREAM, radius=2, ip=19.0, op=22.0, pivot="origin", fade_out=(21.8, 22.0), name="playhead")
head["ks"]["p"] = c.keys((19.0, [wx0, wy - 110, 0]), (22.0, [wx1, wy - 110, 0]), ease=LINEAR)
c.text("cuts on the beat · sync ±0.9 frames", font=MONO, size=30, x=W / 2, y=1222, color=INK2, align="center", **cm)

# ---------------------------------------------------------------- 8 · 22.0–25.5  ④ speed + every aspect
chip("04", "Renders at 120 fps, every aspect", 22.0, 25.5)
counter = c.text("240", font=SANS, size=250, x=W / 2, y=590, color=INK, align="center", ip=22.0, op=25.5, tracking=-40,
                 fade=(22.0, 22.2), fade_out=(25.3, 25.5))
counter["t"]["d"]["x"] = "var $bm_rt;\n$bm_rt = '' + Math.round(linear(time, 22.1, 24.0, 0, 240));"
c.text("frames in 2.0 seconds", font=SERIF, size=74, x=W / 2, y=690, color=AMB, align="center", ip=22.0, op=25.5,
       fade=(22.2, 22.5), rise=12, fade_out=(25.3, 25.5))
# four aspects of the same scene, each a crop of the film still, landing on the 24.0–24.75 hits
still = ART / "film-still.png"
from PIL import Image  # noqa: E402
src = Image.open(still).convert("RGB")
asp = [("9:16", 9 / 16), ("4:5", 4 / 5), ("1:1", 1.0), ("16:9", 16 / 9)]
hmax, gap = 250, 24
sizes = [(round(hmax * a) if a <= 1 else 300, hmax if a <= 1 else round(300 / a)) for _, a in asp]
sizes = [(w, h) for (w, h) in sizes]
tot = sum(w for w, _ in sizes) + gap * 3
ax0, base = (W - tot) / 2, 1110
for i, ((lab, a), (w, h)) in enumerate(zip(asp, sizes)):
    t = 24.0 + i * 0.25
    sw_, sh_ = src.size
    cw2, ch2 = (sw_, round(sw_ / a)) if sw_ / sh_ < a else (round(sh_ * a), sh_)
    cw2, ch2 = min(cw2, sw_), min(ch2, sh_)
    if sw_ / sh_ > a:
        cw2, ch2 = round(sh_ * a), sh_
    else:
        cw2, ch2 = sw_, round(sw_ / a)
    l, tp = (sw_ - cw2) // 2, (sh_ - ch2) // 2
    p = ART / f"aspect-{lab.replace(':', 'x')}.png"
    src.crop((l, tp, l + cw2, tp + ch2)).resize((w * 2, h * 2), Image.LANCZOS).save(p)
    x = ax0 + sum(s[0] for s in sizes[:i]) + gap * i
    m = dict(ip=t, op=25.5, fade=(t, t + 0.15), pop=t, fade_out=(25.3, 25.5))
    c.image(p, x, base - h, w, h, radius=14, **m)
    c.text(lab, font=MONO, size=28, x=x + w / 2, y=base + 48, color=INK2, align="center", **m)

# ---------------------------------------------------------------- 9 · 25.5–30.0  finale
FT = 25.5
# earlier beats gather in from the edges: the site, the real product, the scored card, the swatches
gather = [
    (hero_with_film(), 60, 120, 400, 250, (-520, -60), -5, 14),
    (still, 780, 96, 230, 288, (420, -120), 6, 16),
]
for path, gx, gy, gw, gh, (dx, dy), rot, rad in gather:
    L = c.image(path, gx, gy, gw, gh, radius=rad, ip=FT, op=30.3, fade=(FT, FT + 0.2), slide=(dx, dy), spring=True)
    L["ks"]["r"] = static(rot)
for i, col in enumerate([RUF, AMB, SLATE, INK]):
    t = FT + 0.1 + i * 0.06
    c.rect(70 + i * 62, 1210, 46, 46, col, radius=12, ip=t, op=30.3, fade=(t, t + 0.2), slide=(-300, 80), spring=True)
for i, (lab, w, h) in enumerate([("9:16", 36, 64), ("4:5", 52, 64), ("1:1", 60, 60), ("16:9", 86, 48)]):
    t = FT + 0.1 + i * 0.06
    c.rect(790 + sum([36, 52, 60, 86][:i]) + 14 * i, 1274 - h, w, h, "#3A3530", radius=8, ip=t, op=30.3,
           fade=(t, t + 0.2), slide=(300, 80), spring=True)
c.text("Marketing & social videos,", font=SANS, size=76, x=W / 2, y=640, color=INK, align="center", tracking=-20,
       ip=FT, op=30.3, fade=(FT, FT + 0.35), rise=26, spring=True)
c.text("written as code.", font=SERIF, size=128, x=W / 2, y=780, color=AMB, align="center",
       ip=26.0, op=30.3, fade=(26.0, 26.35), rise=26, spring=True)
c.text("An agent skill + a 120 fps renderer.", font=SANS_R, size=44, x=W / 2, y=880, color=INK2, align="center",
       ip=26.5, op=30.3, fade=(26.5, 26.8), rise=12)
c.text("Free for builders & teams up to 10", font=SANS, size=48, x=W / 2, y=1020, color=INK, align="center",
       ip=27.0, op=30.3, fade=(27.0, 27.3), rise=12)
c.text(URL, font=MONO, size=31, x=W / 2, y=1085, color=RUF, align="center", ip=27.5, op=30.3, fade=(27.5, 27.8), rise=10)

# ---------------------------------------------------------------- 10 · 30.0–33.0  postroll v1 (unchanged)
c.video(HERE / "brand" / "postroll-4x5.mp4", 0, 0, W, H, start=30.0, ip=30.0, op=DUR, fade=(30.0, 30.3), name="postroll v1")

c.save(HERE / "scene.json")
print("scene.json", f"{DUR}s", len(c.layers), "layers")
