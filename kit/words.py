"""Kinetic words: the voice-over as words that land in the frame one at a time.

Each spoken word appears at its own time, where the eye is, not in a caption bar. Small words
("and", "the", "at") stay small and plain; the words that carry the line are set large in the
accent colour. A word comes into focus from a blur; when its phrase ends it goes back into the
blur and fades, so the last phrase is still a faint echo while the next one lands.

    from kit.words import transcribe, phrases, kinetic
    words = transcribe("media/voice.wav")                   # [(word, t0, t1), ...]
    groups = phrases(words)                                 # where the lines break
    kinetic(c, groups, keys={"captions", "look", "hardest"}, ...)

The tool measures (word times, text widths); the model decides (which words are keys, where a
line breaks when the default is wrong: pass your own groups).
"""
from __future__ import annotations

from pathlib import Path

from .check import _width
from .lottie import EASE_OUT, LINEAR, Comp, static

MODEL = "mlx-community/whisper-large-v3-turbo"
SMALL_WORDS = set("""a an and are as at be but by for from had has have i if in into is it its it's of on or our
so than that the their then there these they this to was we were what when where which who will with you your""".split())
PUNCT = ".,!?;:"


def transcribe(path, *, model=MODEL, language=None) -> list[tuple[str, float, float]]:
    """Word times for a voice file, with mlx-whisper (Apple silicon, runs on this machine)."""
    import mlx_whisper
    r = mlx_whisper.transcribe(str(path), path_or_hf_repo=model, word_timestamps=True, language=language)
    return [(w["word"].strip(), float(w["start"]), float(w["end"])) for s in r["segments"] for w in s["words"]]


def _bare(word: str) -> str:
    return word.strip(PUNCT + "\"'“”‘’").lower()


def phrases(words, *, most=6, gap=0.35):
    """Break the words into phrases: at the end of a sentence or clause, at a pause longer than
    *gap*, and so that no phrase has more than *most* words (a long one breaks before the small
    word nearest its middle: "Most captions just sit | at the bottom of the frame.")."""
    out, cur = [], []
    for n, w in enumerate(words):
        cur.append(w)
        nxt = words[n + 1] if n + 1 < len(words) else None
        if nxt is None or w[0][-1:] in PUNCT or nxt[1] - w[2] > gap:
            out.append(cur)
            cur = []
    done = []
    while out:
        p = out.pop(0)
        if len(p) <= most:
            done.append(p)
            continue
        mid = len(p) / 2
        cuts = [i for i in range(2, len(p) - 1)        # before the first of a run of small words
                if _bare(p[i][0]) in SMALL_WORDS and _bare(p[i - 1][0]) not in SMALL_WORDS] or [round(mid)]
        i = min(cuts, key=lambda i: abs(i - mid))
        out[:0] = [p[:i], p[i:]]
    return done


# ---------- layout ----------
def _lines(group, keys, small, big, font_small, font_big, max_w, fonts):
    """A phrase as lines: small words share a line; each key word has its own large line."""
    lines = []
    for w in group:
        if _bare(w[0]) in keys:
            size = big
            width = _width(w[0], font_big, size, 0, fonts)
            if width > max_w:
                size *= max_w / width
                width = max_w
            lines.append({"big": True, "size": size, "font": font_big, "words": [(w, 0, width)], "w": width})
        else:
            if not lines or lines[-1]["big"]:
                lines.append({"big": False, "size": small, "font": font_small, "words": [], "w": 0})
            ln = lines[-1]
            x = ln["w"] + (_width(" ", font_small, small, 0, fonts) if ln["words"] else 0)
            width = _width(w[0], font_small, small, 0, fonts)
            if x + width > max_w:                       # too long: a new small line
                lines.append({"big": False, "size": small, "font": font_small, "words": [], "w": 0})
                ln, x = lines[-1], 0
            ln["words"].append((w, x, width))
            ln["w"] = x + width
    # small lines after a large one end at its right edge; the rest start at the left
    block_w = max(ln["w"] for ln in lines)
    prev_big = None
    for ln in lines:
        ln["x"] = (prev_big["x"] + prev_big["w"] - ln["w"]) if (not ln["big"] and prev_big) else 0
        if ln["big"]:
            ln["x"] = 0
            prev_big = ln
    return lines, block_w


SPOTS = [("left", 0.20), ("right", 0.62), ("left", 0.38), ("right", 0.22), ("center", 0.58)]


