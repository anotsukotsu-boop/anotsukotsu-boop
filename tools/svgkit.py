"""Tiny toolkit for hand-built animated SVGs.

Text is rendered as real glyph outlines (not <text>), so every SVG looks the
same in every browser and never depends on fonts being installed or on
GitHub's image proxy allowing embedded web fonts. Each glyph is defined once
in <defs> and reused with <use>, which keeps the files small.
"""

from __future__ import annotations

import math
import random
import urllib.request
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONT_DIR = Path(__file__).resolve().parent / ".fonts"
GF = "https://github.com/google/fonts/raw/main/"

# key -> (path in google/fonts, variable-axis location or None)
FONT_SPECS = {
    "serif": ("ofl/shipporiminchob1/ShipporiMinchoB1-Bold.ttf", None),
    "serif-md": ("ofl/shipporiminchob1/ShipporiMinchoB1-Medium.ttf", None),
    "mono": ("ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf", {"wght": 400}),
    "mono-b": ("ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf", {"wght": 700}),
    "brush": ("ofl/yujisyuku/YujiSyuku-Regular.ttf", None),
}
FALLBACK = ["serif", "mono", "brush"]

# ------------------------------------------ palette: Subaru's staircase
# Night teal, neon green flashes and the acid-yellow light on his face.
# Vermilion is kept for death and hanko seals only.
C = {
    "sumi0": "#030910",   # 夜 night
    "sumi1": "#06110f",
    "sumi2": "#0b1a16",
    "line": "#1d3a31",
    "muted": "#8fa89a",   # 霧 mist
    "kinari": "#eef3dc",  # pale washi, tinted by the scene
    "acid": "#d9e67a",    # 黄 the light on Subaru's face
    "acid-d": "#a8b84a",
    "neon": "#24e33d",    # 翠 the green flashes
    "teal": "#1f8a70",
    "ai": "#1f6f63",      # deep teal
    "shu": "#e03c31",     # 朱 vermilion: death and seals
    "shu-d": "#9e2a1f",
    "sakura": "#e8a0b4",
    "matcha": "#5fd97a",
    "gin": "#c9cdd4",
    "kaki": "#e07b39",
}


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "svgkit"})
    with urllib.request.urlopen(req, timeout=180) as r:
        dest.write_bytes(r.read())


class Font:
    def __init__(self, key: str):
        path, loc = FONT_SPECS[key]
        raw = FONT_DIR / urllib.request.unquote(path.rsplit("/", 1)[1])
        if not raw.exists():
            print(f"  downloading {raw.name} ...")
            _download(GF + path, raw)
        tt = TTFont(raw)
        if loc and "fvar" in tt:
            tt = instancer.instantiateVariableFont(tt, loc)
        self.key = key
        self.cmap = tt.getBestCmap()
        self.gs = tt.getGlyphSet()
        self.hmtx = tt["hmtx"]
        self.upm = tt["head"].unitsPerEm
        self._paths: dict[str, str] = {}

    def has(self, ch: str) -> bool:
        return ord(ch) in self.cmap

    def advance(self, ch: str) -> int:
        return self.hmtx[self.cmap[ord(ch)]][0]

    def path(self, ch: str) -> str:
        if ch not in self._paths:
            pen = SVGPathPen(self.gs, ntos=lambda v: f"{v:.0f}")
            self.gs[self.cmap[ord(ch)]].draw(TransformPen(pen, (1, 0, 0, -1, 0, 0)))
            self._paths[ch] = pen.getCommands()
        return self._paths[ch]


_FONTS: dict[str, Font] = {}


def font(key: str) -> Font:
    if key not in _FONTS:
        _FONTS[key] = Font(key)
    return _FONTS[key]


