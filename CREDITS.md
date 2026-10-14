# Credits

This kit stands on other people's work. Code that is ported keeps a credit line in the file it
lives in; ideas and methods are credited here.

## Methods and ideas

| Source | Licence | What we took |
|---|---|---|
| [shader-effects-inc/shaders](https://github.com/shader-effects-inc/shaders), © 2026 Shader Effects Inc. | MIT | The maths behind `kit/finish.py`: LightLeak, Glow, FilmGrain, Vignette (ported by hand from their TypeGPU/WGSL recipes to numpy + FFmpeg). The list of further looks worth porting (Sparkle, Paper, Film Stock, Scratches, Lens Flare). Only the MIT repo is used, not the presets or editor on shaders.com, which have their own terms. |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | Apache-2.0 | The HTML frame-by-frame engine and its `product-launch-video` workflow that §5b of the skill builds on, and the gotchas collected while using it. |
| [Vincentwei1021/video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft) | Apache-2.0 | Methodology, rewritten in our own words: the four-part energy arc for promos; at most three big impacts, on the strongest kicks; scoring 0.5×/1×/2× tempo candidates against kicks to fix tempo doubling; foley as a declarative timeline table; the post-render beat-sync check (< 3 frames); the pre-delivery review checklist, including minimum text height (≥ 5% of frame height); always exporting a music-free cut. No code or recipe cards are copied. |
| [@0xMovez](https://x.com/0xMovez/status/2104216919033192746), "How to build a motion design studio with Opus 5.5" | article | The framing of the skill: the model writes a deterministic program (`draw(t)`), not a video; the harness matters more than the prompt; references beat descriptions; write the state list; closed-form springs (`Comp.spring_keys`); sound on a beat grid; the render–score–fix critique loop until every beat scores 8+; every aspect from one timeline; package the pipeline as a skill. |
| [ace-step/ACE-Step-1.5](https://github.com/ace-step/ACE-Step-1.5) | MIT | Recommended in §6 of the skill for generating a film's music from a prompt. Not bundled; you install and run it yourself. |

## The renderer (kestrel)

kestrel is distributed here as a compiled binary. It is built on:

| Project | Licence | Use |
|---|---|---|
| [Skia](https://skia.org) and its Skottie module | BSD-3-Clause | Lottie playback and rasterisation |
| [JetBrains/skia-pack](https://github.com/JetBrains/skia-pack) | Apache-2.0 | Prebuilt Skia (m144) |
| [FFmpeg](https://ffmpeg.org) 8.0.1 | LGPL-2.1+ (built with no GPL or non-free parts; shipped as replaceable shared libraries) | Decoding clips, encoding MP4/ProRes, audio mux |
| [OpenH264](https://github.com/cisco/openh264) (Cisco) | BSD-2-Clause | Software H.264 encoding where no hardware encoder is available |
| [libvpx](https://chromium.googlesource.com/webm/libvpx) | BSD-3-Clause (VP9 royalty-free) | VP9 encoding and VP8/VP9 decoding, including WebM alpha |
| [Opus / libopus](https://opus-codec.org) | BSD-3-Clause | WebM audio |
| [libwebp](https://chromium.googlesource.com/webm/libwebp) (inside Skia) | BSD-3-Clause | WebP stills and posters |
| [quickjs-ng](https://github.com/quickjs-ng/quickjs) | MIT | After Effects expressions |
| [airbnb/lottie-web](https://github.com/airbnb/lottie-web) test animations | MIT | Conformance testing (not shipped) |

## Fonts

All under the [SIL Open Font License 1.1](https://openfontlicense.org): EB Garamond
(Georg Duffner, Octavio Pardo), Inter (Rasmus Andersson), Dancing Script (Pablo Impallari).
