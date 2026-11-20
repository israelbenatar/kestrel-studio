"""kestrel studio — the demo reel (4:5, about 70 s): every effect the kit makes, each with the
prompt that makes it. Built with kestrel from the other examples' films.

    python build.py                      # scene.json and media/audio.flac (the mix)
    kestrel render scene.json -o out/kestrel-demo.mp4 --fonts ../../fonts --audio media/audio.flac

Each feature is a clip from an example film in a card, its name above, and the prompt typed into
a panel below. The sound is the launch track as a bed, with the clip's own sound (a voice, the
drop) on the clips that have it, the bed ducked under them.
"""
import subprocess
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "launch-linkedin"))

from art import BRAND, aurora  # noqa: E402
from kit.lottie import Comp  # noqa: E402

W, H, FPS = 1080, 1350, 30
P = BRAND["palette"]
INK, INK2, ACCENT, PANEL = P["ink"], P["ink2"], P["accent"], "#17181E"
SANS, SERIF, MONO = "InterTight-SemiBold", "InstrumentSerif-Italic", "JetBrainsMono-Medium"
EX = HERE.parent
MUSIC = EX / "launch-linkedin" / "media" / "music-11.flac"

# (name, film, from (s), length (s), prompt, use the clip's sound)
FEATURES = [
    ("The camera follows the subject", "kit-update/out/kit-update.mp4", 6.4, 4.2,
     "Record the app, and push in on each step as it happens.", False),
    ("Waits play fast", "kit-update/out/kit-update.mp4", 10.6, 3.8,
     "Speed through every spinner: no wait longer than 3 s.", False),
    ("The look of your site", "launch-linkedin/out/launch.mp4", 13.5, 2.5,
     "Make a launch film for our product. Take the look from our site.", False),
    ("A glint of light", "glint-card/out/glint.mp4", 2.6, 4.0,
     "Run a slow glint across the member card.", False),
    ("Kinetic words", "kinetic-words/kinetic-words.mp4", 0.0, 4.8,
     "Voice this line, female and warm. Land each word on its time; make 'captions' and 'look' big.", True),
    ("A speaker, with lips in sync", "behind-words/behind-words.mp4", 0.0, 2.4,
     "Make an AI speaker: one still, our voice, lips that follow the words.", True),
    ("Words behind the subject", "behind-words/behind-words.mp4", 2.4, 4.2,
     "Put the key words behind her head.", True),
    ("A ring of words in 3D", "behind-words/behind-words.mp4", 6.6, 2.6,
     "On 'captions, music, the cut', turn a ring of words round her head.", True),
    ("One huge word behind her", "body-words/body-words.mp4", 4.5, 2.2,
     "End each line on one huge word behind her head.", True),
    ("Words on the body", "body-words/body-words.mp4", 6.65, 3.1,
     "Set the words on her shoulders, and keep them there as she moves.", True),
    ("Rows on a diagonal", "poster-titles/poster-titles.mp4", 0.2, 3.8,
     "Fill the frame with red diagonal rows of the line, then cut in square blocks.", False),
    ("Stepped sizes", "poster-titles/poster-titles.mp4", 3.75, 2.85,
     "Black poster words on yellow, each one bigger than the last.", False),
    ("A pen circle", "poster-titles/poster-titles.mp4", 6.75, 3.3,
     "Circle Friday the 20th like a pen, then stamp SHIP.", False),
    ("A heavy italic", "poster-titles/poster-titles.mp4", 10.1, 3.5,
     "Throw AWAY. in from the right, out of a blur.", False),
    ("Music on the beat", "launch-linkedin/out/launch.mp4", 19.8, 2.9,
     "Make three instrumental takes at 120 BPM. Cut on the beat; hit the drop.", True),
]
INTRO, OUTRO, GAP = 3.2, 4.0, 0.0
CARD_W, CARD_H = 640, 800
CX, CY = (W - CARD_W) / 2, 214
PANEL_Y = 1046

starts, t = [], INTRO
for f in FEATURES:
    starts.append(t)
    t += f[3] + GAP
DUR = round(t + OUTRO, 2)

c = Comp(W, H, fps=FPS, duration=DUR, name="kestrel-studio-demo")
c.image(aurora(), 0, 0, W, H, zoom=((0, DUR), (100, 108)))

# ---------- intro ----------
c.text("kestrel studio", font=MONO, size=42, x=W / 2, y=520, color=INK2, align="center", op=INTRO,
       fade=(0.1, 0.5), fade_out=(INTRO - 0.3, INTRO))
c.text("Every effect,", font=SANS, size=88, x=W / 2, y=680, color=INK, align="center", op=INTRO,
       fade=(0.3, 0.7), rise=30, spring=True, fade_out=(INTRO - 0.3, INTRO))