class Doc:
    """One SVG document: collects glyph defs, CSS and body markup."""

    def __init__(self, w: int, h: int, title: str, desc: str):
        self.w, self.h = w, h
        self.title, self.desc = title, desc
        self.css: list[str] = []
        self.defs: list[str] = []
        self.body: list[str] = []
        self._glyphs: dict[str, str] = {}

    # -- glyphs -------------------------------------------------------------
    def _resolve(self, ch: str, key: str) -> Font | None:
        for k in [key] + [f for f in FALLBACK if f != key]:
            f = font(k)
            if f.has(ch):
                return f
        print(f"  ! missing glyph {ch!r} (U+{ord(ch):04X})")
        return None

    def _glyph_id(self, f: Font, ch: str) -> str:
        gid = f"{f.key}-{ord(ch):x}"
        if gid not in self._glyphs:
            self._glyphs[gid] = f'<path id="{gid}" d="{f.path(ch)}" pathLength="1"/>'
        return gid

    def measure(self, s: str, key: str, size: float, ls: float = 0) -> float:
        base = font(key)
        total = 0.0
        for ch in s:
            f = base if ch == " " else self._resolve(ch, key)
            if f is None:
                continue
            adv = f.advance(ch) if f.has(ch) else f.upm * 0.3
            total += adv * size / f.upm + ls
        return total - (ls if s else 0)

    def text(self, s: str, x: float, y: float, size: float, key: str = "mono", anchor: str = "start",
             ls: float = 0, attrs: str = "", char_attrs=None) -> str:
        """Glyph-outline text. `char_attrs(i, ch)` adds attributes per glyph."""
        width = self.measure(s, key, size, ls)
        if anchor == "middle":
            x -= width / 2
        elif anchor == "end":
            x -= width
        base = font(key)
        k = size / base.upm
        cur, uses, visible = 0.0, [], 0
        for ch in s:
            f = base if ch == " " else self._resolve(ch, key)
            if f is None:
                continue
            fk = size / f.upm
            if ch != " ":
                gid = self._glyph_id(f, ch)
                extra = char_attrs(visible, ch) if char_attrs else ""
                if f is base:
                    uses.append(f'<use href="#{gid}" x="{cur / k:.1f}"{extra}/>')
                else:  # fallback glyph from another font
                    t = f"translate({cur / k:.1f} 0) scale({fk / k:.4f})"
                    uses.append(f'<use href="#{gid}" transform="{t}"{extra}/>')
                visible += 1
            adv = f.advance(ch) if f.has(ch) else f.upm * 0.3
            cur += adv * fk + ls
        return f'<g transform="translate({x:.1f} {y:.1f}) scale({k:.5f})"{attrs}>{"".join(uses)}</g>'

    def vtext(self, s: str, x: float, y: float, size: float, key: str = "serif", gap: float = 1.08,
              attrs: str = "") -> str:
        """Vertical (tategaki) text: one glyph per line, centred on x, first baseline at y."""
        return "".join(self.text(ch, x, y + i * size * gap, size, key, "middle", attrs=attrs) for i, ch in enumerate(s))

    # -- output ---------------------------------------------------------------
    def render(self) -> str:
        defs = "".join(self._glyphs.values()) + "".join(self.defs)
        css = "".join(self.css) + "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
            f'width="{self.w}" height="{self.h}" role="img" aria-labelledby="t d">'
            f'<title id="t">{self.title}</title><desc id="d">{self.desc}</desc>'
            f"<style>{css}</style><defs>{defs}</defs>{''.join(self.body)}</svg>"
        )

    def save(self, name: str) -> Path:
        ASSETS.mkdir(exist_ok=True)
        out = ASSETS / name
        out.write_text(self.render(), encoding="utf-8")
        print(f"  wrote assets/{name}  ({out.stat().st_size / 1024:.1f} KB)")
        return out


# ---------------------------------------------------------------- helpers
def fill(col: str) -> str:
    return f' fill="{col}"'


def polar(cx: float, cy: float, r: float, deg: float) -> tuple[float, float]:
    a = math.radians(deg - 90)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def smil_steps(total: float, events: list[tuple[float, float]]) -> tuple[str, str]:
    """keyTimes/values for a discrete SMIL animation from (time, value) pairs."""
    events = sorted(events)
    if events[0][0] > 0:
        events.insert(0, (0.0, events[0][1]))
    kt = ";".join(f"{min(t / total, 1):.4f}" for t, _ in events)
    vals = ";".join(f"{v:.1f}" for _, v in events)
    return kt, vals


