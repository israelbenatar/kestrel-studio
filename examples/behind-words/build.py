"""kestrel studio — words behind the subject (4:5, 9.75 s): a person talks, the key words land behind
her, and a ring of words turns around her head.

    python build.py
    kestrel render scene.json -o out/behind-words.mp4 --fonts ../../fonts --audio media/voice.flac

Sources (media/, not in git):
  portrait.png      AI-generated still (Flux 1.1 Pro on Replicate), a generic Israeli look. Not a real person.
  voice.flac        python -m kit.voice "..." --voice female --style "...a light, natural Israeli accent..."
  talk.mp4          the still animated by the voice (OmniHuman 1.5 on Replicate, kit.replicate): the lips
                    follow the real words
  person-4x5.mp4    ffmpeg -i talk.mp4 -vf scale=1080:-2,crop=1080:1350:0:0,fps=24 ...  (the top: room above her head)
  person-alpha.mov  the person alone:  npx hyperframes remove-background person-4x5.mp4 -o person-alpha.mov --device cpu
words.json holds the word times (kit.words.transcribe), so a rebuild does not run whisper.

Layers, bottom to top: the clip; a "behind" group (the key words, the back of the ring); the person
cut out; a "front" group (the front of the ring); the small words and the subtitle.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from kit.lottie import Comp  # noqa: E402
from kit.words import kinetic, ring  # noqa: E402

W, H, FPS, DUR = 1080, 1350, 24, 9.75
INK, ACCENT, WHITE = "#16181F", "#6B200C", "#FFFFFF"   # dark words on the taupe wall
M = HERE / "media"

words = [tuple(w) for w in json.loads((HERE / "words.json").read_text())]
# the model decides the breaks and the keys
GROUPS = [words[0:6], words[6:8], words[8:14], words[14:19], words[19:23], words[23:24]]
RING = GROUPS[4]                                     # "Captions, music, the cut," turns around her head
KEYS = {"editing", "itself", "done"}                # few, so each one lands (a key word must stay sharp > 0.5 s)

c = Comp(W, H, fps=FPS, duration=DUR, name="kestrel-studio-behind-words")
c.video(M / "person-4x5.mp4", 0, 0, W, H)
behind = c.precomp(0, 0, W, H, name="behind")
c.video(M / "person-alpha.mov", 0, 0, W, H, name="person")
front = c.precomp(0, 0, W, H, name="front")

spots = [("center", 0.05), ("center", 0.19), ("center", 0.05), ("center", 0.19), ("center", 0), ("center", 0.19)]                          # small-only phrases sit high, clear of the key words below them
kinetic(c, GROUPS, keys=KEYS, x=70, y=110, w=W - 140, h=1000, font_small="Inter-Bold", small=54,
        font_big="Anton-Regular", big=330, big_cap=0.86, color=INK, accent=ACCENT, tilt=(0,), spots=spots,
        behind=behind, end=DUR, hide={4}, subtitle={"y": 1250, "size": 40, "color": WHITE, "panel": INK})

ring(c, "CAPTIONS · MUSIC · THE CUT · " * 2, cx=W / 2, cy=640, radius=340, t0=RING[0][1] - 0.1, t1=RING[-1][2] + 0.35,
     back=behind, front=front, turns=0.4, start=0.05, tilt=30, font="Anton-Regular", size=64, color=INK,
     back_opacity=55, fade=0.3, step=1)

c.save(HERE / "scene.json")
print("scene.json", DUR, "s")
