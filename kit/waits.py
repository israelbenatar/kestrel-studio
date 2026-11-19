"""Play the waits in a screen capture fast instead of cutting them (numpy + ffmpeg).

    python -m kit.waits capture.webm                         # how much the picture changes, second by second
    python -m kit.waits capture.webm --wait 13.6:33.6 --wait 40:105 --keep 10:38 -o clip.mp4

When the screen shows work in progress (a progress bar, text streaming in, a page filling in),
playing it fast keeps the sense that time passed and shows the result arriving; a cut makes it look
instant. The rules:
- A wait plays in about 2 to 5 seconds on screen whatever its length, so a long render plays much
  faster than a short install (*on_screen()*).
- Still stretches inside a wait (only a spinner or a caret) play fast with the rest when short
  and are cut when long; a flash of movement between two cuts is cut too.
- The wait ends where the result appears, so the result plays at 1x. Typing stays at 1x.
- The sound of a sped-up stretch is muted: the rendered clip has no audio at all. Lay music and
  foley in the build, on the beat grid.

The waits come from the capture script (kit/capture.cjs marks: typed -> reply, started -> done),
which knows when they start and end; this module measures what happens inside them. *remap()*
turns recording seconds into clip seconds, for kit.camera and for timing beats to the clip.
"""
from __future__ import annotations

import argparse
import math
import subprocess

import numpy as np

SMALL = 0.006            # share of the picture's 32 px cells: changes smaller than this (a spinner, a caret,
                         # the pointer) are "nothing"; a line of new text is several times more
CELL = 32


def motion(path: str, *, rate: float = 4) -> tuple[np.ndarray, np.ndarray]:
    """(times, change): *rate* times a second, the share of the picture's 32 px cells that differ from
    one second earlier. A one-second lag lets text that streams in a word at a time add up, and
    counting cells rather than pixels lets a line of thin text weigh what it covers."""
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height", "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    w, h = (int(v) for v in probe.stdout.strip().split(",")[:2])
    sw, sh = max(4, w // 8), max(4, h // 8)           # each pixel: the mean of an 8 x 8 block
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={rate},scale={sw}:{sh}:flags=area,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, sh, sw).astype(np.int16)
    lag = max(1, int(round(rate)))
    k = CELL // 8
    ch, cw = sh // k, sw // k
    changed = np.abs(frames[lag:] - frames[:-lag])[:, :ch * k, :cw * k] > 12
    cells = changed.reshape(len(changed), ch, k, cw, k).any(axis=(2, 4))
    change = np.concatenate([np.zeros(lag), cells.mean(axis=(1, 2))])
    times = np.arange(len(change)) / rate
    return times, change


def on_screen(length: float) -> float:
    """Seconds a wait of *length* seconds plays for: 2 s for a 5 s wait, rising to 5 s at 10 min."""
    if length <= 2:
        return length
    u = (math.log10(length) - math.log10(5)) / (math.log10(600) - math.log10(5))
    return round(min(5.0, max(2.0, 2 + 3 * u)), 2)