def stars(rng: random.Random, n: int, w: float, h: float) -> str:
    out = []
    for _ in range(n):
        out.append(
            f'<circle cx="{rng.uniform(0, w):.1f}" cy="{rng.uniform(0, h):.1f}" r="{rng.choice([.5, .7, .9, 1.1])}" '
            f'class="tw" style="animation-duration:{rng.uniform(2.5, 6):.2f}s;animation-delay:-{rng.uniform(0, 6):.2f}s"/>'
        )
    return "".join(out)


STAR_CSS = (f".tw{{fill:{C['kinari']};animation:tw 4s ease-in-out infinite}}"
            "@keyframes tw{0%,100%{opacity:.1}50%{opacity:.8}}")

PETAL = "M0 6C-5 3-5.2-3.6-1.3-6L0-4.2 1.3-6C5.2-3.6 5 3 0 6Z"
PETAL_CSS = (
    ".pt{animation:fall linear infinite both}"
    "@keyframes fall{0%{transform:translate(0,0) rotate(0) scale(1,1);opacity:0}"
    "10%{opacity:var(--o)}50%{transform:translate(calc(var(--dx)*.5),calc(var(--dy)*.5)) rotate(calc(var(--r)*.5)) scale(.35,1)}"
    "90%{opacity:var(--o)}100%{transform:translate(var(--dx),var(--dy)) rotate(var(--r)) scale(1,1);opacity:0}}"
)


def petals(rng: random.Random, n: int, w: float, h: float, colors=None) -> str:
    """Falling petals (sakura / higanbana), drifting down and to the right."""
    colors = colors or [C["acid"], C["kinari"], C["acid"], C["matcha"]]
    out = []
    for _ in range(n):
        x, y = rng.uniform(-80, w), rng.uniform(-40, h * .4)
        s = rng.uniform(.55, 1.25)
        dur = rng.uniform(9, 18)
        style = (f"--dx:{rng.uniform(80, 220):.0f}px;--dy:{h + 60 - y:.0f}px;--r:{rng.choice([-1, 1]) * rng.uniform(200, 540):.0f}deg;"
                 f"--o:{rng.uniform(.45, .9):.2f};animation-duration:{dur:.1f}s;animation-delay:-{rng.uniform(0, dur):.1f}s")
        out.append(f'<g transform="translate({x:.0f} {y:.0f}) scale({s:.2f})"><path d="{PETAL}" '
                   f'fill="{rng.choice(colors)}" class="pt" style="{style}"/></g>')
    return "".join(out)


def seigaiha(d: Doc, x0: float, y0: float, w: float, rows: int, r: float = 18, stroke: str = "#a8b84a",
             bg: str = "#030910", sid: str = "sg") -> str:
    """Rows of 青海波 waves. Returns a group; animate it by one unit width for a seamless drift."""
    arcs = "".join(
        f'<path d="M{-r * f:.1f} 0A{r * f:.1f} {r * f:.1f} 0 0 1 {r * f:.1f} 0" fill="none" stroke="{stroke}" stroke-width="1"/>'
        for f in (1, .74, .48, .22)
    )
    d.defs.append(f'<g id="{sid}"><path d="M{-r} 0A{r} {r} 0 0 1 {r} 0Z" fill="{bg}"/>{arcs}</g>')
    uses = []
    for row in range(rows):
        off = r if row % 2 else 0
        y = y0 + row * r / 2
        x = x0 - 2 * r + off
        while x < x0 + w + 2 * r:
            uses.append(f'<use href="#{sid}" x="{x:.0f}" y="{y:.0f}"/>')
            x += 2 * r
    return "".join(uses)


