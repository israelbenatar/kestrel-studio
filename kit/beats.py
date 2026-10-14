"""Beat grid and sync check for a music track (numpy + ffmpeg, no other dependencies).

    python -m kit.beats music.flac                      # tempo, first beat, strongest hits
    python -m kit.beats music.flac --bpm 120            # you set the tempo: find only the phase
    python -m kit.beats out/final.mp4 --check 0.5,2.5   # how far each landing is from a beat

Onsets come from spectral flux on a 100 Hz frame grid. Tempo detectors flip between half and double
time, so the 0.5x, 1x and 2x candidates are scored by how much onset energy lands on whole beats
and the winner is kept. When the music was generated at a known BPM, pass `--bpm` and only the
phase (where beat one falls) is measured.
"""
from __future__ import annotations

import argparse
import subprocess

import numpy as np

SR, HOP = 22050, 220          # ~100 onset frames per second
FPS_ENV = SR / HOP


def load(path: str) -> np.ndarray:
    """Mono float32 samples at SR, decoded by ffmpeg (any audio or video file)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def onset_envelope(x: np.ndarray) -> np.ndarray:
    n = 1024
    frames = np.lib.stride_tricks.sliding_window_view(np.pad(x, (n // 2, n // 2)), n)[::HOP]
    mag = np.log1p(100 * np.abs(np.fft.rfft(frames * np.hanning(n), axis=1)))
    flux = np.maximum(np.diff(mag, axis=0, prepend=mag[:1]), 0).sum(axis=1)
    flux -= np.convolve(flux, np.ones(31) / 31, mode="same")    # remove the slow loudness trend
    return np.maximum(flux, 0) / (flux.max() + 1e-9)


def _on(env: np.ndarray, off: float, period: float) -> float:
    idx = np.round(np.arange(off, len(env) / FPS_ENV, period) * FPS_ENV).astype(int)
    idx = idx[idx < len(env)]
    # take the max of +-1 frame so a beat isn't missed by rounding
    return float(np.mean([env[max(i - 1, 0):i + 2].max() for i in idx])) if len(idx) else 0.0


def _phase(env: np.ndarray, period: float) -> tuple[float, float]:
    """Best offset (s) of a beat grid with this period, and its contrast: onset energy on the beats
    minus energy halfway between them. Half tempo puts real beats on its midpoints, so it scores
    low; double tempo has empty beats, so it scores lower than the true tempo."""
    best = (0.0, -1.0)
    for off in np.arange(0, period, 1 / FPS_ENV):
        score = _on(env, off, period) - _on(env, off + period / 2, period)
        if score > best[1]:
            best = (float(off), score)
    return best


def grid(path: str, bpm: float | None = None) -> dict:
    env = onset_envelope(load(path))
    if bpm is None:
        lags = np.arange(int(FPS_ENV * 60 / 200), int(FPS_ENV * 60 / 60))   # 60..200 BPM
        ac = np.array([np.dot(env[:-l], env[l:]) for l in lags])
        base = 60 * FPS_ENV / lags[int(np.argmax(ac))]
        cands = [b for b in (base / 2, base, base * 2) if 60 <= b <= 200]
        bpm = max(cands, key=lambda b: _phase(env, 60 / b)[1])
    period = 60 / bpm
    first, _ = _phase(env, period)
    peaks = [i for i in range(1, len(env) - 1) if env[i] >= env[i - 1] and env[i] > env[i + 1]]
    strongest = sorted(sorted(peaks, key=lambda i: -env[i])[:5])
    return {"bpm": round(float(bpm), 2), "beat": round(float(period), 4), "first_beat": round(first, 3),
            "duration": round(len(env) / FPS_ENV, 2),
            "strongest": [round(i / FPS_ENV, 2) for i in strongest]}


def beats(g: dict) -> list[float]:
    return [round(float(g["first_beat"] + k * g["beat"]), 3)
            for k in range(int((g["duration"] - g["first_beat"]) / g["beat"]) + 1)]


def check(path: str, landings: list[float], fps: float = 30, bpm: float | None = None) -> list[tuple]:
    """Distance of each landing from the nearest detected beat, in video frames (pass: < 3)."""
    bs = np.array(beats(grid(path, bpm)))
    return [(t, round(float(np.min(np.abs(bs - t))) * fps, 1)) for t in landings]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--check", help="comma-separated landing times (s)")
    ap.add_argument("--fps", type=float, default=30)
    a = ap.parse_args()
    if a.check:
        for t, off in check(a.audio, [float(v) for v in a.check.split(",")], a.fps, a.bpm):
            print(f"{t:7.2f}s  {off:4.1f} frames off  {'ok' if off < 3 else 'MISS'}")
    else:
        g = grid(a.audio, a.bpm)
        print(g)
        print("beats:", beats(g)[:16], "...")
