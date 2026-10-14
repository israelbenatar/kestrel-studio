"""A small builder for Lottie (Bodymovin) scenes, written for kestrel.

Times are in seconds, positions in canvas pixels, colours as '#RRGGBB'. Layers are
added bottom-to-top (the order you would paint them) and reversed on save, since
Lottie draws its first layer on top.

    c = Comp(1080, 1350, fps=30, duration=8)
    c.solid('#F5F0E8')
    c.text('Hello', font='EBGaramond-Regular', size=92, x=540, y=520, align='center',
           reveal=(0.2, 1.0))
    c.image('photo.jpg', 60, 200, 480, 320, radius=12, fade=(0.5, 0.9))
    c.save('scene.json')

Fonts are named by file stem (`EBGaramond-Regular` -> EBGaramond-Regular.ttf in a
`--fonts` folder). Images and clips are used at the size they are placed; crop them
to the slot first (kestrel_studio.media does that) so nothing is stretched.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

# ease-out cubic, ease-in-out, linear: Lottie bezier handles
EASE_OUT = {"i": {"x": [0.2], "y": [1]}, "o": {"x": [0.3], "y": [0]}}
EASE_IN_OUT = {"i": {"x": [0.6], "y": [1]}, "o": {"x": [0.4], "y": [0]}}
LINEAR = {"i": {"x": [1], "y": [1]}, "o": {"x": [0], "y": [0]}}


def rgb(hexcolor: str) -> list[float]:
    h = hexcolor.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def static(v):
    return {"a": 0, "k": v}


def rounded_rect_path(w, h, r):
    """Closed bezier path for a w x h rectangle at the origin, corner radius r."""
    if r <= 0:
        return {"i": [[0, 0]] * 4, "o": [[0, 0]] * 4, "v": [[0, 0], [w, 0], [w, h], [0, h]], "c": True}
    k = r * 0.5523
    v = [[r, 0], [w - r, 0], [w, r], [w, h - r], [w - r, h], [r, h], [0, h - r], [0, r]]
    i = [[-k, 0], [0, 0], [0, -k], [0, 0], [k, 0], [0, 0], [0, k], [0, 0]]
    o = [[0, 0], [k, 0], [0, 0], [0, k], [0, 0], [-k, 0], [0, 0], [0, -k]]
    return {"i": i, "o": o, "v": v, "c": True}


class Comp:
    def __init__(self, w: int, h: int, *, fps: int = 30, duration: float, name: str = "scene"):
        self.w, self.h, self.fps, self.duration, self.name = w, h, fps, duration, name
        self.layers: list[dict] = []
        self.assets: list[dict] = []
        self.fonts: dict[str, dict] = {}
        self._asset_ids: dict[str, str] = {}

    # ---------- time & keyframes ----------
    def f(self, t: float) -> float:
        return round(t * self.fps, 3)

    def keys(self, *pairs, ease=EASE_OUT):
        """Animated property from (time_s, value) pairs."""
        out = []
        for n, (t, v) in enumerate(pairs):
            k = {"t": self.f(t), "s": v if isinstance(v, list) else [v]}
            if n < len(pairs) - 1:
                k.update(ease)
            out.append(k)
        return {"a": 1, "k": out}

    def spring_keys(self, t0, a, b, *, duration=0.9, bounce=0.3):
        """a -> b on a closed-form damped spring starting at t0: it speeds up, overshoots by about
        *bounce*, and settles. Baked as one linear keyframe per frame, so the motion stays a pure
        function of time (no simulation state). *a*/*b* are numbers or equal-length lists.
        Springs for weight: an idea from @0xMovez (see CREDITS.md)."""
        zeta = max(0.05, 1 - bounce)                   # damping ratio: bounce 0 = critically damped
        omega = 2 * 3.14159 * 1.25 / duration          # settles in about *duration*
        wd = omega * (1 - min(zeta, 0.999) ** 2) ** 0.5
        steps = max(2, int(duration * self.fps) + 1)
        av = a if isinstance(a, list) else [a]
        bv = b if isinstance(b, list) else [b]
        out = []
        for n in range(steps + 1):
            t = n / self.fps
            x = 1 - math.exp(-zeta * omega * t) * (math.cos(wd * t) + zeta * omega / wd * math.sin(wd * t))
            if n == steps:
                x = 1.0
            k = {"t": self.f(t0 + t), "s": [p + (q - p) * x for p, q in zip(av, bv)]}
            if n < steps:
                k.update(LINEAR)
            out.append(k)
        return {"a": 1, "k": out}

    def _transform(self, x, y, *, anchor=(0, 0), opacity=None, pos=None, scale=None, rot=None):
        return {"o": opacity or static(100), "r": rot or static(0),
                "p": pos or static([x, y, 0]), "a": static([anchor[0], anchor[1], 0]),
                "s": scale or static([100, 100, 100])}

    def _layer(self, ty, name, ip, op, ks, **extra):
        ind = len(self.layers) + 1
        layer = {"ty": ty, "ind": ind, "nm": name, "ip": self.f(ip), "op": self.f(op if op is not None else self.duration),
                 "st": 0, "sr": 1, "ao": 0, "ks": ks, **extra}
        self.layers.append(layer)
        return layer

    def _motion(self, x, y, w, h, *, ip, fade=None, fade_out=None, rise=0, slide=None, zoom=None, pivot="center",
                opacity=100, pop=None, spring=False):
        """Transform for a box at (x, y, w, h): optional fade in/out, a rise from below during the fade,
        a slide ((dx, dy) from which it arrives), and a slow zoom ((s0, s1) over the layer's life).
        pop=t0: scale in from 85% on a spring at t0. spring=True: the rise/slide lands on a spring
        instead of an ease."""
        ax, ay = (w / 2, h / 2) if pivot == "center" else (0, 0)
        px, py = x + ax, y + ay
        op_keys = []
        if fade:
            op_keys += [(fade[0], 0), (fade[1], opacity)]
        if fade_out:
            if not op_keys:
                op_keys.append((fade_out[0], opacity))
            else:
                op_keys.append((fade_out[0], opacity))
            op_keys.append((fade_out[1], 0))
        opacity_p = self.keys(*op_keys) if op_keys else static(opacity)
        pos = None
        if fade and (rise or slide):
            dx, dy = slide if slide else (0, rise)
            if spring:
                pos = self.spring_keys(fade[0], [px + dx, py + dy, 0], [px, py, 0])
            else:
                pos = self.keys((fade[0], [px + dx, py + dy, 0]), (fade[1], [px, py, 0]))
        scale = None
        if pop is not None:
            scale = self.spring_keys(pop, [85, 85, 100], [100, 100, 100], duration=0.7, bounce=0.35)
        elif zoom:
            (t0, t1), (s0, s1) = zoom
            scale = self.keys((t0, [s0, s0, 100]), (t1, [s1, s1, 100]), ease=LINEAR)
        return self._transform(px, py, anchor=(ax, ay), opacity=opacity_p, pos=pos, scale=scale)

    # ---------- assets ----------
    def _asset(self, path: str | Path, w: int, h: int, video=False) -> str:
        key = f"{path}|{w}x{h}"
        if key not in self._asset_ids:
            aid = f"{'video' if video else 'image'}_{len(self.assets)}"
            p = Path(path)
            self.assets.append({"id": aid, "w": w, "h": h, "u": str(p.parent.resolve()) + "/", "p": p.name, "e": 0})
            self._asset_ids[key] = aid
        return self._asset_ids[key]

    def _font(self, font: str):
        self.fonts.setdefault(font, {"fName": font, "fFamily": font, "fStyle": "Regular", "ascent": 75})

    # ---------- layers ----------
    def solid(self, color: str, *, ip=0, op=None, fade=None, fade_out=None, name="Background"):
        ks = self._motion(0, 0, self.w, self.h, ip=ip, fade=fade, fade_out=fade_out)
        return self._layer(1, name, ip, op, ks, sc=color, sw=self.w, sh=self.h)

    def rect(self, x, y, w, h, color: str, *, radius=0, ip=0, op=None, opacity=100, name="Rect", **motion):
        ks = self._motion(x, y, w, h, ip=ip, opacity=opacity, **motion)
        ax, ay = w / 2, h / 2
        shape = {"ty": "gr", "nm": name, "it": [
            {"ty": "rc", "nm": "Box", "d": 1, "p": static([ax, ay]), "s": static([w, h]), "r": static(radius)},
            {"ty": "fl", "nm": "Fill", "c": static(rgb(color) + [1]), "o": static(100), "r": 1},
            {"ty": "tr", "p": static([0, 0]), "a": static([0, 0]), "s": static([100, 100]), "r": static(0),
             "o": static(100), "sk": static(0), "sa": static(0)}]}
        return self._layer(4, name, ip, op, ks, shapes=[shape])

    def circle(self, cx, cy, d, color: str, *, ip=0, op=None, name="Dot", color_keys=None, **motion):
        ks = self._motion(cx - d / 2, cy - d / 2, d, d, ip=ip, **motion)
        fill = color_keys or static(rgb(color) + [1])
        shape = {"ty": "gr", "nm": name, "it": [
            {"ty": "el", "nm": "Ellipse", "d": 1, "p": static([d / 2, d / 2]), "s": static([d, d])},
            {"ty": "fl", "nm": "Fill", "c": fill, "o": static(100), "r": 1},
            {"ty": "tr", "p": static([0, 0]), "a": static([0, 0]), "s": static([100, 100]), "r": static(0),
             "o": static(100), "sk": static(0), "sa": static(0)}]}
        return self._layer(4, name, ip, op, ks, shapes=[shape])

    def image(self, path, x, y, w, h, *, radius=0, ip=0, op=None, name=None, **motion):
        aid = self._asset(path, w, h)
        ks = self._motion(x, y, w, h, ip=ip, **motion)
        extra = {"refId": aid}
        if radius:
            extra.update(hasMask=True, masksProperties=[{"nm": "Round", "mode": "a", "inv": False, "o": static(100),
                                                         "x": static(0), "pt": static(rounded_rect_path(w, h, radius))}])
        return self._layer(2, name or Path(path).stem, ip, op, ks, **extra)

    def video(self, path, x, y, w, h, *, start=0.0, radius=0, ip=0, op=None, name=None, **motion):
        """A clip placed at (x, y, w, h); its first frame shows at time *start*."""
        aid = self._asset(path, w, h, video=True)
        ks = self._motion(x, y, w, h, ip=ip, **motion)
        extra = {"refId": aid}
        if radius:
            extra.update(hasMask=True, masksProperties=[{"nm": "Round", "mode": "a", "inv": False, "o": static(100),
                                                         "x": static(0), "pt": static(rounded_rect_path(w, h, radius))}])
        layer = self._layer(2, name or Path(path).stem, ip, op, ks, **extra)
        layer["st"] = self.f(start)
        return layer

    def text(self, text, *, font, size, x, y, color="#000000", align="left", ip=0, op=None, tracking=0,
             line_height=None, reveal=None, typewriter=None, name=None, **motion):
        """Point text; *y* is the first baseline. Lines break at '\\n'.
        reveal=(t0, t1): characters rise and fade in, in reading order.
        typewriter=(t0, t1): the text types itself out."""
        self._font(font)
        j = {"left": 0, "right": 1, "center": 2}[align]
        doc = {"s": size, "f": font, "t": text.replace("\n", "\r"), "j": j, "tr": tracking,
               "lh": line_height or size * 1.2, "ls": 0, "fc": rgb(color)}
        tdoc = {"k": [{"t": 0, "s": doc}]}
        if typewriter:
            t0, t1 = typewriter
            tdoc["x"] = (f"var $bm_rt;\nvar full = value;\nvar n = Math.floor(linear(time, {t0}, {t1}, 0, full.length));\n"
                         f"$bm_rt = full.substr(0, n);")
        animators = []
        if reveal:
            t0, t1 = reveal
            animators.append({"nm": "Reveal", "s": {"t": 0, "xe": static(0), "ne": static(0), "a": static(100), "b": 1,
                                                    "rn": 0, "sh": 1, "r": 1, "e": static(100), "o": static(0),
                                                    "s": self.keys((t0, 0), (t1, 100), ease=EASE_IN_OUT)},
                              "a": {"p": static([0, size * 0.45, 0]), "o": static(0)}})
        ks = self._motion(x, y, 0, 0, ip=ip, pivot="origin", **motion)
        return self._layer(5, name or text[:24], ip, op, ks,
                           t={"d": tdoc, "p": {}, "m": {"g": 1, "a": static([0, 0])}, "a": animators})

    # ---------- shaders ----------
    def shader(self, layer: dict, code: str, uniforms: dict | None = None, *, content: bool = True,
               name: str = "shader") -> dict:
        """Attach an SkSL shader to *layer* (kestrel runs it through Skottie's "SkSL Shader" effect).

        The shader sees the layer's own pixels as `uniform shader content;` (content=True) and
        returns the new colour, premultiplied — keep rgb <= alpha. `p` arrives in COMPOSITION
        pixels; every shader also gets `kOrigin[2]`, the layer's top-left corner, animated with the
        layer's position, so `p - float2(kOrigin[0], kOrigin[1])` is the layer's own pixels and a
        texture or glint moves with the layer (layer scale is not compensated: keep scaled layers'
        effects position-independent). Uniforms must be declared `float` or `float x[N]`
        (a float2 is silently dropped); pass each as a number, a list (for float[N]), or an
        animated property from `keys()` / `spring_keys()`.

        Use it on the layer the effect belongs to (a glint on a card, paper on a page). A
        full-frame shader runs on the CPU at ~1 s per 1080p frame: frame-wide light belongs in
        kit.finish instead."""
        # Skottie (Skia m144) only draws an SkSL effect once one of its uniforms has changed; with
        # every uniform static the layer silently disappears. An unused uniform that ticks over the
        # comp's life keeps every shader live, static ones included.
        props = [{"nm": "sksl", "sh": "uniform float kTick[1];\nuniform float kOrigin[2];\n" + code}]
        if content:
            props.append({"nm": "content", "ty": 99})
        for u, v in (uniforms or {}).items():
            prop = v if isinstance(v, dict) else static(v if isinstance(v, list) else [v])
            props.append({"nm": u, "ty": 0, "v": prop})
        props.append({"nm": "kTick", "ty": 0, "v": self.keys((0, 0), (self.duration, 1), ease=LINEAR)})
        # the layer's top-left in comp pixels: its position minus its anchor, keyframe for keyframe
        ks = layer["ks"]
        ax, ay = ks["a"]["k"][0], ks["a"]["k"][1]
        pos = ks["p"]
        if pos.get("a"):
            origin = {"a": 1, "k": [{**k, "s": [k["s"][0] - ax, k["s"][1] - ay]} for k in pos["k"]]}
        else:
            origin = static([pos["k"][0] - ax, pos["k"][1] - ay])
        props.append({"nm": "kOrigin", "ty": 0, "v": origin})
        layer.setdefault("ef", []).append({"ty": 5, "nm": name, "mn": "SkSL Shader", "en": 1, "ef": props})
        return layer

    # ---------- output ----------
    def to_dict(self) -> dict:
        layers = list(reversed(self.layers))
        for n, layer in enumerate(layers):
            layer["ind"] = n + 1
        return {"v": "5.7.4", "fr": self.fps, "ip": 0, "op": self.f(self.duration), "w": self.w, "h": self.h,
                "nm": self.name, "ddd": 0, "assets": self.assets,
                "fonts": {"list": list(self.fonts.values())}, "layers": layers}

    def save(self, path) -> Path:
        p = Path(path)
        p.write_text(json.dumps(self.to_dict()))
        return p
