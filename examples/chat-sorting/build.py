"""Sustain feature film: the 4:5 "re-sort by asking" video, a Lottie scene for kestrel.

Intro, three asks (each with the chat recording, a rebuild cut and a board of the result), outro,
with real motion: typed requests, per-character title reveals, cards that rise in, slow push-ins on
photos. HyperFrames renders the intro and a transparent outro that kestrel composites.

    ../../.venv/bin/python build.py          # media/ + scene.json
    kestrel render scene.json -o out/raw.mp4 --fonts ../../fonts --audio $SRC/music.mp3 --fade-out 2
    ../../.venv/bin/python -m kit.finish out/raw.mp4 out/finished.mp4 --flash ...

Showcase: the inputs (Playwright recordings of the Sustain app and the demo album's photos, whose
people are AI-generated) live in sources/ and are not in git, so this example documents the method
rather than rebuilding from a fresh clone.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from kit.lottie import Comp  # noqa: E402

REC = HERE / "sources" / "recordings"
# inputs (not in git): screen recordings of the Sustain app and its demo album's photos
# (AI-generated people), under sources/
ALBUM = HERE / "sources" / "album"
FONTS = HERE.parent.parent / "fonts"
MEDIA = HERE / "media"
MEDIA.mkdir(exist_ok=True)
# HyperFrames renders of the parts HTML does best (CSS 3D, blur, glass); kestrel composites them
HF_INTRO, HF_OUTRO = HERE / "hf" / "intro.mp4", HERE / "hf" / "outro.mp4"
# transparent (ProRes 4444) outro: HyperFrames type and glass chips over kestrel's own photo layers
HF_OUTRO_ALPHA = HERE / "hf" / "outro-alpha.mov"

W, H, FPS = 1080, 1350, 30
CREAM, INK, TERRA, MUTED, DOT_OFF = "#F5F0E8", "#2D3436", "#B07A64", "#6E6862", "#D6CDC2"
CHAT = (1048, 600, 1422, 884)        # chat panel crop in the 1440x900 recordings
STRIP = (120, 812, 760, 895)         # page strip with its chapter labels
CHAT_W = 900
CHAT_H = round(CHAT_W * (CHAT[3] - CHAT[1]) / (CHAT[2] - CHAT[0]) / 2) * 2   # even, for x264
STRIP_W = W - 120
STRIP_H = round(STRIP_W * (STRIP[3] - STRIP[1]) / (STRIP[2] - STRIP[0]) / 2) * 2
HOLD, REBUILD, PAYOFF, XF = 0.5, 1.0, 4.5, 0.35

SEGMENTS = [
    ("1 · By date", "“Put my album in date order, oldest photos first.”",
     [("date", 10.0, 13.6, 1.0), ("date", 13.6, 33.6, 10.0), ("date", 33.6, 38.2, 1.1)],
     "Oldest to newest",
     [("2000 · Birthday cake", ["bday-02"]), ("2001 · First sandcastle", ["sea-01"]),
      ("2004 · First day of school", ["school-06"]), ("2009 · Paris", ["city-11"]),
      ("2016 · Graduation", ["school-18"]), ("2024 · Times Square", ["city-26"])]),
    ("2 · By theme", "“Now group the album by theme instead of by date.”",
     [("theme", 11.3, 14.6, 1.0), ("theme", 14.6, 29.0, 8.0), ("theme", 29.0, 34.0, 1.0), ("theme", 34.0, 41.0, 2.4)],
     "New chapters",
     [("Children's Birthdays", ["bday-02", "bday-05", "bday-09", "bday-16"]),
      ("Family Moments", ["win-07", "fam-gp", "win-23", "hike-04"]),
      ("Travels", ["city-11", "city-16", "city-20", "city-26"]),
      ("Outdoors", ["sea-01", "hike-13", "win-19", "sea-20"]),
      ("Portraits", ["city-24", "bday-25", "school-14"]),
      ("Celebrations", ["school-18", "school-22", "fam-ben", "fam-kitchen"])]),
    ("3 · Your own chapters", "“Use my own chapters: Summers by the Sea, Birthday Wishes, Snow Days… and sort the photos in.”",
     [("chapters", 8.8, 14.6, 1.0), ("chapters", 14.6, 36.0, 10.0), ("chapters", 36.0, 49.0, 1.6)],
     "Your chapters, photos sorted in",
     [("Summers by the Sea", ["sea-01", "sea-08", "sea-12", "sea-20"]),
      ("Birthday Wishes", ["bday-02", "bday-09", "bday-12", "bday-16"]),
      ("Snow Days", ["win-03", "win-11", "win-15", "win-19"]),
      ("Wild Places", ["hike-13", "hike-17", "hike-20", "hike-24"]),
      ("Big Milestones", ["school-06", "school-18", "school-22", "fam-ben"]),
      ("Postcards from Abroad", ["city-11", "city-16", "city-20", "city-26"])]),
]


# ---------- media prep ----------
def clip(si, pieces, crop, size, pad):
    """The segment's recording pieces, each at its speed, cropped to *crop*, held *pad* s at the end."""
    out = MEDIA / f"s{si}-{'chat' if crop == CHAT else 'strip'}.mp4"
    x0, y0, x1, y1 = crop
    parts, inputs = [], []
    for k, (name, t0, t1, speed) in enumerate(pieces):
        inputs += ["-ss", str(t0), "-to", str(t1), "-i", str(REC / f"{name}.webm")]
        parts.append(f"[{k}:v]setpts=(PTS-STARTPTS)/{speed},fps={FPS},crop={x1 - x0}:{y1 - y0}:{x0}:{y0},"
                     f"scale={size[0]}:{size[1]}:flags=lanczos,setsar=1[p{k}]")
    graph = ";".join(parts) + ";" + "".join(f"[p{k}]" for k in range(len(pieces))) + \
        f"concat=n={len(pieces)}:v=1:a=0,tpad=stop_mode=clone:stop_duration={pad}[v]"
    if not out.exists():
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[v]",
                        "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out, sum((t1 - t0) / s for _, t0, t1, s in pieces)


