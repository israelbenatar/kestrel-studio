"""Voice-over with Gemini TTS: a line of text -> a FLAC file the renderer can mix.

    python -m kit.voice "Most captions just sit at the bottom." -o media/voice.flac --voice Kore \
        --style "warm, confident, a product demo"

The key is GOOGLE_API_KEY, from the environment or from a `.env` file at the repo root
(git-ignored). The output is FLAC at 48 kHz stereo: kestrel's --audio drops WAV without a word.

The request is the one the ai-tutor backend makes (Interactions endpoint, the delivery style as a
`speech_metadata` annotation), so the voices sound the same.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

from .env import secret

MODEL = os.environ.get("GEMINI_TTS_MODEL") or "gemini-3.8-flash-tts"
VOICES = {"male": "Charon", "female": "Kore"}
RATE = 24000                                    # fixed by the API: 16-bit mono PCM at 24 kHz
URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


def _key() -> str:
    return secret("GOOGLE_API_KEY")


def _pcm(audio: bytes) -> bytes:
    """The API wraps the samples in a WAV with a C2PA chunk after them: keep the samples only."""
    if audio[:4] != b"RIFF":
        return audio
    with wave.open(io.BytesIO(audio)) as w:
        return w.readframes(w.getnframes())


def speak(text: str, *, voice: str = "female", style: str = "", retries: int = 4) -> bytes:
    """One line of text -> 16-bit mono PCM at 24 kHz."""
    item: dict = {"type": "text", "text": text}
    if style:
        item["annotations"] = [{"type": "speech_metadata", "style": style}]
    body = json.dumps({
        "model": MODEL,
        "input": [{"type": "user_input", "content": [item]}],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": VOICES.get(voice, voice)}]},
    }).encode()
    key = _key()
    for attempt in range(retries + 1):
        req = urllib.request.Request(URL, data=body, headers={"x-goog-api-key": key,
                                                              "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                d = json.loads(resp.read())
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < retries:
                time.sleep(min(8.0, 2 ** attempt))
                continue
            raise SystemExit(f"gemini HTTP {e.code}: {e.read()[:300]!r}") from e
    audio = [c for step in d.get("steps") or [] if step.get("type") == "model_output"
             for c in step.get("content") or [] if c.get("type") == "audio"]
    if not audio:
        raise SystemExit(f"gemini returned no audio: {json.dumps(d)[:300]}")
    return _pcm(base64.b64decode(audio[-1]["data"]))


def save(pcm: bytes, out) -> Path:
    """PCM -> FLAC at 48 kHz stereo, with a short fade at each end against clicks."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        with wave.open(tmp.name, "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(RATE), w.writeframes(pcm)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp.name, "-af", "afade=t=in:d=0.02",
                        "-ar", "48000", "-ac", "2", str(out)], check=True)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("text")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--voice", default="female", help="female (Kore), male (Charon), or a Gemini voice name")
    ap.add_argument("--style", default="", help="how to say it, in plain words")
    a = ap.parse_args()
    pcm = speak(a.text, voice=a.voice, style=a.style)
    print(f"{save(pcm, a.out)}  {len(pcm) / (2 * RATE):.2f} s")


if __name__ == "__main__":
    main()