def kinetic(c: Comp, groups, *, keys, x=80, y=120, w=None, h=None, font_small="InterTight-SemiBold",
            font_big="Inter-Bold", small=58, big=170, color="#F2EEE8", accent="#E8743B", tilt=(-4, 3, 0),
            spots=SPOTS, fonts=Path(__file__).resolve().parent.parent / "fonts", end=None,
            focus=0.28, ghost=0.9, subtitle=None, behind=None, big_cap=0.72, hide=(), hold=0.6):
    """Place *groups* (from phrases()) in the box (x, y, w, h) of *c*, one word at a time.

    keys: the words that carry the line (lower case, no punctuation): large and in *accent*.
    tilt: angles in degrees, used in turn for the large words.
    spots: where each phrase sits, in turn: (left | right | center, height of its middle as a share of h).
    end: when the last phrase leaves (default: it stays to the end of the comp).
    hold: a phrase stays until each of its key words has been sharp this long, even when the next
    phrase has started (a key word that blurs out after 0.3 s is not read).
    hide: indices of groups whose words are not drawn (shown another way, such as a ring) but
    still keep the timing and the subtitle.
    behind: a layer group under the subject (a precomp the size of *c*, placed at 0, 0): the key
    words go there, so a matted subject in front of it hides part of them. Small words stay on *c*.
    big_cap: the large font's cap height as a share of its size (0.72 for Inter; about 0.86 for a
    narrow poster face such as Anton), so the lines stack without touching.
    subtitle: dict(y=, size=, color=, font=, panel="#000000", panel_opacity=70) to also show the whole phrase as one small, plain line
    (for viewers who read): it changes with each phrase."""
    w = w or c.w - 2 * x
    h = h or c.h - 2 * y
    keys = {k.lower() for k in keys}
    nbig = 0
    for gi, group in enumerate(groups):
        t_in = group[0][1]
        t_out = groups[gi + 1][0][1] if gi + 1 < len(groups) else (end if end is not None else None)
        t_next = t_out                                  # the subtitle changes here, held key words or not
        if t_out is not None and gi not in hide:
            last_key = max((t0 for wd, t0, _ in group if _bare(wd) in keys), default=None)
            if last_key is not None:
                t_out = max(t_out, max(0.0, last_key - 0.06) + focus + hold)
        if gi in hide:
            lines, block_w = [], 0
        else:
            lines, block_w = _lines(group, keys, small, big, font_small, font_big, w, fonts)
        # line heights: a large line takes about its cap height, a small one its size
        gaps = [ln["size"] * (big_cap + 0.28 if ln["big"] else 1.2) for ln in lines]
        block_h = sum(gaps)
        side, frac = spots[gi % len(spots)]
        bx = {"left": x, "right": x + w - block_w, "center": x + (w - block_w) / 2}[side]
        by = y + min(max(frac * h - block_h / 2, 0), h - block_h)
        base = by
        for ln, g in zip(lines, gaps):
            base += g
            rot = 0
            if ln["big"]:
                rot = tilt[nbig % len(tilt)] if tilt else 0
                nbig += 1
            for (word, t0, t1), dx, ww in ln["words"]:
                into_behind = behind is not None and ln["big"]
                lay = _word(behind if into_behind else c, word, t0, t_out, x=bx + ln["x"] + dx, base=base - (ln["size"] * 0.08 if ln["big"] else 0),
                      width=ww, size=ln["size"], font=ln["font"], color=accent if ln["big"] else color,
                      rot=rot, big=ln["big"], focus=focus, ghost=ghost, cap_share=big_cap if ln["big"] else 0.72)
                if into_behind:
                    lay["cl"] = "behind"                # kit.check: the subject hides part of it
        if subtitle:
            text = " ".join(wd for wd, _, _ in group)
            op = t_next - 0.05 if t_next is not None else c.duration   # the next line starts here
            sfont, ssize, ip = subtitle.get("font", font_small), subtitle.get("size", 40), max(0, t_in - 0.05)
            if subtitle.get("panel"):                   # a soft pill behind the line, for a busy picture
                tw = _width(text, sfont, ssize, 0, fonts)
                px, py = ssize * 0.6, ssize * 0.35
                c.rect(c.w / 2 - tw / 2 - px, subtitle["y"] - ssize * 0.78 - py, tw + 2 * px, ssize * 1.05 + 2 * py,
                       subtitle["panel"], radius=ssize, ip=ip, op=op, opacity=subtitle.get("panel_opacity", 70),
                       name="subtitle panel")
            c.text(text, font=sfont, size=ssize, x=c.w / 2, y=subtitle["y"], color=subtitle.get("color", color),
                   align="center", ip=ip, op=op, name="subtitle")


def _word(c: Comp, word, t0, t_out, *, x, base, width, size, font, color, rot, big, focus, ghost, cap_share=0.72):
    """One word: it comes into focus at *t0*; at *t_out* it blurs back, stays faint, then goes."""
    c._font(font)
    start = max(0.0, t0 - 0.06)
    cap = size * cap_share                              # about the cap height
    ax, ay = width / 2, -cap / 2                        # turn and scale about the middle of the word
    s0 = 118 if big else 108
    op_keys = [(start, 0), (start + 0.16, 100)]
    blur_keys = [(start, 26 if big else 16), (start + focus, 0)]
    end = c.duration
    if t_out is not None:
        t_out = max(t_out, start + focus + 0.02)        # keys must stay in order when phrases come fast
        op_keys += [(t_out, 100), (t_out + 0.35, 22), (t_out + ghost, 22), (t_out + ghost + 0.4, 0)]
        blur_keys += [(t_out, 0), (t_out + 0.35, 22)]
        end = min(c.duration, t_out + ghost + 0.4)
    ks = c._transform(x + ax, base + ay, anchor=(ax, ay), opacity=c.keys(*op_keys),
                      scale=c.keys((start, [s0, s0, 100]), (start + focus + 0.1, [100, 100, 100]), ease=EASE_OUT),
                      rot=static(rot))
    doc = {"s": size, "f": font, "t": word, "j": 0, "tr": 0, "lh": size * 1.2, "ls": 0, "fc": _rgb(color)}
    layer = c._layer(5, word, start, end, ks, t={"d": {"k": [{"t": 0, "s": doc}]}, "p": {},
                                                 "m": {"g": 1, "a": static([0, 0])}, "a": []})
    c.blur(layer, c.keys(*blur_keys, ease=EASE_OUT))
    return layer