c.text("and the prompt that makes it.", font=SERIF, size=84, x=W / 2, y=785, color=ACCENT, align="center",
       op=INTRO, fade=(0.7, 1.1), rise=30, spring=True, fade_out=(INTRO - 0.3, INTRO))

# ---------- the features ----------
for n, ((name, film, src, length, prompt, _), s0) in enumerate(zip(FEATURES, starts)):
    s1 = s0 + length
    out = (s1 - 0.15, s1)
    c.text(f"{n + 1:02d} / {len(FEATURES)}", font=MONO, size=30, x=W - 80, y=112, color=INK2, align="right",
           ip=s0, op=s1, fade=(s0, s0 + 0.2), fade_out=out, decor=True)
    c.text("kestrel studio", font=MONO, size=30, x=80, y=112, color=INK2, ip=s0, op=s1,
           fade=(s0, s0 + 0.2), fade_out=out, decor=True)
    c.text(name, font=SANS, size=58, x=W / 2, y=184, color=INK, align="center", ip=s0, op=s1,
           fade=(s0, s0 + 0.2), rise=16, fade_out=out)
    c.video(EX / film, CX, CY, CARD_W, CARD_H, start=s0 - src, radius=26, ip=s0, op=s1,
            fade=(s0, s0 + 0.15), pop=s0, fade_out=out)
    # the prompt: typed into a panel, as you would type it to the agent
    lines = textwrap.wrap(prompt, 34)
    ph = 74 + 52 * len(lines)
    c.rect(80, PANEL_Y, W - 160, ph, PANEL, radius=22, ip=s0, op=s1, fade=(s0, s0 + 0.2), fade_out=out)
    c.text("you ›", font=MONO, size=30, x=112, y=PANEL_Y + 46, color=ACCENT, ip=s0, op=s1,
           fade=(s0, s0 + 0.2), fade_out=out, decor=True)
    body = "\n".join(lines)
    typed = (s0 + 0.25, min(s1 - 0.6, s0 + 0.25 + 0.028 * len(body)))
    c.text(body, font=MONO, size=42, x=112, y=PANEL_Y + 104, color=INK, line_height=52, ip=s0, op=s1,
           typewriter=typed, fade_out=out)

# ---------- outro ----------
o0 = starts[-1] + FEATURES[-1][3]
c.text("Write it.", font=SANS, size=120, x=W / 2, y=600, color=INK, align="center", ip=o0,
       fade=(o0 + 0.1, o0 + 0.5), rise=30, spring=True)
c.text("Render it.", font=SERIF, size=120, x=W / 2, y=740, color=ACCENT, align="center", ip=o0,
       fade=(o0 + 0.5, o0 + 0.9), rise=30, spring=True)
c.text("github.com/israelbenatar/kestrel-studio", font=MONO, size=42, x=W / 2, y=900, color=INK2,
       align="center", ip=o0, fade=(o0 + 1.1, o0 + 1.6))

c.save(HERE / "scene.json")


# ---------- the sound ----------
def mix(out: Path):
    """The bed (the launch track, ducked to 15% under clips with their own sound) and each such
    clip's sound at its place, with short fades so no cut clicks."""
    voiced = [(s, s + f[3]) for f, s in zip(FEATURES, starts) if f[5]]
    duck = "+".join(f"between(t,{a - 0.05:.2f},{b:.2f})" for a, b in voiced)
    inputs, chains, labels = ["-i", str(MUSIC)], [], []
    chains.append(f"[0:a]aloop=loop=-1:size=2e9,atrim=0:{DUR},volume='if({duck},0.15,0.55)':eval=frame,"
                  f"afade=t=in:d=0.5,afade=t=out:st={DUR - 2}:d=2[bed]")
    for k, ((name, film, src, length, _, sound), s0) in enumerate(zip(FEATURES, starts)):
        if not sound:
            continue
        inputs += ["-i", str(EX / film)]
        i = len(inputs) // 2 - 1
        ms = int(s0 * 1000)
        chains.append(f"[{i}:a]atrim={src}:{src + length},asetpts=PTS-STARTPTS,afade=t=in:d=0.06,"
                      f"afade=t=out:st={length - 0.12}:d=0.12,adelay={ms}|{ms}[a{k}]")
        labels.append(f"[a{k}]")
    chains.append(f"[bed]{''.join(labels)}amix=inputs={1 + len(labels)}:normalize=0:duration=first[m]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(chains), "-map", "[m]",
                    "-ar", "48000", "-ac", "2", str(out)], check=True)


(HERE / "media").mkdir(exist_ok=True)
mix(HERE / "media" / "audio.flac")
print("scene.json + media/audio.flac", DUR, "s")