def plan(path: str, waits, *, keep=None, max_gap: float = 8.0, min_move: float = 1.0, min_shown: float = 0.5,
         rate: float = 4) -> list[tuple]:
    """Pieces (t0, t1, speed) of the recording that make the clip, in order; what is left out is cut.

    *waits*: (t0, t1) recording seconds of each wait, ending where its result appears.
    *keep*: (t0, t1) of the recording to use at all (default: all of it).
    Inside a wait, the stretches where the picture changes are sped up together to play in
    on_screen() seconds. Still gaps shorter than *max_gap* s between them play fast with them (time
    is seen to pass); longer ones are cut. A stretch that moves for less than *min_move* s, or would
    be on screen less than *min_shown* s, is cut too: a flash between two cuts reads as a glitch."""
    times, change = motion(path, rate=rate)
    k0, k1 = keep if keep else (0.0, float(times[-1]) if len(times) else 0.0)
    pieces: list[tuple] = []
    cur = k0
    for w0, w1 in sorted(waits):
        w0, w1 = max(w0, k0), min(w1, k1)
        if w1 <= w0:
            continue
        if w0 > cur:
            pieces.append((cur, w0, 1.0))
        # runs of change inside the wait; a change at t was measured against t - 1 s
        runs: list[list[float]] = []
        for t, ch in zip(times, change):
            if w0 < t <= w1 and ch >= SMALL:
                if runs and t - runs[-1][1] <= max_gap:
                    runs[-1][1] = t
                else:
                    runs.append([max(w0, t - 1.0), t])
        spans = [(a, b) for a, b in runs if b - a >= min_move]
        while spans:
            length = sum(b - a for a, b in spans)
            speed = max(1.0, length / on_screen(length))
            short = [sp for sp in spans if (sp[1] - sp[0]) / speed < min_shown]
            if not short or len(spans) == 1:
                break
            spans.remove(min(short, key=lambda sp: sp[1] - sp[0]))
        if spans:
            pieces += [(round(a, 3), round(b, 3), round(speed, 3)) for a, b in spans]
        cur = w1
    if k1 > cur:
        pieces.append((cur, k1, 1.0))
    return pieces


def remap(pieces, t: float) -> float:
    """Clip seconds for recording second *t*; a time inside a cut lands where the cut is."""
    out = 0.0
    for a, b, s in pieces:
        if t < a:
            return out
        if t <= b:
            return out + (t - a) / s
        out += (b - a) / s
    return out


def length(pieces) -> float:
    return sum((b - a) / s for a, b, s in pieces)


def render(path: str, pieces, out: str, *, fps: int = 30, crop=None, size=None, crf: int = 16) -> str:
    """Write the clip: every piece at its speed, joined, optionally cropped (x0, y0, x1, y1) and
    scaled (w, h). Silent: a sped-up wait's sound only distracts."""
    inputs, parts = [], []
    post = ""
    if crop:
        x0, y0, x1, y1 = crop
        post += f",crop={x1 - x0}:{y1 - y0}:{x0}:{y0}"
    if size:
        post += f",scale={size[0]}:{size[1]}:flags=lanczos,setsar=1"
    for k, (a, b, s) in enumerate(pieces):
        inputs += ["-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", path]
        parts.append(f"[{k}:v]setpts=(PTS-STARTPTS)/{s},fps={fps}{post}[p{k}]")
    graph = ";".join(parts) + ";" + "".join(f"[p{k}]" for k in range(len(pieces))) + \
        f"concat=n={len(pieces)}:v=1:a=0[v]"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[v]", "-an",
                    "-c:v", "libx264", "-crf", str(crf), "-pix_fmt", "yuv420p", out], check=True)
    return out


def _span(v: str) -> tuple[float, float]:
    a, b = v.split(":")
    return float(a), float(b)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("--wait", action="append", type=_span, default=[], help="t0:t1 of a wait (repeat)")
    ap.add_argument("--keep", type=_span, help="t0:t1 of the recording to use")
    ap.add_argument("-o", "--out", help="render the clip here")
    ap.add_argument("--fps", type=int, default=30)
    a = ap.parse_args()
    if not a.wait:
        times, change = motion(a.video, rate=1)
        for t, ch in zip(times, change):
            bar = "#" * min(60, int(ch * 600))
            print(f"{t:7.1f}s  {ch:6.3f}  {'.' if ch < SMALL else bar}")
    else:
        p = plan(a.video, a.wait, keep=a.keep)
        for t0, t1, s in p:
            print(f"{t0:8.2f} - {t1:8.2f}  x{s:<7}  -> {(t1 - t0) / s:5.2f}s on screen")
        print(f"clip: {length(p):.2f}s")
        if a.out:
            render(a.video, p, a.out, fps=a.fps)
            print("wrote", a.out)
