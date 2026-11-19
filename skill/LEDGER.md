# Ledger: mistakes found, and what catches them now

Every mistake found in a video, by the user or by a review, gets a row here with the check that
catches it next time. Before delivery, run every check this ledger lists (§8 of the skill). A
mistake fixed once and not written down comes back.

How to add a row: say what the viewer saw, not what the code did; name the check. Prefer a check
in code (`kit/check.py`, `kit/beats.py`, a test of the kit) over a sentence in the skill: a
sentence asks the model to remember, a check doesn't. When no check is possible yet, write
`review` and the exact thing to look at in the stills.

| # | Found | What the viewer saw | Caught by | Status |
|---|---|---|---|---|
| 1 | 2026-10 | Hebrew text revealed from its last word to its first. | `Comp.text(reveal=)` reverses the selector for right-to-left text | fixed in the kit |
| 2 | 2026-10 | A layer with a shader vanished from the render, with no error. | `Comp.shader()` adds a ticking uniform; Skottie skips an effect whose uniforms never change | fixed in the kit |
| 3 | 2026-10 | A shader ignored a `float2` uniform. | `Comp.shader()` docstring: declare `float` or `float x[N]` only | review |
| 4 | 2026-11-19 | A review sheet showed the stills out of time order (`f12` before `f3`). | §8 step 1: number stills 1, 2, 3… and tile with `f%d.png`, not a glob | skill |
| 5 | 2026-11-19 | Chapter labels in `chat-sorting` (terracotta on cream, 26 px) measure 2.7:1 after the finish pass, 3.2:1 as designed. | `kit.check --video`: `contrast` | fixed: type uses a darker terracotta (`TERRA_TEXT`, 4.2:1), at 40 px |
| 6 | 2026-11-19 | `→ brand.json` in `launch-linkedin` sits 37 px above the bottom edge. | `kit.check`: `safe-area` | fixed: 40 px, and the swatch block moved up 40 px |
| 7 | 2026-11-19 | Body lines of 24–31 px in all three examples: hard to read on a phone. | `kit.check`: `text-height` (3% floor); mark true decoration `decor=True` | fixed: labels a viewer reads are 40 px; swatch hex codes and the card's small print are `decor=True` |
| 8 | 2026-11-19 | In the `kit-update` film, a cream-on-orange tag (2.6:1) and an amber ×12 on light glass over a white UI (1.4:1). | `kit.check --video`: `contrast` | fixed: dark text on the tag, a solid dark pill behind ×12 |

## Checks by id

| id | Where | What it measures |
|---|---|---|
| `text-height` | `kit/check.py` | readable text ≥ 3% of frame height; the main line of a beat 5% is a review call |
| `safe-area` | `kit/check.py` | text inside the frame's margins; on 9:16, clear of the platform's buttons and captions |
| `contrast` | `kit/check.py --video` | text ≥ 3:1 against the picture behind it, on the frame where it is fully in |
| `sync` | `kit/beats.py --check` | every landing within 3 frames of a beat |
| `seam` | `ffmpeg -lavfi psnr` | joined clips ~40 dB at the join |