def brush(rng: random.Random, x0: float, x1: float, yc: float, h: float) -> str:
    """A horizontal brush stroke: pressed start, rough edges, dry-brush tail."""
    n = 36
    top, bot = [], []
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        press = min(1, t / .06) ** .6
        taper = 1 - max(0, (t - .82) / .18) ** 1.6 * .75
        hh = h / 2 * press * taper
        top.append((x, yc - hh + rng.uniform(-.8, .8)))
        bot.append((x, yc + hh + rng.uniform(-.8, .8)))
    pts = top + bot[::-1]
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z"
    return d


def tomoe(cx: float, cy: float, r: float, hc: float = .45, hr: float = .26, sweep: float = 150) -> str:
    """三つ巴 mitsudomoe: round heads near the centre, tails tapering out along the rim.

    Tails trail clockwise from their heads, so spin it counter-clockwise.
    """
    parts = []
    for k in range(3):
        phi = k * 120
        outer, inner = [], []
        for i in range(33):
            t = i / 32
            a = phi + sweep * t
            c = hc + (.93 - hc) * t ** .6
            w = hr * (1 - t) ** 1.2
            outer.append(polar(cx, cy, r * (c + w), a))
            inner.append(polar(cx, cy, r * (c - w), a))
        pts = outer + inner[::-1]
        hx, hy = polar(cx, cy, r * hc, phi)
        rh = r * hr
        parts.append("M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z"
                     f"M{hx - rh:.1f} {hy:.1f}a{rh:.1f} {rh:.1f} 0 1 1 {2 * rh:.1f} 0a{rh:.1f} {rh:.1f} 0 1 1 {-2 * rh:.1f} 0Z")
    return "".join(parts)


def _smooth_closed(pts: list[tuple[float, float]]) -> str:
    """Closed Catmull-Rom curve through pts, as cubic Béziers."""
    n = len(pts)
    d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f"C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}"
    return d + "Z"


def _spline(pts: list[tuple[float, float]], n: int) -> list[tuple[float, float]]:
    """Open Catmull-Rom through pts, sampled at n + 1 points."""
    ext = [pts[0]] + pts + [pts[-1]]
    segs = len(pts) - 1
    out = []
    for k in range(n + 1):
        u = k / n * segs
        i = min(int(u), segs - 1)
        t = u - i
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        out.append(tuple(.5 * (2 * p1[c] + (p2[c] - p0[c]) * t + (2 * p0[c] - 5 * p1[c] + 4 * p2[c] - p3[c]) * t * t
                               + (3 * p1[c] - p0[c] - 3 * p2[c] + p3[c]) * t ** 3) for c in (0, 1)))
    return out


def _digit(base: tuple[float, float], ang: float, lens: list[float], w: float, bends: list[float], n: int = 12) -> str:
    """A finger of three phalanges bent at two joints: a smooth centreline, then a
    width that tapers gently from the knuckle to a rounded fingertip."""
    joints = [base]
    x, y = base
    a = ang
    for k, L in enumerate(lens):
        r = math.radians(a)
        x, y = x + math.cos(r) * L, y + math.sin(r) * L
        joints.append((x, y))
        if k < len(bends):
            a += bends[k]
    c = _spline(joints, n)
    left, right = [], []
    for i, p in enumerate(c):
        q, r = c[min(i + 1, n)], c[max(i - 1, 0)]
        dx, dy = q[0] - r[0], q[1] - r[1]
        L = math.hypot(dx, dy) or 1
        hw = w * (1 - .3 * (i / n) ** 1.6)
        left.append((p[0] - dy / L * hw, p[1] + dx / L * hw))
        right.append((p[0] + dy / L * hw, p[1] - dx / L * hw))
    # round cap: a half circle around the last centreline point
    dx, dy = c[-1][0] - c[-2][0], c[-1][1] - c[-2][1]
    a0 = math.atan2(dy, dx)
    hw = w * .7
    cap = [(c[-1][0] + math.cos(a0 + t) * hw, c[-1][1] + math.sin(a0 + t) * hw)
           for t in (math.pi / 3, math.pi / 6, 0, -math.pi / 6, -math.pi / 3)]
    return _smooth_closed(left + cap + right[::-1])