def photo_tile(key, w, h):
    out = MEDIA / f"{key}-{w}x{h}.jpg"
    if not out.exists():
        p = ALBUM / "video-photos" / f"{key}.jpg"
        im = Image.open(p if p.exists() else ALBUM / "photos" / f"{key}.jpg").convert("RGB")
        # a little bigger than the slot, so the slow push-in never shows an edge
        s = max(w / im.width, h / im.height)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        x, y = (im.width - w) // 2, int((im.height - h) * 0.35)
        im.crop((x, y, x + w, y + h)).save(out, quality=92)
    return out


def shadow(w, h, r=26, blur=18, alpha=70):
    out = MEDIA / f"shadow-{w}x{h}.png"
    if not out.exists():
        pad = blur * 3
        im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle((pad, pad + 10, pad + w, pad + h + 10), r, fill=(60, 40, 30, alpha))
        im.filter(ImageFilter.GaussianBlur(blur)).save(out)
    return out, blur * 3


def wrap(text, font_file, size, width):
    font = ImageFont.truetype(str(FONTS / f"{font_file}.ttf"), size)
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if d.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = word
    return lines + [cur]


# ---------- scene ----------
def dots(c, t0, t1, active):
    for i in range(3):
        c.circle(W / 2 - 40 + i * 40, H - 53, 14, TERRA if i <= active else DOT_OFF, ip=t0, op=t1,
                 fade=(t0, t0 + XF), fade_out=(t1 - XF, t1), name=f"dot{i}")


