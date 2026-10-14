"""Layer shaders in kestrel: a membership card on paper stock, catching the light twice.

    # music: generated at a BPM we chose, so the beat grid is known before the track exists
    ../../.venv/bin/python ../../kit/music.py "minimal warm electronic, soft kick on every beat, felt piano chords, gentle shimmer, clean and premium, steady groove" \
        --bpm 120 --key "D Major" --duration 10 --seeds 7 -o media        # add --replicate to run on Replicate
    ../../.venv/bin/python build.py
    kestrel render scene.json -o out/glint.mp4 --fonts ../../fonts --audio media/music-7.flac --fade-out 1.5
    ../../.venv/bin/python ../../kit/beats.py out/glint.mp4 --bpm 120 --check 2,3,3.5,4,6

The card is one shape layer carrying two shaders: PAPER (static texture) then GLINT (a band of
light swept across by an animated uniform). Text sits on its own layers above, untouched. Every
moment sits on the 120 BPM grid (one beat = 0.5 s): each glint crosses the card's centre on a
beat, and the three lines of text arrive on beats.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from kit.lottie import EASE_IN_OUT, Comp  # noqa: E402
from kit.shaders import GLINT, PAPER  # noqa: E402

BPM = 120
BEAT = 60 / BPM
W, H = 1080, 1350
CW, CH = 640, 400
X, Y = (W - CW) // 2, (H - CH) // 2

c = Comp(W, H, fps=30, duration=16 * BEAT, name="glint-card")
c.solid("#1E2328")
card = c.rect(X, Y, CW, CH, "#C9A45C", radius=30, fade=(0.1, 0.5), rise=60, spring=True, name="card")
c.shader(card, PAPER, {"uScale": 2.0, "uAmount": 0.12, "uSeed": 3.0}, name="paper")
# two sweeps; with ease-in-out the band crosses the centre (uPos 0.5) halfway, on beats 4 and 12
c.shader(card, GLINT, {"uSize": [CW, CH], "uWidth": 0.06, "uGain": 0.55,
                       "uPos": c.keys((3 * BEAT, -0.3), (5 * BEAT, 1.3), (11 * BEAT - 0.01, 1.3),
                                      (11 * BEAT, -0.3), (13 * BEAT, 1.3), ease=EASE_IN_OUT)},
         name="glint")
c.text("MEMBER", font="Inter-Bold", size=30, x=X + 48, y=Y + 80, color="#3A2E1A", tracking=300,
       fade=(6 * BEAT, 6 * BEAT + 0.4))
c.text("Ada Lovelace", font="EBGaramond-Regular", size=64, x=X + 48, y=Y + CH - 70, color="#2A2112",
       fade=(7 * BEAT, 7 * BEAT + 0.4), rise=12)
c.text("No. 0001", font="Inter-Regular", size=24, x=X + CW - 48, y=Y + 80, color="#3A2E1A", align="right",
       fade=(8 * BEAT, 8 * BEAT + 0.4))
c.save(HERE / "scene.json")
print("scene.json")
