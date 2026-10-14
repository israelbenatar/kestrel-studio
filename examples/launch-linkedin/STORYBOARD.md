---
title: kestrel studio — launch (LinkedIn)
format: 1080x1350        # 4:5, LinkedIn feed
fps: 30
length: 30 s + 3 s postroll (33 s)
music: ACE-Step 1.5, 120 BPM (beat 0.5 s, bar 2 s), D minor, instrumental, 34 s
narration: none (captions on screen; LinkedIn autoplays muted)
---

# Frame

- **Subject:** kestrel studio — an agent skill + renderer that turns a prompt into a finished
  marketing video. One message: *a launch video is now a prompt, not a week.*
- **Goal:** awareness + GitHub visits from builders and small teams.
- **Channel:** LinkedIn feed post, autoplay muted → every beat must read without sound; captions
  are the story. Music is the second layer.
- **Meta-proof:** the video demos the kestrel studio landing page and ends with "Made with kestrel
  studio" — the video is its own proof.
- **Look:** the landing page's glass language (dark aurora, frosted panels, hairline highlights),
  taken from `site/` via `brand/brand.json` — the video and the site match.

# State list (as built — re-timed to music-11: quiet 0–14, breath 14–15, riser, drop at 16.0)

| # | time | on screen | takeaway |
|---|---|---|---|
| 1 | 0.0–2.0 | "A launch video / used to take / a week." — lines on 0.5, 1.0, 1.5 | the pain |
| 2 | 2.0–4.0 | "a week." struck through on 2.0; "*a prompt.*" springs in on 2.5 | the promise |
| 3 | 4.0–8.0 | HyperFrames: glass terminal lands on 4.0, the prompt types at 1×, ⏎ on 8.0 | it starts from a sentence |
| 4 | 8.0–12.0 | HyperFrames: terminal lifts away, the real site unfolds from a 68° tilt, lands flat on 12.0 | the real site |
| 5 | 12.0–16.0 | kestrel takes over invisibly; the site's film plays in its stage. Chip ①; the site's palette pops as swatches (12.5–13.5); type specimen (14.0); → brand.json (15.0) | it looks like you |
| 6 | 16.0–19.0 | **Drop.** Chip ②; the real Sustain film, "Oldest to newest" building photo by photo | real product |
| 7 | 19.0–22.0 | Chip ③; the gold card (PAPER + GLINT shaders) lands; glint crosses on 21.0; this track's real waveform, beats lit, playhead | music on the beat |
| 8 | 22.0–25.5 | Chip ④; counter 0 → 240 (22.1–24.0); four aspects land on 24.0 / 24.25 / 24.5 / 24.75 | fast, every aspect |
| 9 | 25.5–30.0 | Finale: site + film gather in; "Marketing & social videos, / *written as code.*"; "An agent skill + a 120 fps renderer."; "Free for builders & teams up to 10"; URL | the message + CTA |
| 10 | 30.0–33.0 | Postroll v1 (`brand/postroll-4x5.mp4`), CTA slot: "Made with kestrel studio" | the signature |

Sync check (`kit/beats.py --check` on the finished file): every landing 0.6 frames off the beat.

# Engines

- **HyperFrames** (transparent ProRes 4444 overlays): the 3D site unfold (state 4), glass terminal and
  chips (real `backdrop-filter` over the site capture inside the same HTML), the finale orbit.
- **kestrel** (compositor): aurora background, captures, glint card (shader), counter, aspect
  frames, captions, music, finish pass (soft light leak on impacts, grain).

# Assets

- `site/` — the kestrel studio landing page (built first; the video's subject and its style source).
- `assets/captures/` — Playwright: hero still (2x), full-page still, 3 s scroll recording, hover.
- `media/music-<seed>.flac` — ACE-Step, 120 BPM, D minor, 34 s; 3 candidates.
- `brand/brand.json` — read from the site.

# Decisions

- Repo: github.com/israelbenatar/kestrel-studio. Format: 4:5 only for now.
- Music: music-11 (seed 11, ACE-Step 1.5 on Replicate, 120 BPM, D minor).
