"""kestrel studio — words on the body (4:5, 9.75 s): one huge word fills the frame behind the
speaker, small lines ride above her head, and words sit on her shoulders as she moves.

    python build.py
    kestrel render scene.json -o out/body-words.mp4 --fonts ../../fonts --audio ../behind-words/media/voice.flac

The speaker, the voice and the matte are the ones from examples/behind-words (media/, not in git):
no new paid runs. track.json holds her head and shoulders per frame (kit.track.silhouette, measured
from the matte), so a rebuild does not read the matte again.

Layers, bottom to top: the clip; a "behind" group (the huge words); the person cut out; a "front"
group (the words on her shoulders and above her head); the subtitle.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from kit.lottie import Comp  # noqa: E402
from kit.poster import big_word  # noqa: E402
from kit.track import along, pin, silhouette  # noqa: E402
from kit.words import kinetic  # noqa: E402

W, H, FPS, DUR = 1080, 1350, 24, 9.75
INK, BRICK, WHITE = "#16181F", "#6B200C", "#FFFFFF"
M = HERE.parent / "behind-words" / "media"

words = [tuple(w) for w in json.loads((HERE.parent / "behind-words" / "words.json").read_text())]
tr = silhouette(M / "person-alpha.mov", fps=FPS, cache=HERE / "track.json")

c = Comp(W, H, fps=FPS, duration=DUR, name="kestrel-studio-body-words")
c.video(M / "person-4x5.mp4", 0, 0, W, H)
behind = c.precomp(0, 0, W, H, name="behind")
c.video(M / "person-alpha.mov", 0, 0, W, H, name="person")
front = c.precomp(0, 0, W, H, name="front")


def t(i, end=False):
    return words[i][2 if end else 1]


# huge words behind her head, each at the end of its phrase
for word, i, until, colour in [("EDITING", 7, t(8) - 0.05, INK), ("STORY", 13, t(14) - 0.05, BRICK),
                               ("ITSELF", 18, t(19) - 0.05, INK), ("DONE.", 23, DUR, BRICK)]:
    big_word(behind, word, t0=t(i) - 0.05, t1=until, color=colour, cy=560, width=0.9)

# lines that ride above her head, until the huge word lands
for lines, i0, i_end in [(["I used to lose", "whole days to"], 0, 7), (["Now I just", "write the"], 8, 13),
                         (["and the video", "edits"], 14, 18)]:
    for n, line in enumerate(lines):
        first = sum(len(l.split()) for l in lines[:n])
        pin(front, line, tr, "head_top", t0=t(i0 + first), t1=t(i_end) - 0.05, dy=-150 + n * 66,
            font="Inter-Bold", size=54, color=INK, align="center")

# words on her shoulders, turned to the shoulder line
for word, i, at, lift in [("CAPTIONS", 19, 0.2, 14), ("MUSIC", 20, 0.8, 14), ("THE CUT.", 21, 0.5, -170)]:
    along(front, word, tr, t0=t(i), t1=t(23) - 0.05, at=at, lift=lift, size=84, color=INK)

# the subtitle only: every phrase hidden, its line kept
GROUPS = [words[0:8], words[8:14], words[14:19], words[19:23], words[23:24]]
kinetic(c, GROUPS, keys=set(), end=DUR, hide=set(range(len(GROUPS))),
        subtitle={"y": 1250, "size": 40, "color": WHITE, "panel": INK})

c.save(HERE / "scene.json")
print("scene.json", DUR, "s")