def _rgb(hexcolor):
    from .lottie import rgb
    return rgb(hexcolor)


# ---------- a ring of text in 3D ----------
def ring(c: Comp, text, *, cx, cy, radius, t0, t1, back=None, front=None, turns=0.5, start=0.0, tilt=14,
         font="Inter-Bold", size=64, color="#E8743B", back_opacity=40, tracking=0.08,
         fonts=Path(__file__).resolve().parent.parent / "fonts", fade=0.4, step=1):
    """*text* on a circle of *radius* px that turns about a vertical axis through (cx, cy), seen from
    a little above (*tilt* degrees): the front of the ring passes low and large, the back high,
    small, dim and mirrored, as a real ring of letters would.

    Each letter is drawn twice: into *back* (behind the subject) and into *front* (in front of it),
    and only the copy on the right side of the ring is visible at any moment. Pass the layer group
    that sits under the subject as *back* and the one above it as *front*: the subject then hides
    the back of the ring. Both default to *c*.
    turns: how far the ring turns between t0 and t1 (1 = once round). start: the turn at t0.
    step: bake a key every *step* frames (2 halves the scene size; motion stays smooth).
    fade: seconds to fade in before t0 and to fade out before t1."""
    import math
    back, front = back or c, front or c
    for comp in {id(back): back, id(front): front}.values():
        comp._font(font)
    # spread the letters by their real widths along the circumference
    widths = [_width(ch, font, size, 0, fonts) + size * tracking for ch in text]
    total = sum(widths)
    circ = 2 * math.pi * radius
    if total > circ:
        raise ValueError(f"text is {total:.0f} px, the ring only {circ:.0f} px: shorten it or raise radius")
    phi = math.radians(tilt)
    F = radius * 4.5                                    # the camera's distance: the strength of the perspective
    frames = list(range(int(c.f(max(0, t0 - fade))), int(c.f(t1)) + 1, step))
    acc = 0.0
    for ch, w in zip(text, widths):
        mid = (acc + w / 2) / circ * 2 * math.pi       # the letter's angle on the ring
        acc += w
        if ch == " ":
            continue
        keys = {"p": [], "s": [], "fo": [], "bo": []}
        for fr in frames:
            t = fr / c.fps
            k = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
            a = mid + 2 * math.pi * (start + turns * k)
            z = math.cos(a) * radius                    # + toward the viewer
            p = F / (F - z * math.cos(phi))
            x = cx + math.sin(a) * radius * p
            y = cy + z * math.sin(phi) * p
            sx = math.cos(a) * p * 100                  # foreshortened; below zero on the back: mirrored
            fade_in = min(1.0, max(0.0, (t - (t0 - fade)) / fade), max(0.0, (t1 - t) / fade)) if fade else 1.0
            on_front = z >= 0
            depth = (z / radius + 1) / 2                # 0 at the back, 1 at the front
            o = (back_opacity + (100 - back_opacity) * depth) * fade_in
            keys["p"].append((t, [x, y, 0]))
            keys["s"].append((t, [sx, p * 100, 100]))
            keys["fo"].append((t, o if on_front else 0))
            keys["bo"].append((t, 0 if on_front else o))
        for comp, ok in ((back, "bo"), (front, "fo")):
            _ring_letter(comp, ch, w - size * tracking, size, font, color, keys["p"], keys["s"], keys[ok],
                         ip=frames[0] / c.fps, op=t1)


def _ring_letter(c: Comp, ch, w, size, font, color, pos, scale, opacity, *, ip, op):
    def baked(pairs):
        out = []
        for n, (t, v) in enumerate(pairs):
            k = {"t": c.f(t), "s": v if isinstance(v, list) else [v]}
            if n < len(pairs) - 1:
                k.update(LINEAR)
            out.append(k)
        return {"a": 1, "k": out}
    cap = size * 0.72
    ks = c._transform(0, 0, anchor=(w / 2, -cap / 2), opacity=baked(opacity), pos=baked(pos), scale=baked(scale))
    doc = {"s": size, "f": font, "t": ch, "j": 0, "tr": 0, "lh": size * 1.2, "ls": 0, "fc": _rgb(color)}
    return c._layer(5, f"ring {ch}", ip, op, ks, t={"d": {"k": [{"t": 0, "s": doc}]}, "p": {},
                                                    "m": {"g": 1, "a": static([0, 0])}, "a": []})
