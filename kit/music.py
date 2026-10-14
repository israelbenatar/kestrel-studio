"""Generate a music track from a prompt with ACE-Step 1.5 (standard library only), either on your
own machine or on Replicate.

Local (free; ~6 GB of GPU memory; Apple Silicon works). Start the server once, in the
ACE-Step-1.5 checkout (models download on the first request):

    ACESTEP_INIT_LLM=false uv run acestep-api --port 8001     # macOS: also ACESTEP_LM_BACKEND=mlx

ACESTEP_INIT_LLM=false skips the planning language model; we always give the BPM and key, so it
isn't needed. The first request downloads ~6 GB of weights.

Replicate (no GPU needed; billed per run to your Replicate account): set REPLICATE_API_TOKEN and
add `--replicate`. It runs the community-hosted `fishaudio/ace-step-1.5`, pinned to one version so
a seed gives the same track next month.

Then:

    python -m kit.music "calm felt piano intro, builds into warm indie-pop with claps" \
        --bpm 120 --key "D Major" --duration 10 --seeds 7,8,9 -o media/

Set the BPM yourself: the beat grid is then known before the track exists (beat = 60 / BPM s), so
cuts can be planned against it. Each seed is one candidate, saved as `music-<seed>.flac` with a
`.json` beside it recording the exact request, so the chosen track can be regenerated.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

SERVER = "http://127.0.0.1:8001"
REPLICATE_VERSION = "74e3a7d383b18815e277de5223f5fe9d53d38832de15aa567fe729fa129d0d85"   # fishaudio/ace-step-1.5


def _post(path: str, body: dict, server: str, headers: dict | None = None) -> dict:
    req = urllib.request.Request(server + path, json.dumps(body).encode(),
                                 {"Content-Type": "application/json", **(headers or {})})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            # Replicate rate-limits low-credit accounts to a few predictions a minute: wait it out
            if e.code != 429 or attempt == 5:
                raise
            time.sleep(float(e.headers.get("Retry-After") or 10 * (attempt + 1)))


def generate_replicate(prompt: str, *, bpm: int, duration: float, seed: int, out_dir: Path,
                       key: str = "", instrumental: bool = True, timeout: float = 900) -> Path:
    """The same candidate, generated on Replicate. Needs REPLICATE_API_TOKEN."""
    token = os.environ["REPLICATE_API_TOKEN"]
    auth = {"Authorization": f"Bearer {token}"}
    inputs = {"prompt": prompt, "bpm": bpm, "key_scale": key, "time_signature": "4",
              "duration": duration, "seed": seed, "batch_size": 1, "audio_format": "flac",
              "thinking": False}
    if instrumental:
        inputs["lyrics"] = "[Instrumental]"
    pred = _post("/v1/predictions", {"version": REPLICATE_VERSION, "input": inputs},
                 "https://api.replicate.com", auth)
    t0 = time.time()
    while pred["status"] not in ("succeeded", "failed", "canceled"):
        if time.time() - t0 > timeout:
            raise TimeoutError(f"Replicate prediction {pred['id']} still {pred['status']}")
        time.sleep(2)
        with urllib.request.urlopen(urllib.request.Request(pred["urls"]["get"], headers=auth)) as r:
            pred = json.load(r)
    if pred["status"] != "succeeded":
        raise RuntimeError(f"Replicate {pred['status']}: {pred.get('error')}")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"music-{seed}.flac"
    url = pred["output"][0] if isinstance(pred["output"], list) else pred["output"]
    with urllib.request.urlopen(url) as r:
        out.write_bytes(r.read())
    meta = {"backend": "replicate", "version": REPLICATE_VERSION, "input": inputs,
            "seconds": round(time.time() - t0, 1), "metrics": pred.get("metrics")}
    out.with_suffix(".json").write_text(json.dumps(meta, indent=1))
    return out


def generate(prompt: str, *, bpm: int, duration: float, seed: int, out_dir: Path, key: str = "",
             instrumental: bool = True, server: str = SERVER, timeout: float = 1800) -> Path:
    """One candidate for one seed. Blocks until the file is written; returns its path."""
    request = {"prompt": prompt, "instrumental": instrumental, "bpm": bpm, "key_scale": key,
               "time_signature": "4", "audio_duration": duration, "use_random_seed": False,
               "seed": seed, "batch_size": 1, "audio_format": "flac", "thinking": False,
               "use_cot_caption": False}   # keep the prompt as written, and our BPM and key
    task = _post("/release_task", request, server)["data"]["task_id"]
    t0 = time.time()
    while True:
        item = _post("/query_result", {"task_id_list": [task]}, server)["data"][0]
        if item["status"] == 1:
            break
        if item["status"] == 2:
            raise RuntimeError(f"ACE-Step failed: {item.get('result')}")
        if time.time() - t0 > timeout:
            raise TimeoutError(f"ACE-Step task {task} still running after {timeout:.0f} s")
        time.sleep(2)
    result = json.loads(item["result"])[0]
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"music-{seed}.flac"
    with urllib.request.urlopen(server + result["file"]) as r:
        out.write_bytes(r.read())
    meta = {"backend": "local", "request": request, "metas": result.get("metas"), "dit_model": result.get("dit_model"),
            "seconds": round(time.time() - t0, 1)}
    out.with_suffix(".json").write_text(json.dumps(meta, indent=1))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ap.add_argument("--bpm", type=int, required=True)
    ap.add_argument("--key", default="")
    ap.add_argument("--duration", type=float, required=True, help="seconds (ACE-Step: 10-600)")
    ap.add_argument("--seeds", default="1,2,3", help="one candidate per seed")
    ap.add_argument("--vocals", action="store_true", help="allow vocals (default: instrumental)")
    ap.add_argument("-o", "--out", default="media")
    ap.add_argument("--server", default=SERVER, help="local ACE-Step API server")
    ap.add_argument("--replicate", action="store_true", help="run on Replicate instead")
    a = ap.parse_args()
    for s in (int(v) for v in a.seeds.split(",")):
        kw = dict(bpm=a.bpm, key=a.key, duration=max(a.duration, 10), seed=s, out_dir=Path(a.out),
                  instrumental=not a.vocals)
        print(generate_replicate(a.prompt, **kw) if a.replicate else generate(a.prompt, server=a.server, **kw))