def hand(rng: random.Random, grip: float = .6) -> str:
    """The Witch's Unseen Hand, as in the anime: a solid silhouette with jointed,
    clawed fingers curling to grasp. Local frame: wrist at (0, 0), reaching +x,
    thumb on the -y side, forearm running far back to -x (off-canvas). `grip`
    (0..1) sets how far the fingers curl. Returns bare <path>s: wrap them in a
    group with a fill and the WITCH_RIM filter, then place it with a transform.
    """
    j = lambda v: v * (1 + rng.uniform(-.06, .06))
    parts = [
        _smooth_closed([(6, -14), (-190, -19), (-620, -24), (-620, 24), (-190, 19), (6, 14)]),     # forearm
        _smooth_closed([(0, -14), (16, -19), (40, -21), (52, -13), (55, -1), (52, 12),
                        (44, 21), (24, 19), (0, 14)]),                                              # back of hand
    ]
    # fingers fan out just enough that their rounded tips stay apart when curled
    for base, ang, lens, w in (((46, -15), -19, (25, 16, 12), 5.2), ((52, -5), -5, (28, 18, 13), 5.5),
                               ((51, 6), 9, (26, 17, 12), 5.2), ((44, 16), 24, (20, 13, 10), 4.6)):
        parts.append(_digit(base, ang + rng.uniform(-2, 2) + 6 * grip, [j(L) for L in lens], w,
                            [j(10 + 34 * grip), j(8 + 26 * grip)]))
    parts.append(_digit((14, -14), -62 + rng.uniform(-4, 4), [18, 14, 10], 6.6,
                        [j(14 + 18 * grip), j(10 + 14 * grip)]))                                   # thumb
    return "".join(f'<path d="{d}"/>' for d in parts)


# Glow for the hands, worked on the union of their parts so no seams show:
# an outer violet halo, a purple inner glow and a pale crisp edge.
WITCH_RIM = (
    '<filter id="wrim" x="-30%" y="-30%" width="160%" height="160%" color-interpolation-filters="sRGB">'
    '<feMorphology in="SourceAlpha" operator="dilate" radius="1.6" result="d"/>'
    '<feFlood flood-color="#b04dff"/><feComposite in2="d" operator="in" result="rim"/>'
    '<feGaussianBlur in="rim" stdDeviation="6" result="glow"/>'
    '<feGaussianBlur in="SourceAlpha" stdDeviation="4" result="sb"/>'
    '<feComposite in="SourceAlpha" in2="sb" operator="out" result="inner"/>'
    '<feFlood flood-color="#8a2be2"/><feComposite in2="inner" operator="in" result="innerc"/>'
    '<feMorphology in="SourceAlpha" operator="erode" radius="1" result="e"/>'
    '<feComposite in="SourceAlpha" in2="e" operator="out" result="edge"/>'
    '<feFlood flood-color="#f6d6ff"/><feComposite in2="edge" operator="in" result="edgec"/>'
    '<feMerge><feMergeNode in="glow"/><feMergeNode in="glow"/><feMergeNode in="rim"/><feMergeNode in="SourceGraphic"/>'
    '<feMergeNode in="innerc"/><feMergeNode in="innerc"/><feMergeNode in="edgec"/></feMerge></filter>'
)


def corners(x: float, y: float, w: float, h: float, col: str, n: float = 14, inset: float = 8) -> str:
    """Gold L-brackets in the four corners of a frame."""
    a, b = x + inset, y + inset
    c, d = x + w - inset, y + h - inset
    p = [f"M{a} {b + n}V{b}H{a + n}", f"M{c - n} {b}H{c}V{b + n}", f"M{c} {d - n}V{d}H{c - n}", f"M{a + n} {d}H{a}V{d - n}"]
    return f'<path d="{"".join(p)}" fill="none" stroke="{col}" stroke-width="1.4"/>'
