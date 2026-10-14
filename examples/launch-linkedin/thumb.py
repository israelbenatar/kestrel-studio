"""Cover image for the LinkedIn post (1080x1350, the film's aspect), rendered by kestrel as a still.

    ../../.venv/bin/python thumb.py
    kestrel render thumb.json --frame 0 -o out/thumb.png --fonts ../../fonts

The film's own hook over a real frame of it: the landing page mid-unfold (hf/unfold.mp4 at 5.6 s).
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE))
from art import ART, BRAND, glass, mark_svg, measure  # noqa: E402
from kit.lottie import Comp  # noqa: E402

W, H = 1080, 1350
P = BRAND["palette"]
SANS, SERIF, MONO, SANS_R = "InterTight-SemiBold", "InstrumentSerif-Italic", "JetBrainsMono-Medium", "InterTight-Regular"

bg = ART / "thumb-bg.png"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "5.6", "-i", str(HERE / "hf" / "unfold.mp4"),
                "-frames:v", "1", str(bg)], check=True)

c = Comp(W, H, fps=30, duration=1, name="thumb")
c.image(bg, 0, 0, W, H, name="film frame")
# soft dark gradients behind the text blocks so they read over the aurora (no hard edges)
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
y = np.arange(H, dtype=float)[:, None]
alpha = np.maximum(np.clip(1 - y / 380, 0, 1) ** 1.4 * 0.72, np.clip((y - 960) / 300, 0, 1) ** 1.2 * 0.8)
shade = np.zeros((H, W, 4), np.uint8)
shade[..., :3] = [14, 15, 19]
shade[..., 3] = (alpha * 255).astype(np.uint8).repeat(W, axis=1)
Image.fromarray(shade, "RGBA").save(ART / "thumb-shade.png")
c.image(ART / "thumb-shade.png", 0, 0, W, H, name="shade")

# the hook
line = "Launch videos used to take"
c.text(line, font=SANS, size=58, x=W / 2, y=128, color=P["ink"], align="center", tracking=-15)
wk = "a week."
ww = measure(wk, SANS, 58)
c.text(wk, font=SANS, size=58, x=W / 2, y=196, color=P["muted"], align="center", tracking=-15)
c.rect(W / 2 - ww / 2 - 4, 176, ww + 8, 7, P["accent"], radius=3, name="strike")
c.text("Now: a conversation.", font=SERIF, size=104, x=W / 2, y=296, color=P["accent2"], align="center")

# brand + proof
m = 92
a, b, g = measure("kestrel", SANS, 76), measure("studio", SERIF, 84), 14
total = m + 22 + a + g + b
x0 = (W - total) / 2
c.image(mark_svg(), x0, 1060, m, m, name="mark")
c.text("kestrel", font=SANS, size=76, x=x0 + m + 22, y=1130, color=P["ink"], tracking=-25)
c.text("studio", font=SERIF, size=84, x=x0 + m + 22 + a + g, y=1130, color=P["accent2"])
pill = "▶  This video was made with it"
pw = round(measure(pill, SANS_R, 34) + 64)
gp, pad = glass(pw, 70, 35, "thumb-pill")
c.image(gp, (W - pw) / 2 - pad, 1196 - pad, pw + 2 * pad, 70 + 2 * pad, name="pill")
c.text(pill, font=SANS_R, size=34, x=W / 2, y=1243, color=P["ink"], align="center")

c.save(HERE / "thumb.json")
print("thumb.json")
