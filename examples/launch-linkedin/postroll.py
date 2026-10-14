"""kestrel studio postroll v1 — the same 3-second ending on every kestrel studio video (skill §9).

    ../../.venv/bin/python postroll.py [--cta "Made with kestrel studio"]
    kestrel render brand/postroll.json -o brand/postroll-4x5.mp4 --fonts ../../fonts

Mark springs in, the wordmark rises, a glint crosses the mark, then the one line the postroll lets
vary (the CTA slot) and the URL. Only the CTA line may change between videos; re-version the file
(postroll-v2) when the brand changes and swap it everywhere at once.
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE))
from art import BRAND, aurora, mark_svg, measure  # noqa: E402
from kit.lottie import EASE_IN_OUT, Comp  # noqa: E402
from kit.shaders import GLINT  # noqa: E402

W, H = 1080, 1350
URL = "github.com/israelbenatar/kestrel-studio"
P = BRAND["palette"]


def build(cta: str, out: Path) -> Path:
    c = Comp(W, H, fps=30, duration=3.0, name="postroll-v1")
    c.image(aurora(), 0, 0, W, H, name="aurora")
    m = 180
    mark = c.image(mark_svg(), (W - m) / 2, 410, m, m, pop=0.15, fade=(0.15, 0.35), name="mark")
    c.shader(mark, GLINT, {"uSize": [m, m], "uWidth": 0.12, "uGain": 0.5,
                           "uPos": c.keys((0.9, -0.3), (1.7, 1.3), ease=EASE_IN_OUT)}, name="glint")
    # wordmark: "kestrel" (Inter Tight SemiBold) + "studio" (Instrument Serif italic), centred as one
    a, b, gap = measure("kestrel", "InterTight-SemiBold", 120), measure("studio", "InstrumentSerif-Italic", 132), 22
    x0 = (W - (a + gap + b)) / 2
    c.text("kestrel", font="InterTight-SemiBold", size=120, x=x0, y=780, color=P["ink"], tracking=-30,
           fade=(0.35, 0.75), rise=24, spring=True)
    c.text("studio", font="InstrumentSerif-Italic", size=132, x=x0 + a + gap, y=780, color=P["accent2"],
           fade=(0.45, 0.85), rise=24, spring=True)
    c.text(cta, font="InterTight-Regular", size=46, x=W / 2, y=905, color=P["ink2"], align="center",
           fade=(0.95, 1.3), rise=12)
    c.text(URL, font="JetBrainsMono-Medium", size=34, x=W / 2, y=990, color=P["accent"], align="center",
           fade=(1.15, 1.5), rise=10)
    return c.save(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cta", default="Marketing & social videos, written as code.")
    a = ap.parse_args()
    (HERE / "brand").mkdir(exist_ok=True)
    print(build(a.cta, HERE / "brand" / "postroll.json"))
