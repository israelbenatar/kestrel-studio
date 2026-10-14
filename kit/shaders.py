"""Ready-made SkSL layer shaders for `Comp.shader()`.

Each constant is SkSL source; the comment above it lists the uniforms it expects. All of them
read the layer's own pixels (`content`), work in layer-local pixels via the `kOrigin` that
`Comp.shader()` supplies, and return premultiplied colour, so they compose with masks, fades and
the layers around them, and move with their layer.

    from kit.shaders import GLINT
    card = c.rect(240, 480, 600, 380, '#C9A45C', radius=28)
    c.shader(card, GLINT, {"uSize": [600, 380], "uPos": c.keys((0.8, -0.3), (1.8, 1.3))})
"""

# A soft diagonal band of light sweeping across the layer — foil, glass, a card catching the light.
#   uSize[2]   the layer's width and height in its own pixels
#   uPos[1]    band position: -0.3 (before the left edge) .. 1.3 (past the right); animate it
#   uWidth[1]  band softness (default look: 0.06)
#   uGain[1]   peak brightness added (0.5 is bright, 0.25 subtle)
GLINT = """uniform shader content;
uniform float uSize[2];
uniform float uPos[1];
uniform float uWidth[1];
uniform float uGain[1];
half4 main(float2 p) {
  half4 c = content.eval(p);
  float2 q = p - float2(kOrigin[0], kOrigin[1]);   // layer pixels
  // distance across a band leaning 30 degrees, normalised to the layer's diagonal extent
  float d = (q.x + q.y * 0.58) / (uSize[0] + uSize[1] * 0.58) - uPos[0];
  float core = exp(-d * d / (uWidth[0] * uWidth[0] * 0.5));
  float halo = exp(-d * d / (uWidth[0] * uWidth[0] * 6.0)) * 0.35;
  half g = half((core + halo) * uGain[0]);
  half3 rgb = c.rgb + half3(g, g * 0.97, g * 0.9) * c.a;   // slightly warm light, only where opaque
  return half4(min(rgb, half3(c.a)), c.a);
}"""

# Paper: fine fibre noise plus a faint large-scale mottle, multiplied into the layer — for cards,
# labels and pages that would otherwise be flat colour. Static unless uSeed is animated.
#   uScale[1]   fibre size in pixels (1.5 fine .. 4 coarse)
#   uAmount[1]  strength (0.06 subtle .. 0.15 obvious)
#   uSeed[1]    any number; change it to vary the sheet
PAPER = """uniform shader content;
uniform float uScale[1];
uniform float uAmount[1];
uniform float uSeed[1];
float hash(float2 q) { return fract(sin(dot(q, float2(127.1, 311.7)) + uSeed[0]) * 43758.5453); }
float noise(float2 q) {
  float2 i = floor(q), f = fract(q);
  float2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + float2(1, 0)), u.x), mix(hash(i + float2(0, 1)), hash(i + float2(1, 1)), u.x), u.y);
}
half4 main(float2 p) {
  half4 c = content.eval(p);
  float2 l = p - float2(kOrigin[0], kOrigin[1]);   // layer pixels: the texture travels with the layer
  float2 q = l / uScale[0];
  float fibre = noise(q) * 0.6 + noise(q * float2(3.1, 0.7)) * 0.4;   // stretched: fibres run one way
  float mottle = noise(l / 90.0);
  float shade = 1.0 - uAmount[0] * (fibre * 0.8 + mottle * 0.6 - 0.5);
  return half4(c.rgb * half(shade), c.a);
}"""

# Stage lights: the layer sits in darkness and only what the lights reach shows — three soft
# spotlights you move by animating their uniforms, plus a rim light built from the layer's own
# alpha (edges that face the light glow), so a cut-out subject (a transparent ProRes/WebM clip,
# a PNG) gets a silhouette before its face. Coordinates are layer pixels.
#   uSpotA[4], uSpotB[4], uSpotC[4]   x, y, radius, gain (gain 0 = off; 1 = full exposure at centre)
#   uTint[3]     colour of the spotlights (1,1,1 neutral; warm it slightly for skin)
#   uAmbient[1]  light everywhere (0 = black outside the spots)
#   uRim[4]      direction x, y (toward the light, any length), width in px, gain
#   uRimAt[3]    x, y, radius: where the rim light falls (a rim lights one side of a subject, not all
#                of its outline); use a huge radius for everywhere
#   uRimColor[3] rim colour (linear 0..1)
LIGHTS = """uniform shader content;
uniform float uSpotA[4];
uniform float uSpotB[4];
uniform float uSpotC[4];
uniform float uTint[3];
uniform float uAmbient[1];
uniform float uRim[4];
uniform float uRimAt[3];
uniform float uRimColor[3];
half4 main(float2 p) {
  half4 c = content.eval(p);
  float2 q = p - float2(kOrigin[0], kOrigin[1]);
  float l = uAmbient[0];
  float2 d = q - float2(uSpotA[0], uSpotA[1]); l += uSpotA[3] * exp(-dot(d, d) / max(uSpotA[2] * uSpotA[2], 1.0));
  d = q - float2(uSpotB[0], uSpotB[1]);        l += uSpotB[3] * exp(-dot(d, d) / max(uSpotB[2] * uSpotB[2], 1.0));
  d = q - float2(uSpotC[0], uSpotC[1]);        l += uSpotC[3] * exp(-dot(d, d) / max(uSpotC[2] * uSpotC[2], 1.0));
  // rim: opaque here, transparent toward the light; three taps give a soft falloff into the subject
  float2 dir = normalize(float2(uRim[0], uRim[1]) + float2(1e-5, 0.0));
  float open = 0.0;
  open += 1.0 - content.eval(p + dir * uRim[2] * 0.35).a;
  open += 1.0 - content.eval(p + dir * uRim[2] * 0.7).a;
  open += 1.0 - content.eval(p + dir * uRim[2]).a;
  float2 r = q - float2(uRimAt[0], uRimAt[1]);
  float rim = float(c.a) * (open / 3.0) * uRim[3] * exp(-dot(r, r) / max(uRimAt[2] * uRimAt[2], 1.0));
  half3 rgb = c.rgb * half(l) * half3(uTint[0], uTint[1], uTint[2])
            + half3(uRimColor[0], uRimColor[1], uRimColor[2]) * half(rim) * c.a;
  return half4(min(rgb, half3(c.a)), c.a);
}"""
