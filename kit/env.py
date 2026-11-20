"""API keys for the kit: from the environment, else from `.env` at the repo root (git-ignored).

    GOOGLE_API_KEY=...          # kit/voice.py (Gemini TTS)
    REPLICATE_API_TOKEN=...     # kit/music.py --replicate, generated clips and images
"""
from __future__ import annotations

import os
from pathlib import Path

ENV = Path(__file__).resolve().parent.parent / ".env"
ALIASES = {"REPLICATE_API_TOKEN": ("REPLICATE_API_KEY",), "GOOGLE_API_KEY": ("GEMINI_API_KEY",)}


def secret(name: str) -> str:
    names = (name, *ALIASES.get(name, ()))
    for n in names:
        if os.environ.get(n):
            return os.environ[n]
    if ENV.exists():
        found = {}
        for line in ENV.read_text().splitlines():
            key, _, value = line.partition("=")
            if value.strip():
                found[key.strip()] = value.strip().strip("'\"")
        for n in names:
            if n in found:
                return found[n]
    raise SystemExit(f"{name} is not set: add it to the environment or to {ENV}")
