"""Run a model on Replicate and save what it makes: generated stills, clips and talking heads.

    from kit.replicate import run, upload
    run("black-forest-labs/flux-1.1-pro", {"prompt": "...", "aspect_ratio": "4:5"}, "media/portrait.jpg")
    run("bytedance/omni-human-1.5", {"image": upload("media/portrait.jpg"), "audio": upload("media/voice.flac")},
        "media/talk.mp4")

Billed per run to the account of REPLICATE_API_TOKEN (kit/env.py). A talking head made from one
still and the voice file (OmniHuman) has lips that follow the real words; a clip generated from a
prompt and voiced afterwards does not.
"""
from __future__ import annotations

import json
import mimetypes
import sys
import time
import urllib.request
import uuid
from pathlib import Path

from .env import secret

API = "https://api.replicate.com/v1"


def _headers(extra=None):
    # the default urllib agent gets a 403 from Replicate
    return {"Authorization": f"Bearer {secret('REPLICATE_API_TOKEN')}", "User-Agent": "kestrel-studio-kit",
            **(extra or {})}


def upload(path) -> str:
    """Upload a local file to Replicate's file store; returns a URL a model input accepts."""
    path = Path(path)
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"content\"; filename=\"{path.name}\"\r\n"
            f"Content-Type: {ctype}\r\n\r\n").encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"{API}/files", data=body,
                                 headers=_headers({"Content-Type": f"multipart/form-data; boundary={boundary}"}))
    return json.loads(urllib.request.urlopen(req, timeout=300).read())["urls"]["get"]


def run(model: str, inputs: dict, out, *, every=5.0, force=False) -> Path:
    """Start *model* (owner/name) with *inputs*, wait for it, and save the first output to *out*.

    Each call is a billed job. When *out* already exists, return it and do not start a job,
    unless *force* is true."""
    out = Path(out)
    if out.exists() and not force:
        print(f"{model}: {out} exists, no new run (force=True to pay for a new one)", file=sys.stderr)
        return out
    req = urllib.request.Request(f"{API}/models/{model}/predictions", data=json.dumps({"input": inputs}).encode(),
                                 headers=_headers({"Content-Type": "application/json"}))
    p = json.loads(urllib.request.urlopen(req, timeout=120).read())
    t0 = time.time()
    print(f"{model}: {p['id']} {p['status']}", file=sys.stderr, flush=True)
    while p["status"] not in ("succeeded", "failed", "canceled"):
        time.sleep(every)
        p = json.loads(urllib.request.urlopen(urllib.request.Request(p["urls"]["get"], headers=_headers()),
                                              timeout=120).read())
    print(f"{model}: {p['status']} in {time.time() - t0:.0f} s", file=sys.stderr, flush=True)
    if p["status"] != "succeeded":
        raise SystemExit(f"{model} {p['status']}: {p.get('error')}")
    url = p["output"] if isinstance(p["output"], str) else p["output"][0]
    out.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "kestrel-studio-kit"})) as r:
        out.write_bytes(r.read())
    return out
