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
