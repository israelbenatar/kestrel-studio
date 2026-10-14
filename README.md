# kestrel-studio

Marketing & social videos, written as code. Product promos, feature demos, social clips and site
heroes are a program that draws every frame, not a generated video, so a fix is an edit and a
re-render, not a reroll.

It is three things:

- **`skill/`** — an agent skill (`kestrel-video`) that takes a video from brief to finished file:
  framing, state list, real media, engine choice, sound on a beat grid, shaders and a film finish,
  a render–review–fix loop, delivery formats and a fixed postroll.
- **`kit/`** — the Python helpers the skill uses: a Lottie scene builder (`Comp`, with springs,
  text reveals, video layers and SkSL layer shaders), ready-made shaders, the finish pass, music
  generation (ACE-Step, local or Replicate) and a beat grid with a sync check.
- **kestrel** — a fast native Lottie → video renderer (Skia Skottie + FFmpeg), shipped as a
  compiled binary. It renders MP4, WebM (with alpha), ProRes and WebP posters, and composites
  [HyperFrames](https://github.com/heygen-com/hyperframes) renders as layers, transparent ones
  included.

## Why it exists

This started as the in-house pipeline for social and marketing videos for
[Sustain](https://www.sustain-app.com), an app that turns your photos into a designed photo album.
Every video in `examples/` was made for Sustain with this kit and shows the real product. The skill
and the kit themselves are generic: nothing in them is tied to Sustain, albums or any one brand.

## The workflow

The skill walks an agent through the same steps for every video:

1. **Frame it.** Subject (one message), goal, channel, aspect, length, language, narration or
   music only. Collect references (a named look, a frame, a clip) rather than adjectives.
   **Take the design from the product's website:** colours, fonts, radii and logo are read from
   the live site with Playwright into `brand/brand.json`, which you confirm and both engines use.
2. **Write the state list.** A beat-by-beat `STORYBOARD.md`: time, what's on screen, what moves,
   what the viewer takes away. Promos follow a four-part energy arc: quiet open, one hero moment,
   a feature climb, a finale at peak energy. You approve it before any frame is built.
3. **Show the real thing.** Real data and real photos, and the real product captured by a script
   so a take can be repeated: **Playwright** for web apps, **Maestro** for iOS and Android apps.
   Captures are saved into the project (`assets/captures/`), named after the storyboard beat they
   serve, and the build reads them from there. Cut waiting time instead of faking speed.
4. **Pick the engine per beat.** kestrel for photo- and clip-heavy beats, text animation and the
   long timeline; HyperFrames for what CSS does best (3D perspective, blur, glass, complex
   layout). kestrel composites the HyperFrames renders, transparent ones included, into one film.
5. **Build.** Scenes are Python (`kit/lottie.py`) or HTML; springs and easing are closed-form, so
   every render is identical.
6. **Sound.** Generate a track from a prompt with ACE-Step 1.5, locally or on Replicate, at a
   tempo you choose (or bring one), so every cut and landing can sit on a beat; lay foley as a
   timeline table, check sync after rendering (< 3 frames off), and always export a music-free cut.
7. **Shaders and finish.** Per-object effects as SkSL shaders on a layer (glint, paper);
   whole-frame light leak, glow, grain and vignette in one finish pass.
8. **Review.** Render stills at every state change, score each beat 1–10, fix the three worst
   problems, repeat until every beat scores 8+. Then a delivery checklist (text ≥ 5% of frame
   height, safe areas, truthful claims).
9. **Deliver.** MP4 for social, WebM for the web, transparent WebM/ProRes for overlays, a WebP
   poster.
10. **Postroll.** End every marketing video with the same brand end card, unchanged. If there
    isn't one yet, the skill proposes making it first.
11. **Variants.** Other aspects are re-laid from the same timeline, never cropped; other languages
    get their own voice-over and timing.

## Example prompts

With the skill installed (copy `skill/` to `~/.claude/skills/kestrel-video/`, or point your agent
at `skill/SKILL.md`):

- *"Make a 30-second 4:5 Instagram promo for our new export feature. Take the look from
  example.com, record the export flow on the staging site with Playwright, and save the captures in
  the project. Music only, upbeat."*
- *"Record the onboarding flow of our iOS app on the simulator with Maestro and turn it into a
  15-second 9:16 Reel."*
- *"Read the design of our website and set up `brand.json` before we storyboard anything."*
- *"Turn this storyboard into a 9:16 Reel and a 16:9 version for the website hero, from the same
  timeline."*
- *"We don't have an end card yet. Design a 3-second postroll with our wordmark and URL in all four
  aspects, then add it to the launch video."*
- *"Add a glint sweeping across the pricing card when it lands, and a paper texture on it."*
- *"Generate three instrumental candidates at 118 BPM for the launch film on Replicate, and put
  every cut in the storyboard on a beat."*
- *"Here's `track.mp3`. Re-time the cuts in `build.py` to its beats and give me a music-free cut
  too."*
- *"Review `out/final.mp4` against `STORYBOARD.md` and fix whatever scores below 8."*

## Prerequisites

**Required**

| What | Why | Cost |
|---|---|---|
| An AI coding agent that loads skills (e.g. [Claude Code](https://claude.com/claude-code)) | runs the workflow | that agent's own plan or API usage |
| Python 3.10+ with `numpy` and `pillow` | the kit | free |
| FFmpeg and ffprobe on the `PATH` | finish pass, stills, sync checks | free |
| kestrel (from this repo's releases) | rendering | free |

**Optional, depending on the video**

| What | When you need it | Account or cost |
|---|---|---|
| Node.js 22+ and [HyperFrames](https://github.com/heygen-com/hyperframes) (`npx hyperframes`) | HTML-built beats (3D, blur, glass, complex layout) | none: open source, renders locally in headless Chrome |
| A text-to-speech service (e.g. HeyGen, ElevenLabs) | narrated videos | an account and an API key with that provider; usually paid per character or minute |
| Music: [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) running locally | generating a track from a prompt (`kit/music.py`) | none: open weights (MIT); about 6 GB of GPU memory (Apple Silicon works), a one-time ~6 GB model download; ~30 s per short track on an M3 Pro |
| Music: ACE-Step 1.5 on [Replicate](https://replicate.com/fishaudio/ace-step-1.5) | the same, without a GPU (`kit/music.py --replicate`) | a Replicate account with credits and an API token (`REPLICATE_API_TOKEN`); billed per run |
| Music: your own track | instead of generating one | a licence that covers your channel |
| An image or video generation service (e.g. Replicate, the same account as above) | AI-generated people or scenes when you have no real photos | an account with credits on that service |
| [Playwright](https://playwright.dev) | reading your site's design; capturing a web app | free |
| [Maestro](https://maestro.mobile.dev) + Xcode or Android Studio | capturing an iOS or Android app on a simulator or emulator | free (Maestro Cloud is paid but not needed) |

The skill and kit never call a paid service themselves; the agent only uses the ones you set up.

## Quickstart

```sh
python3 -m venv .venv && .venv/bin/pip install numpy pillow
cd examples/glint-card
../../.venv/bin/python build.py                       # writes scene.json
kestrel render scene.json -o out/glint.mp4 --fonts ../../fonts
```

## Examples

| Example | What it shows |
|---|---|
| `examples/glint-card` | Layer shaders and music on a beat: a card with a paper texture catching the light twice, to an ACE-Step track generated at 120 BPM; each glint and line of text lands on a beat (sync check under 1 frame). Renders in about 2.5 s. |
| `examples/launch-linkedin` | The kestrel studio launch film for LinkedIn (4:5, 33 s), made with the skill end to end: the site's look read into `brand.json`, Playwright captures, a HyperFrames 3D unfold handed to kestrel, an ACE-Step track with every landing on a beat, and the postroll. |
| `examples/chat-sorting` | A Sustain feature film: screen recordings of the real app, a HyperFrames intro, a transparent HyperFrames outro composited over kestrel layers, and the finish pass. |

The people in the example photos are AI-generated (Flux 1.1 Pro on Replicate); no real person is
depicted.

## Site

`site/` is the kestrel studio landing page (static HTML; serve it with `python3 -m http.server`). The
launch example captures it.

## Credits

See [CREDITS.md](CREDITS.md) for the projects, methods and fonts this builds on.