def build():
    timeline = [("intro", 2.6)]
    media = []
    for si, (_title, _req, pieces, *_rest) in enumerate(SEGMENTS):
        chat_len = sum((t1 - t0) / s for _, t0, t1, s in pieces)
        pad = HOLD + REBUILD + 0.2
        media.append((clip(si, pieces, CHAT, (CHAT_W, CHAT_H), pad)[0], clip(si, pieces, STRIP, (STRIP_W, STRIP_H), pad)[0],
                      chat_len))
        timeline += [(f"ask{si}", chat_len + HOLD + REBUILD), (f"board{si}", PAYOFF)]
    timeline.append(("outro", 3.2))
    duration = sum(d for _, d in timeline)
    c = Comp(W, H, fps=FPS, duration=duration, name="chat-sorting")
    c.solid(CREAM)

    starts, t = {}, 0.0
    for name, d in timeline:
        starts[name] = (t, t + d)
        t += d
    cuts = [round(s, 2) for s, _ in list(starts.values())[1:]]

    # intro: the HyperFrames clip (hf/intro, rendered by HyperFrames) when present, else native text
    a, b = starts["intro"]
    if HF_INTRO.exists():
        c.video(HF_INTRO, 0, 0, W, H, start=a, ip=a, op=b, fade_out=(b - XF, b), name="hf intro")
    else:
        c.text("One album.", font="EBGaramond-Regular", size=92, x=W / 2, y=520, align="center", color=INK, ip=a, op=b,
               reveal=(a + 0.15, a + 0.9), fade_out=(b - XF, b))
        c.text("Any order you like.", font="EBGaramond-Italic", size=92, x=W / 2, y=630, align="center", color=TERRA,
               ip=a, op=b, reveal=(a + 0.7, a + 1.5), fade_out=(b - XF, b))
        c.text("Just ask the Sustain chat.", font="Inter-Regular", size=30, x=W / 2, y=780, align="center", color=MUTED,
               ip=a, op=b, fade=(a + 1.4, a + 1.9), rise=14, fade_out=(b - XF, b))

    for si, (title, request, pieces, heading, cells) in enumerate(SEGMENTS):
        chat_mp4, strip_mp4, chat_len = media[si]
        a, b = starts[f"ask{si}"]
        c.text(title, font="Inter-Bold", size=26, x=60, y=82, color=TERRA, ip=a, op=b, fade=(a, a + XF),
               fade_out=(b - XF, b), tracking=20)
        lines = wrap(request, "EBGaramond-Italic", 40, W - 120)
        c.text("\n".join(lines), font="EBGaramond-Italic", size=40, line_height=50, x=60, y=140, color=INK, ip=a, op=b,
               typewriter=(a + 0.2, a + 0.2 + 0.02 * len(request)), fade_out=(b - XF, b))
        cy = max(140 + 50 * (len(lines) - 1) + 50, 300)
        sh, pad = shadow(CHAT_W, CHAT_H)
        card_in = (a + 0.15, a + 0.75)
        c.image(sh, (W - CHAT_W) // 2 - pad, cy - pad, CHAT_W + 2 * pad, CHAT_H + 2 * pad, ip=a, op=b,
                fade=card_in, rise=40, fade_out=(b - XF, b), name="card shadow")
        c.video(chat_mp4, (W - CHAT_W) // 2, cy, CHAT_W, CHAT_H, start=a, radius=24, ip=a, op=b, fade=card_in, rise=40,
                fade_out=(b - XF, b), name="chat")
        sy = cy + CHAT_H + 40
        c.text("Your album", font="Inter-Bold", size=24, x=60, y=sy + 22, color=MUTED, ip=a, op=b,
               fade=(a + 0.4, a + 0.9), fade_out=(b - XF, b), tracking=20)
        c.video(strip_mp4, 60, sy + 40, STRIP_W, STRIP_H, start=a, radius=8, ip=a, op=b, fade=(a + 0.4, a + 0.9),
                rise=24, fade_out=(b - XF, b), name="strip")
        # the cut over the wait: a cream veil, the words, three breathing dots
        r0 = a + chat_len + HOLD
        c.rect(0, 0, W, H, CREAM, ip=r0, op=b, opacity=90, fade=(r0, r0 + 0.25), name="veil")
        c.text("Rebuilding the album…", font="EBGaramond-Regular", size=64, x=W / 2, y=cy + CHAT_H // 2, align="center",
               color=INK, ip=r0, op=b, fade=(r0 + 0.05, r0 + 0.3), rise=10)
        for i in range(3):
            o = c.keys(*[(r0 + 0.3 + i * 0.12 + k * 0.36, [35, 100][k % 2]) for k in range(3)])
            dot = c.circle(W / 2 - 24 + i * 24, cy + CHAT_H // 2 + 50, 10, TERRA, ip=r0, op=b, name="pulse")
            dot["ks"]["o"] = o
        dots(c, a, b, si)

        # the board: chapters with their photos
        a, b = starts[f"board{si}"]
        c.text(title, font="Inter-Bold", size=26, x=60, y=82, color=TERRA, ip=a, op=b, fade=(a, a + XF),
               fade_out=(b - XF, b), tracking=20)
        c.text(heading, font="EBGaramond-Regular", size=58, x=60, y=152, color=INK, ip=a, op=b,
               reveal=(a + 0.05, a + 0.6), fade_out=(b - XF, b))
        single = all(len(k) == 1 for _, k in cells)
        cw, gap = (W - 120 - 40) // 2, 10
        ph = 276 if single else 135
        rowh = 40 + (ph if single else 2 * ph + gap) + 28
        hw = (cw - gap) // 2
        for i, (name, keys) in enumerate(cells):
            x, y = 60 + (i % 2) * (cw + 40), 196 + (i // 2) * rowh
            t_in = a + 0.3 + i * 0.28
            inn = (t_in, t_in + 0.5)
            c.circle(x + 6, y + 17, 12, TERRA, ip=a, op=b, fade=inn, rise=24, fade_out=(b - XF, b))
            c.text(name, font="Inter-Bold", size=28, x=x + 24, y=y + 28, color=INK, ip=a, op=b, fade=inn, rise=24,
                   fade_out=(b - XF, b))
            if single:
                boxes = [(0, 40, cw, ph)]
            elif len(keys) == 3:
                boxes = [(0, 40, cw, ph), (0, 40 + ph + gap, hw, ph), (hw + gap, 40 + ph + gap, hw, ph)]
            else:
                boxes = [((k % 2) * (hw + gap), 40 + (k // 2) * (ph + gap), hw, ph) for k in range(4)]
            for k, (key, (bx, by, bw, bh)) in enumerate(zip(keys, boxes)):
                tk = t_in + 0.06 * k
                c.image(photo_tile(key, bw, bh), x + bx, y + by, bw, bh, radius=12, ip=a, op=b,
                        fade=(tk, tk + 0.5), rise=24, fade_out=(b - XF, b), zoom=((tk, b), (100, 104)))
        dots(c, a, b, si)

    # outro: the HyperFrames finale (chapter chips gather round the wordmark) when present
    a, b = starts["outro"]
    if HF_OUTRO_ALPHA.exists():
        # kestrel keeps the last board's photos on screen, dimmed and drifting; HyperFrames lays its
        # panel, type and chips over them with real transparency
        cells = SEGMENTS[-1][4]
        cw, gap, ph = (W - 120 - 40) // 2, 10, 135
        hw, rowh = (cw - gap) // 2, 40 + 2 * 135 + 10 + 28
        for i, (_name, keys) in enumerate(cells):
            x, y = 60 + (i % 2) * (cw + 40), 196 + (i // 2) * rowh
            for k, key in enumerate(keys):
                bx, by = (k % 2) * (hw + gap), 40 + (k // 2) * (ph + gap)
                c.image(photo_tile(key, hw, ph), x + bx, y + by, hw, ph, radius=12, ip=a, op=b, opacity=45,
                        zoom=((a, b), (100, 106)), name="outro photo")
        c.video(HF_OUTRO_ALPHA, 0, 0, W, H, start=a, ip=a, op=b, name="hf outro (alpha)")
    elif HF_OUTRO.exists():
        c.video(HF_OUTRO, 0, 0, W, H, start=a, ip=a, op=b, fade=(a, a + 0.25), name="hf outro")
    else:
        c.text("Just ask.", font="EBGaramond-Regular", size=110, x=W / 2, y=500, align="center", color=INK, ip=a, op=b,
               reveal=(a + 0.1, a + 0.7))
        c.text("By date, by theme, or your own chapters —\nthe chat re-sorts the whole album for you.", font="Inter-Regular",
               size=30, line_height=46, x=W / 2, y=640, align="center", color=MUTED, ip=a, op=b, fade=(a + 0.6, a + 1.1),
               rise=14)
        c.text("Sustain", font="DancingScript-Bold", size=96, x=W / 2, y=890, align="center", color=TERRA, ip=a, op=b,
               reveal=(a + 1.0, a + 1.8))
        c.text("sustain-app.com", font="Inter-Regular", size=30, x=W / 2, y=960, align="center", color=INK, ip=a, op=b,
               fade=(a + 1.6, a + 2.0))

    c.save(HERE / "scene.json")
    (HERE / "cuts.json").write_text(json.dumps(cuts))
    print(f"scene.json  {duration:.1f}s  {len(c.layers)} layers  cuts {cuts}")


if __name__ == "__main__":
    build()
