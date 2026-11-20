"""kestrel studio — kinetic words (4:5, about 11 s): the voice-over lands in the frame one word at a time.

    python build.py
    kestrel render scene.json -o out/kinetic-words.mp4 --fonts ../../fonts --audio voice.flac

The voice is Gemini TTS (kit.voice, the Kore voice), kept as voice.flac. The word times come from
whisper (kit.words.transcribe) and are kept in words.json, so a rebuild does not run the model again.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

from kit.lottie import LINEAR, Comp  # noqa: E402
from kit.words import kinetic, phrases, transcribe  # noqa: E402

W, H, FPS = 1080, 1350, 30
BG, INK, MUTED, ACCENT = "#0E0F13", "#F2EEE8", "#8A847C", "#E8743B"

cache = HERE / "words.json"
if not cache.exists():
    cache.write_text(json.dumps(transcribe(HERE / "voice.flac", language="en"), indent=1))
words = [tuple(w) for w in json.loads(cache.read_text())]
DUR = round(words[-1][2] + 1.4, 2)

# a soft, dark light behind the words: two blurred glows, drawn once
bg = HERE / "media/glow.png"
if not bg.exists():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.ellipse((-260, 820, 620, 1700), fill="#3A1D10")
    d.ellipse((560, -300, 1420, 560), fill="#18213F")
    im.filter(ImageFilter.GaussianBlur(160)).save(bg)

c = Comp(W, H, fps=FPS, duration=DUR, name="kestrel-studio-kinetic-words")
c.solid(BG)
c.image(bg, 0, 0, W, H, zoom=((0, DUR), (100, 108)))

# the model decides: which words carry each line
KEYS = {"captions", "bottom", "look", "word", "matter", "hardest"}
kinetic(c, phrases(words), keys=KEYS, x=80, y=150, h=1000, color=INK, accent=ACCENT,
        subtitle={"y": 1240, "size": 40, "color": MUTED})

c.text("kestrel studio · kit.words", font="JetBrainsMono-Medium", size=40, x=80, y=110, color=MUTED, ip=0,
       fade=(0, 0.4))

c.save(HERE / "scene.json")
print(f"scene.json  {DUR} s  {len(words)} words  {len(phrases(words))} phrases")
