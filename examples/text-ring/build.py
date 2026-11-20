"""kestrel studio — text ring (4:5, 7 s): a ring of letters turns in 3D around a title.

    python build.py
    kestrel render scene.json -o out/text-ring.mp4 --fonts ../../fonts

The ring's back half is drawn in a group under the title and its front half in a group above it,
so the title hides the back of the ring. Over a person, put the subject (a matted clip) between
the two groups instead.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

from kit.lottie import Comp  # noqa: E402
from kit.words import ring  # noqa: E402

W, H, FPS, DUR = 1080, 1350, 30, 7.0
BG, INK, MUTED, ACCENT = "#0E0F13", "#F2EEE8", "#8A847C", "#E8743B"

bg = HERE / "media/glow.png"
if not bg.exists():
    bg.parent.mkdir(exist_ok=True)
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.ellipse((140, 380, 940, 1080), fill="#3A1D10")
    im.filter(ImageFilter.GaussianBlur(170)).save(bg)

c = Comp(W, H, fps=FPS, duration=DUR, name="kestrel-studio-text-ring")
c.solid(BG)
c.image(bg, 0, 0, W, H, zoom=((0, DUR), (100, 106)))

back = c.precomp(0, 0, W, H, name="ring back")       # under the title
c.text("kestrel", font="Inter-Bold", size=200, x=W / 2, y=740, color=INK, align="center",
       fade=(0.2, 0.8), rise=30, spring=True)
front = c.precomp(0, 0, W, H, name="ring front")     # over the title

ring(c, "KESTREL STUDIO · KIT.WORDS · 3D RING · ", cx=W / 2, cy=670, radius=400, t0=0.3, t1=DUR,
     back=back, front=front, turns=0.55, start=0.2, tilt=21, size=60, color=ACCENT, step=2)

c.text("kit.words.ring", font="JetBrainsMono-Medium", size=40, x=W / 2, y=1200, color=MUTED,
       align="center", fade=(1.0, 1.5))

c.save(HERE / "scene.json")
print("scene.json", DUR, "s")
