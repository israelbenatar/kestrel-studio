---
name: kestrel-video
description: Make motion videos as code — product promos, feature demos, explainers, social clips, site heroes — from storyboard to finished MP4. Takes its look from the product's own website, captures the real product (Playwright for web, Maestro for mobile), builds scenes with kestrel (Lottie → video, a fast native renderer) or HyperFrames (HTML), adds a film finish (light leak, glow, grain, vignette), syncs to music (generated with ACE-Step at a chosen tempo, or supplied), and reviews its own frames in a critique loop until they pass, and closes every marketing video with the brand's fixed postroll. Any aspect (9:16, 4:5, 1:1, 16:9) and any language. Use when asked to make, refresh, or improve a video, an ad, a reel, a promo, an animated explainer, or a hero clip.
---

# kestrel-video

You are writing a **program** that draws every frame, not "generating a video". Every frame is a
pure function of time, so a re-render is identical and a fix is an edit, not a reroll. The prompt
is the small part; the harness around it — references, a state list, real media, a render you can
look at, and a review loop — is what makes the video good.

Repo layout this skill assumes (`$KIT` = the repo root):

| Path | What |
|---|---|
| `kit/lottie.py` | Lottie scene builder for kestrel: text (reveal, typewriter), images, clips, shapes, fades, rises, springs, slow zooms. Seconds and pixels. |
| `kit/finish.py` | Film finish post-pass: grade, glow, light leak (swells on cuts), grain, vignette. |
| `kit/shaders.py` | Ready-made SkSL layer shaders for `Comp.shader()`: `GLINT` (a sweep of light), `PAPER` (fibre texture), `LIGHTS` (stage lights: darkness, moving spotlights, a rim from the layer's alpha). |
| `kit/music.py` | Music from a prompt with ACE-Step 1.5, locally or on Replicate, at a BPM and key you choose (§6). |
| `kit/beats.py` | Beat grid of a track (tempo, beat one, strongest hits) and the post-render sync check (§6). |
| `kestrel` | The renderer binary (Lottie/Bodymovin → MP4 / ProRes / PNG). |
| `fonts/` | Open-licensed fonts, referenced by file stem. |
| `examples/` | Worked scenes. Clone the closest one instead of starting blank. |

## 1. Frame the video (before anything else)

Decide, or ask: **subject** (one message), **goal** (signup, awareness, retention), **channel**
(feed, Reels/Stories, YouTube, site hero, in-app), **aspect**, **length** (15–60 s), **language(s)**,
**narration or music-only**. Plan **every aspect from one timeline** from the start: lay scenes out
with a layout function per aspect and render each, never crop a 16:9 render into 9:16.

**Match the product's own design.** If the product has a website or app, the video should look
like it. Before designing anything, take the design from the live site rather than guessing:
open it with Playwright and read the computed styles of the body, headings, buttons and links
(`getComputedStyle`: colours, font families and weights, radii, shadows, spacing), the CSS custom
properties on `:root` (most design systems keep their tokens there), the logo (SVG from the header,
or the favicon / `og:image`), and full-page screenshots at phone and desktop width as references.
Write it to `brand/brand.json` (palette with roles — background, ink, accent; type pairs; radii;
logo path) and show it to the user to confirm. Both engines then read from it: kestrel scenes take
colours and fonts from it; HyperFrames frames get the same values as CSS variables. If the site's
fonts aren't open-licensed, ask for the files or pick the closest open font and say so. A video
that lives *on* the site (a hero, a feature section) should also be checked in place: drop the
render into a screenshot of the page and look at it at real size before calling it done.

Collect **references**, not adjectives. A named look plus one frame or clip beats any description
of a vibe; with no reference you get centred text on a gradient where everything fades in.

## 2. Write the state list (the storyboard)

A beat-by-beat list of **states**, each with a time, what is on screen, what moves, and what the
viewer should take away. Prefer one element changing between states over cuts between unrelated
cards. A promo usually follows a four-part **energy arc**:

1. **Quiet open** — the brand or the problem, calm.
2. **One hero moment** with a full motion arc (enter, act, settle).
3. **Feature climb** — short beats, each introduced by a small title card, energy rising.
4. **Finale at peak energy** — elements from earlier shots gather around the wordmark/CTA. Don't
   end quietly after a climb.

Keep big, frame-wide impacts rare (≤3 per film) and put them on the music's strongest hits (§6).
Write the state list to `STORYBOARD.md` and get it approved before building frames.

## 3. Show the real thing

Truthful screens sell; mocked UI reads as fake. Use real data and real photos, and cut waiting
rather than faking speed (speed a recording up 8–10× through a spinner, keep typing at 1×).

**Capture the product with a script, not by hand**, so a capture can be re-taken after a UI change
and comes out identical:
- **Web apps — [Playwright](https://playwright.dev)**: a fixed viewport and `deviceScaleFactor: 2`,
  `recordVideo` for flows, `page.screenshot({clip})` for stills, a seeded demo account and fixed
  data so names and dates don't change between takes. Hide what isn't the product (cookie banners,
  dev toolbars) with injected CSS; slow `type()` with a delay so typing reads on screen.
- **Mobile apps — [Maestro](https://maestro.mobile.dev)**: a YAML flow that taps through the
  feature on a simulator or emulator, with `startRecording`/`stopRecording` around the beat and
  `takeScreenshot` for stills. Set the status bar to a clean time and full battery first
  (`xcrun simctl status_bar booted override --time 9:41 --batteryLevel 100`).
- Save every capture into the project as an asset — `assets/captures/<beat>-<what>.webm|png` —
  next to the capture script that made it (`capture/`), and name each after the storyboard beat it
  serves. The build reads captures from there; nothing is pulled from a browser by hand.
- Crop each capture to the panel that matters before it goes into a layer, and record at least the
  output's pixel size so nothing is upscaled.
Anything AI-generated (people, scenes) must be fit for the claim it sits under — a photo captioned
"Paris" must show Paris.

## 4. Pick the engine

| | kestrel (`kit/lottie.py`) | HyperFrames (HTML) |
|---|---|---|
| Best for | photo/clip-heavy scenes, text animation, long or many renders, batch variants | complex layout, CSS-native UI, web-font-heavy design |
| Speed | ~170–270 fps at 1080×1350 on a laptop (a 60 s film in ~10 s) | headless browser screenshots, minutes |
| Motion | keyframes, springs, per-character text animators, expressions | GSAP timelines |
| Output | MP4, WebM (VP9, alpha), transparent ProRes, PNG/WebP | MP4, WebM, transparent MOV (ProRes 4444), PNG sequence |

**Combine them — kestrel as the compositor.** Give each beat to the engine that does it best:
HyperFrames for what CSS does natively (real 3D perspective, `filter: blur` depth of field,
`backdrop-filter` glass, gradient-clipped type, complex flex layout); kestrel for photo- and
clip-heavy beats, text animators, and the long timeline. Render each HyperFrames beat to its own
MP4 (`hyperframes render <dir> -o beat.mp4 --quality delivery`), place it in the kestrel scene as a
full-frame clip on its slot (`c.video('beat.mp4', 0, 0, W, H, start=t0, ip=t0, op=t1)`), and run
the finish over the whole film so both engines share one grade, grain and light.
- Match canvas size, fps and background colour across both engines so the hand-off is invisible.
- **Overlays with real transparency.** Render the HTML layer with a transparent page
  (`html, body, #root { background: transparent }`) as `--format mov` (ProRes 4444) and place it
  above kestrel layers: e.g. kestrel keeps photos drifting underneath while HyperFrames lays type,
  a soft panel and glass chips on top. kestrel keeps the alpha of ProRes 4444, PNG/Animation and
  VP8/VP9 WebM clips, and can write transparent WebM itself. `backdrop-filter` in the HTML only blurs other HTML, not the kestrel layers
  below — put a soft panel behind text instead.
- Opaque full-frame beats (`.mp4`) hand off on a cut or a cross-fade.
- The other direction works too: a kestrel render is just an MP4 for a HyperFrames frame
  (host-root `<video>`, §5b).

## 5a. Building with kestrel

```python
from kit.lottie import Comp
c = Comp(1080, 1350, fps=30, duration=12)
c.solid('#F5F0E8')
c.text('One idea.', font='EBGaramond-Regular', size=92, x=540, y=520, align='center',
       color='#2D3436', reveal=(0.2, 1.0))                      # characters rise in, reading order
c.text(prompt, font='EBGaramond-Italic', size=40, x=60, y=140, typewriter=(1.0, 2.4))
c.video('media/chat.mp4', 90, 300, 900, 682, start=1.0, radius=24, fade=(1.1, 1.6), rise=40)
c.image('media/a-480x276.jpg', 60, 200, 480, 276, radius=12, fade=(3.0, 3.5), rise=24,
        spring=True, zoom=((3.0, 8.0), (100, 104)))            # lands on a spring, slow push-in
c.circle(540, 1290, 14, '#B07A64', pop=4.0)                      # springs in from 85%
c.save('scene.json')
```
```sh
kestrel render scene.json --frame 240 -o check.png --fonts fonts      # one still, instant
kestrel render scene.json -o out/raw.mp4 --fonts fonts --audio music.mp3 --audio-volume 0.8 --fade-out 2
python -m kit.finish out/raw.mp4 out/final.mp4 --flash 2.6,13.9,18.4   # cut times
```

Rules learned the hard way:
- **Crop media to its slot first** (PIL/ffmpeg) — a layer shows its asset at the placed size. For
  a slow push-in, the zoom stays ≤105% so no edge shows.
- **Clip dimensions must be even** (x264 refuses odd heights) — round to a multiple of 2.
- **Hold a clip's last frame** with `tpad=stop_mode=clone:stop_duration=<s>` if the layer outlives
  the clip.
- **A failed ffmpeg step can leave a 0-byte file** that a "skip if exists" cache then trusts —
  check size, not existence.
- **Fonts are named by file stem** (`Inter-Bold` → `fonts/Inter-Bold.ttf`), passed with `--fonts`.
- **Text `y` is the baseline.** Wrap lines yourself (measure with PIL at the same font/size).
- **Springs over eases** for anything that lands (cards, badges, stamps, photos): `spring=True`,
  `pop=t0`, or `c.spring_keys(t0, a, b, bounce=0.3)`. It accelerates, overshoots a little and
  settles — motion that feels heavy and deliberate. Re-targeting? add a new spring from the
  current value rather than restarting the old one.
- **Stagger** arrivals by ~0.25–0.3 s per item and ~0.06 s within a group.
- Right-to-left replacement text: kestrel sets RTL and mirrors per-character reveals so they run
  in reading order.
- Use `kestrel inspect scene.json` to list what a template lets you override; a job file can swap
  text, images, clips, colours and effect controls without touching the scene.

## 5b. Building with HyperFrames

HyperFrames (heygen-com/hyperframes) renders HTML compositions frame by frame. Its
`product-launch-video` workflow fits most promos. Gotchas:
- **A `<video>` inside a sub-composition renders blank** — put it at host root in `index.html`
  and drive it on `window.__timelines["main"]`; re-inject after every assemble.
- **Two frames that must show the identical object** need identical slot CSS (border,
  `width/height:100%`, `inset:0`, `object-fit:cover`), or the same `object-position` renders
  differently.
- **Smart-crop to faces** by sizing the `<img>` to its natural size and transforming it (fit →
  cover). Never `object-fit:contain` + scale: the letterbox scales too.
- **One sub-agent per frame**, each given explicit geometry, so paired frames match without
  cross-referencing. Worker contract: root sized to the canvas, `data-composition-id` on template
  and root, one paused timeline, fonts by name, `fromTo` entrances, no exit tweens / `Date.now` /
  `Math.random` / `repeat`, content inside the caption keep-out.
- `hyperframes lint` false-positives on a `<video>` literal inside an HTML comment — strip it.
- Verify with `hyperframes snapshot --at t1,t2,…` (contact sheet).

## 6. Sound

- **No track yet? Generate one from a prompt with [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5)**
  — `kit/music.py` drives it two ways, with the same prompt, BPM, key and seed:
  - **locally** (free; open weights, MIT; ~6 GB of GPU memory; Apple Silicon, CUDA, AMD, Intel):
    in an ACE-Step-1.5 checkout run `uv sync`, then
    `ACESTEP_INIT_LLM=false uv run acestep-api --port 8001` (add `ACESTEP_LM_BACKEND=mlx` on a
    Mac). `ACESTEP_INIT_LLM=false` skips ACE-Step's planning language model, which only fills in
    a caption, BPM or key you didn't give and otherwise downloads up to 8 GB more. The first
    request downloads ~6 GB of weights; after that a 10 s track takes ~30 s on an M3 Pro.
  - **on Replicate** (no GPU; billed per run; about half a minute for a short track): set
    `REPLICATE_API_TOKEN` and add `--replicate`. It runs the community-hosted
    `fishaudio/ace-step-1.5`, pinned to a version so a seed gives the same track later.

  ```sh
  python kit/music.py "calm felt piano intro, builds into warm indie-pop with claps, big final chorus" \
      --bpm 120 --key "D Major" --duration 31 --seeds 7,8,9 -o media [--replicate]
  ```
  Write the prompt from the storyboard, not from a genre alone: mood and instruments for each part
  of the energy arc, **instrumental** unless lyrics are wanted, **duration** = the film's length
  plus a second (minimum 10 s). **Set the BPM and key yourself**: the beat grid is then known
  before the track exists (beat = 60 / BPM s), so the storyboard can put every landing on a beat
  (`t = k * 60 / BPM`); the generated track does follow the BPM it is given. Each seed is one
  candidate, saved with a `.json` of the exact request so the chosen one can be regenerated; make
  3–4 and pick by ear. ACE-Step asks that AI-made music be disclosed and checked for unintended
  likeness to existing songs — never prompt with an artist's or a song's name.
- **Beat grid.** `python kit/beats.py music.flac [--bpm 120]` prints the tempo, where beat one
  falls, and the strongest hits. Detectors flip between half and double tempo (a kick on every
  other beat reads as half time); `kit/beats.py` scores the 0.5×, 1× and 2× candidates by how much
  stronger the onsets are on the beats than halfway between them. When you chose the BPM, pass it
  and only the phase is measured — more reliable than any detector. Snap cuts, landings and reveals
  to beats.
- **Energy.** Put the 2–3 big moments on the strongest kicks; put calm, readable moments (a long
  caption, a card to read) in the quietest section. Beats set *timing*, not *amplitude*.
- **Foley as a table** — `[{time, sound, volume}]` on the same timeline as the picture: page
  flips, clicks, a whoosh on a slide, a soft impact on a landing. Real foley, not game-like synths.
- **Check sync after rendering**: `python kit/beats.py out/final.mp4 --bpm 120 --check 2,3.5,6`
  reports each landing's distance from the nearest beat in the render's own audio; pass at < 3
  frames.
- **Narration**: normalise VO to −16 LUFS and duck music under it (~0.25). VO is aspect-agnostic —
  reflowing to another aspect or swapping images doesn't need new audio; a new language does.
- **Always also export a music-free cut** — Reels/TikTok users add their own sound.

## 7. Shaders and finish (light, air, texture)

Two routes, chosen by **where the effect lives**:

| The effect belongs to… | Route | Example |
|---|---|---|
| the whole frame (light, grade, grain, vignette) | the finish pass, after kestrel: `python -m kit.finish` | light leak that swells on cuts |
| one object | an SkSL shader on that layer, inside kestrel: `c.shader(layer, code, uniforms)` | a glint across a card, paper on a label, shading on a page |

**A shader on a layer** (`examples/glint-card`):
```python
from kit.lottie import EASE_IN_OUT
from kit.shaders import GLINT, PAPER
card = c.rect(220, 475, 640, 400, '#C9A45C', radius=30, fade=(0.1, 0.5), rise=60, spring=True)
c.shader(card, PAPER, {"uScale": 2.0, "uAmount": 0.12, "uSeed": 3.0})
c.shader(card, GLINT, {"uSize": [640, 400], "uWidth": 0.06, "uGain": 0.55,
                       "uPos": c.keys((0.7, -0.3), (1.6, 1.3), ease=EASE_IN_OUT)})   # animate a uniform
```
**Revealing a subject from darkness — `LIGHTS`.** Put the subject on a transparent clip (a ProRes
4444 / WebM-alpha capture, a cut-out PNG) over a near-black solid and give it `LIGHTS`: three soft
spotlights (`uSpotA/B/C` = x, y, radius, gain — animate them along paths), an ambient level, and a
rim light computed from the clip's own alpha (`uRim` direction, width, gain; `uRimAt` keeps it on
one side, the way a real rim light falls). Let the silhouette arrive first (rim), sweep a key
across to find the face, then let it fall away. Route searchlights *around* the subject — a spot
on a shirt reads as a torch, not a light. A web page's WebGL canvas usually renders with
transparency: hide the page's HTML with injected CSS, screenshot with `omitBackground`, and drive
the page with Playwright's fake clock (`page.clock.install()`, `runFor(1000 / fps)` per frame) for
a deterministic, full-quality capture with alpha.

Writing your own: `uniform shader content;` is the layer's pixels (`content.eval(p)`); return
premultiplied colour (keep rgb ≤ alpha). What the helper handles, learned the hard way:
- **`p` is in composition pixels**, not the layer's. `shader()` supplies `kOrigin[2]`, the layer's
  top-left animated with its position, so `float2 q = p - float2(kOrigin[0], kOrigin[1]);` is
  layer-local and textures travel with the layer. Layer *scale* isn't compensated.
- **A shader whose uniforms never change draws nothing** (the layer vanishes, no error). `shader()`
  adds a ticking `kTick` uniform to every shader so static ones render too.
- **Uniforms are `float` or `float x[N]` only** (a `float2` is dropped silently); matched by name.
- **A shader that fails to compile also just blanks the layer** — if a layer disappears, test the
  shader alone with a passthrough body (`return content.eval(p);`) and build it back up.
- **Keep shaders on small layers.** Full-frame on the CPU costs ~1 s per 1080p frame; frame-wide
  looks go through the finish pass.

**The finish pass**:

`kit/finish.py` adds, in one FFmpeg pass: a slight grade, a glow (blurred copy screened on), a
warm light leak drifting at the frame edges that swells on each `--flash` cut, grain and a
vignette. Defaults are deliberately subtle (`--leak 0.16 --glow 0.08 --grain 5 --vignette 0.22`).
- **Too strong turns light backgrounds grey or yellow** — on cream/white designs keep the leak
  ≤0.2, warmth 0, vignette ≤0.25. Compare raw vs finished stills side by side before deciding.
- **Smooth fields at low resolution, crisp things as layers.** The light field is computed at 1/8
  resolution and scaled up; it costs milliseconds. A full-frame shader on the CPU costs ~1 s per
  1080p frame — never do that inside the renderer.
- **Grade in YUV** (`eq`, `lutyuv`); an RGB colour-balance pass is ~3× slower.
- **Masks** go in as an in-graph `movie=` source, not a looped `-loop 1` input (memory blow-up when
  audio is mixed in).
- More looks to port from the shader library (§Credits) when a video needs them: Sparkle (glints),
  Paper (texture), Film Stock (per-mood LUT grade), Scratches, Lens Flare. **Port the maths**, keep a
  credit line; don't use the website's presets or editor output (different terms).

## 8. Review — the critique loop

Don't trust a render you haven't looked at.
1. Render stills at every state change (`kestrel render --frame N`, or `ffmpeg -ss t -frames:v 1`)
   and tile them: `ffmpeg -pattern_type glob -i 'f*.png' -vf "scale=360:-1,tile=4x2" sheet.png`.
2. **Score each beat 1–10** against: storyboard match, legibility, hierarchy, motion quality,
   brand fit, truthfulness. Write down the **three worst problems**, fix them, re-render.
3. Repeat until every beat scores **8+**.
4. Look at frames **at full size** for small things: glints, grain, text edges, crop seams.
5. Joined clips: measure the seam (`ffmpeg -lavfi psnr`; ~40 dB is seamless).

**Final checklist before delivery**
- Every product claim on screen is true and shown, not just said.
- Every feature the brief named appears; the storyboard is matched beat for beat.
- **Text height ≥ 5% of frame height** for anything a viewer must read on a phone (at 1350 px tall,
  ~68 px; small labels are fine only if they're decoration).
- Captions sit inside the platform's safe area (9:16: nothing important below ~82% height).
- Paired frames show the identical object; no blank video slots; no cut-off faces.
- Audio: no clipping, music fades out, sync check passed; a music-free cut exists.
- Each aspect re-laid, not cropped; each language re-timed to its own VO.
- It ends with the brand's current postroll, unmodified, in the matching aspect (§9).

## Delivery formats

| Where it goes | Render | Why |
|---|---|---|
| Instagram, TikTok, Facebook, LinkedIn, YouTube upload | `out.mp4` (H.264 + AAC) | what every platform ingests and re-encodes from |
| A website, landing-page hero, docs | `out.webm` (VP9 + Opus) + the MP4 as fallback | royalty-free, ~40% smaller than H.264 at the same look |
| A transparent overlay on a web page | `overlay.webm --transparent` (+ HEVC-alpha or PNG fallback for Safari) | VP9 keeps alpha; Safari can't play it |
| An overlay for another edit (kestrel, NLE, HyperFrames) | `overlay.mov --transparent` (ProRes 4444) | lossless-ish, every editor reads it |
| Thumbnail, `<video poster>`, link preview | `--poster poster.webp@<frame>` on the video render | same scene, pick the frame that sells it (not a fade-in) |

Render the social MP4 and the web WebM from the same scene; never transcode one from the other.

## 9. The postroll — the same ending, every time

**Encourage the user to end every marketing video with the same postroll**: a fixed end card of
2.5–4 s — the logo/wordmark animation, one line (tagline or CTA), the URL or handle, and the same
sound logo. Repetition is the point: viewers learn the ending, the brand becomes recognisable in the
last seconds of any clip, and each new video costs nothing to close.
- **If the user has no postroll yet**, propose making one first, before the next video: design it
  once (HyperFrames suits a wordmark sting; kestrel suits a photo/logo build), get it approved, and
  save it as the brand's asset — `brand/postroll-<aspect>.mp4` for 9:16, 4:5, 1:1 and 16:9 (plus
  `.mov` with alpha if it should sit over the last shot), with its sound logo as a separate stem.
- **If they have one, use it unchanged.** Append it after the video's own finale (§2), on a cut or a
  short cross-fade; don't re-animate, re-time or recolour it per video. The only thing that may vary
  is the CTA line, in a slot the postroll reserves for it, and the language of that line.
- Keep the content's finale and the postroll distinct: the finale peaks on this video's message,
  the postroll is the brand's signature. Put the music's last hit on the cut into the postroll and
  let the sound logo play over its own clean tail (duck or end the track there).
- Version it (`postroll-v2`) when the brand changes, and replace it everywhere at once — not one
  video at a time.
- Review checklist addition: *the video ends with the current postroll, unmodified, in the right
  aspect.*

## 10. Variants

Aspect: re-lay per aspect from the same timeline (side by side in landscape, stacked in portrait).
Language: regenerate the VO and re-sync durations; text layers take RTL replacements. Keep each
variant's project a clone (`rsync -a --exclude renders --exclude node_modules`).

## Do / Don't

- DO start from references and a written state list; DO show the real product; DO render stills
  before the full film; DO run the critique loop; DO keep credits for anything ported.
- DO end every marketing video with the same postroll — and offer to make one if the user has none.
- DON'T fake UI, describe a vibe instead of attaching a frame, end a promo quietly after a climb,
  run full-frame shaders on the CPU, or crop one aspect into another.

## Credits

See `CREDITS.md` at the repo root for the sources behind this skill's methods.
