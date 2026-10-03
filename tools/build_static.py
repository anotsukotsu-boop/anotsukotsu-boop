"""Builds every hand-animated SVG in assets/ except the live stats card.

    pip install fonttools
    python tools/build_static.py

Art direction: a Japanese night scroll. Sumi ink, vermilion, gold leaf and
washi cream (no purple), Re:Zero's Return by Death told through a wadokei
clock over a red moon, falling petals, the Witch's shadow hands and a 死 seal.
Edit the content block below to change names, skills or tech.
"""

from __future__ import annotations

import base64
import math
import random
from pathlib import Path

from svgkit import (ASSETS, C, PETAL_CSS, ROOT, STAR_CSS, WITCH_RIM, Doc, brush, corners, fill, hand, petals, polar,
                    smil_steps, stars, tomoe)

# ---------------------------------------------------------------- content
PROFILE = {
    "name": "BINTANG ILHAM",
    "kana": "ビンタン・イルハム",
    "tag": "第十號  ·  MATHERS DOMAIN  ·  LUGUNICA",
    "roles": [
        "Return-by-Death Developer",
        "Full-Stack TypeScript Mage",
        "Debugger of Endless Loops",
    ],
    "chips": ["TypeScript", "Node.js", "React", "Next.js", "NestJS", "PostgreSQL"],
}

NEOFETCH = [
    ("User", "Bintangilham10"),
    ("Class", "Return-by-Death Developer"),
    ("Base", "Mathers Domain, Lugunica"),
    ("Status", "Dying & retrying algorithms..."),
    ("Stack", "TypeScript · Node.js · NestJS"),
    ("Front", "React · Next.js"),
    ("Data", "PostgreSQL · Docker"),
    ("Interests", "System Architecture, Re:Zero"),
    ("Power", "Ctrl+Z (Return by Death), Shamac"),
    ("Motto", '"I will debug you, no matter how many times it takes!"'),
]

# (kanji, sin, colour, skill, level 0-100, flavour)
SINS = [
    ("強欲", "GREED", C["acid"], "TypeScript · NestJS", 80, "wants every type. strictly."),
    ("傲慢", "PRIDE", C["gin"], "React · Next.js", 75, "renders nothing less than perfect."),
    ("暴食", "GLUTTONY", C["kaki"], "Node.js · PostgreSQL", 70, "devours queries by the million."),
    ("怠惰", "SLOTH", C["matcha"], "Debugging at 4 AM", 90, "the Unseen Hand fixes it... eventually."),
    ("憤怒", "WRATH", C["shu"], "Merge Conflicts", 100, "resolved by force. every single time."),
    ("色欲", "LUST", C["sakura"], "UI · CSS Motion", 65, "metamorphosis via transform()."),
    ("嫉妬", "ENVY", "#5d6f66", "System Architecture", 40, "sealed. the witch is still studying it."),
]

# (label, badge kind)
INNER_SPIRITS = [("TypeScript", "ts"), ("JavaScript", "js"), ("React", "react"), ("Next.js", "next")]
OUTER_SPIRITS = [("Node.js", "node"), ("NestJS", "nest"), ("PostgreSQL", "pg"), ("Docker", "docker"), ("Python", "py")]

HEADERS = {
    "header-status.svg": ("壱", "ステータス画面", "STATUS WINDOW"),
    "header-archive.svg": ("弐", "魔女教  大罪司教", "WITCH CULT ARCHIVE"),
    "header-spirits.svg": ("参", "精霊術  契約", "SPIRIT CONTRACTS"),
    "header-records.svg": ("肆", "ループ記録", "LOOP RECORDS"),
    "header-loop.svg": ("伍", "現在のループ", "CURRENT LOOP"),
}

# Headers and the divider are transparent, so they ship a dark and a light tone
# (README picks one with <picture>); acid yellow would vanish on a white page.
INK = {
    "dark": {"lo": C["acid-d"], "mid": C["acid"], "hi": "#f4fbb8", "brush": C["acid-d"], "mark": C["neon"]},
    "light": {"lo": "#2f6b1a", "mid": "#4f8a1a", "hi": "#86b22a", "brush": "#6b7d1a", "mark": "#169a3f"},
}

# Only the hero is a card. Everything below it is drawn straight onto the page,
# and small text cannot clear both a white and a dark page in one colour — so
# each of those sections ships a dark and a light variant, and the README picks
# between them with <picture>.
TONE = {
    "dark": {
        "ink": C["kinari"], "dim": C["muted"], "rule": "#2c4c42", "chip": "#08140f",
        "track": "#16302a", "star": C["kinari"], "shadow": ".55", "ghost": .24,
        "neon": C["neon"], "acid": C["acid"], "acid-hi": "#f4fbb8", "shu": C["shu"],
        "seal-a": "#16863a", "seal-b": C["ai"],
        "petals": [C["acid"], C["kinari"], C["acid"], C["matcha"]],
        "sin": {"GREED": C["acid"], "PRIDE": C["gin"], "GLUTTONY": C["kaki"], "SLOTH": C["matcha"],
                "WRATH": C["shu"], "LUST": C["sakura"], "ENVY": "#5d6f66"},
    },
    "light": {
        "ink": "#16231d", "dim": "#5a6b63", "rule": "#c2d0c9", "chip": "#f2f6f1",
        "track": "#dde5e0", "star": "#9aad a3".replace(" ", ""), "shadow": ".3", "ghost": .16,
        "neon": "#11823a", "acid": "#6f7d16", "acid-hi": "#9bad2a", "shu": "#c42a1f",
        "seal-a": "#15763a", "seal-b": "#1b5f55",
        "petals": ["#8a9a3a", "#9aad a3".replace(" ", ""), "#8a9a3a", "#3f9e5c"],
        "sin": {"GREED": "#8a7a12", "PRIDE": "#5c6b73", "GLUTTONY": "#b2541b", "SLOTH": "#1f8a3f",
                "WRATH": "#c42a1f", "LUST": "#b8537a", "ENVY": "#78867e"},
    },
}


def out_name(name: str, tone: str) -> str:
    return name if tone == "dark" else name.replace(".svg", "-light.svg")


ZODIAC = "子丑寅卯辰巳午未申酉戌亥"
KANJI_NUM = "〇一二三四五六七八九十"


def pct(t: float, total: float) -> str:
    return f"{t / total * 100:.2f}%"


def card(d: Doc, x: float, y: float, w: float, h: float, rx: float = 14, cid: str = "card") -> None:
    """Rounded clip for the hero — the one section that stays a framed card."""
    d.defs.append(f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/></clipPath>')


def rough_filter(fid: str, scale: float = 2.2) -> str:
    """Ink-bleed edge for seals."""
    return (f'<filter id="{fid}" x="-10%" y="-10%" width="120%" height="120%">'
            f'<feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="4"/>'
            f'<feDisplacementMap in="SourceGraphic" scale="{scale}"/></filter>')


def seal(d: Doc, ch: str, size: float, key: str = "serif", col: str = C["shu"], ink: str = C["kinari"]) -> str:
    """A square vermilion hanko centred on (0, 0)."""
    h = size / 2
    return (f'<rect x="{-h}" y="{-h}" width="{size}" height="{size}" rx="{size * .12:.1f}" fill="{col}"/>'
            f'<rect x="{-h + size * .09:.1f}" y="{-h + size * .09:.1f}" width="{size * .82:.1f}" height="{size * .82:.1f}" '
            f'rx="{size * .07:.1f}" fill="none" stroke="{ink}" stroke-width="{max(size * .025, .8):.1f}"/>'
            + d.text(ch, 0, size * .25, size * .62, key, "middle", attrs=fill(ink)))


# ====================================================================== HERO
# Subaru's endless staircase, looping behind the hero. The HD video is cut once
# into a cover-cropped animated WebP (assets/bg/, committed) and embedded,
# because an SVG shown as an <img> may not load external files.
BG_WEBP = ASSETS / "bg" / "subaru-stairs.webp"
BG_VIDEO = ROOT / "rezero-readme" / "assets" / "subaru-stairs_processed.mp4"
BG_FPS, BG_QUALITY = 12, 40
WITCH = {"body": "#07030b", "rim": "#a93dff", "haze": "#6a0dad"}
GIF_TONE = {"night": C["sumi0"], "neon": C["neon"], "acid": C["acid"], "teal": "#1c5a52", "mist": C["muted"]}


def cut_background(w: int, h: int) -> None:
    """Video -> animated WebP at the card's size. Needs `pip install imageio-ffmpeg pillow`."""
    import subprocess
    import tempfile

    import imageio_ffmpeg
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-i", str(BG_VIDEO),
             "-vf", f"crop=iw:iw*{h}/{w},scale={w}:-2:flags=lanczos,fps={BG_FPS}", f"{tmp}/%04d.png"],
            check=True,
        )
        frames = [Image.open(f).convert("RGB") for f in sorted(Path(tmp).glob("*.png"))]
    BG_WEBP.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(BG_WEBP, "WEBP", save_all=True, append_images=frames[1:], duration=round(1000 / BG_FPS),
                   loop=0, quality=BG_QUALITY, method=4)
    print(f"  cut {BG_WEBP.relative_to(ROOT)} ({BG_WEBP.stat().st_size / 1024:.0f} KB, {len(frames)} frames)")


def hero_background(w: int, h: int) -> str:
    if not BG_WEBP.exists():
        cut_background(w, h)
    b64 = base64.b64encode(BG_WEBP.read_bytes()).decode()
    return (f'<image href="data:image/webp;base64,{b64}" x="0" y="0" width="{w}" height="{h}" '
            f'preserveAspectRatio="xMidYMid slice"/>')


def hero() -> None:
    W, H, T = 1000, 380, 8.0
    DIE, BACK = 74, 90  # % of the loop: death, checkpoint restored
    CX, CY, MR = 212, 184, 112
    G = GIF_TONE
    rng = random.Random(10)
    d = Doc(W, H, "Bintang Ilham — Return-by-Death Developer",
            "Subaru climbs an endless staircase behind a ghostly wadokei clock; the Witch's hands rise, a 死 seal lands, time rewinds and the loop counter goes up.")
    card(d, 0, 0, W, H)
    d.defs.append(
        '<linearGradient id="shade" x1="0" x2="1">'
        f'<stop offset="0" stop-color="{G["night"]}" stop-opacity=".3"/><stop offset=".35" stop-color="{G["night"]}" stop-opacity=".12"/>'
        f'<stop offset=".6" stop-color="{G["night"]}" stop-opacity=".38"/><stop offset="1" stop-color="{G["night"]}" stop-opacity=".6"/></linearGradient>'
        f'<radialGradient id="backdrop"><stop offset="0" stop-color="{G["night"]}" stop-opacity=".62"/>'
        f'<stop offset=".7" stop-color="{G["night"]}" stop-opacity=".3"/><stop offset="1" stop-color="{G["night"]}" stop-opacity="0"/></radialGradient>'
        '<filter id="ts" x="-5%" y="-20%" width="110%" height="140%"><feDropShadow dx="0" dy="1.2" stdDeviation="2.6" '
        'flood-color="#000" flood-opacity=".9"/></filter>'
        '<linearGradient id="vfade" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{G["night"]}" stop-opacity=".55"/><stop offset=".22" stop-color="{G["night"]}" stop-opacity="0"/>'
        f'<stop offset=".8" stop-color="{G["night"]}" stop-opacity="0"/><stop offset="1" stop-color="{G["night"]}" stop-opacity=".7"/></linearGradient>'
        f'<radialGradient id="halo"><stop offset="0" stop-color="{G["neon"]}" stop-opacity=".22"/>'
        f'<stop offset=".55" stop-color="{G["neon"]}" stop-opacity=".05"/><stop offset="1" stop-color="{G["neon"]}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="face" cx="45%" cy="38%" r="70%"><stop offset="0" stop-color="#0b2420" stop-opacity=".55"/>'
        f'<stop offset="1" stop-color="{G["night"]}" stop-opacity=".72"/></radialGradient>'
        '<radialGradient id="vig" r="72%"><stop offset=".5" stop-color="#3b0703" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#3b0703" stop-opacity=".9"/></radialGradient>'
        '<linearGradient id="metal" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fbffe8"/>'
        f'<stop offset=".55" stop-color="#e9efc4"/><stop offset="1" stop-color="{G["acid"]}"/></linearGradient>'
        f'<linearGradient id="bar" x1="0" x2="1"><stop offset="0" stop-color="{G["neon"]}"/><stop offset="1" stop-color="{G["acid"]}"/></linearGradient>'
        '<linearGradient id="shine" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset=".5" stop-color="#fbffe8" stop-opacity=".95"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        + rough_filter("rough", 3)
    )

    NX, NY = 452, 168
    size = 54.0
    while d.measure(PROFILE["name"], "serif", size, 4) > 470:
        size -= 1
    name_w = d.measure(PROFILE["name"], "serif", size, 4)
    k = size / 1000
    d.defs.append(
        f'<mask id="nmask" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
        + d.text(PROFILE["name"], NX, NY, size, "serif", ls=4, attrs=' fill="#fff"') + "</mask>"
    )

    d.css.append(PETAL_CSS)
    d.css.append(
        f"""
.halo{{transform-origin:{CX}px {CY}px;animation:halo 6s ease-in-out infinite}}
@keyframes halo{{50%{{transform:scale(1.08);opacity:.6}}}}
.spin{{transform-origin:{CX}px {CY}px;animation:spin 120s linear infinite}}
.spin-r{{transform-origin:{CX}px {CY}px;animation:spin 60s linear infinite reverse}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.hand-c{{transform-origin:{CX}px {CY}px;animation-duration:{T}s;animation-iteration-count:infinite}}
.h-s{{animation-name:hs}}
@keyframes hs{{0%{{transform:rotate(0);animation-timing-function:steps(12,end)}}72%{{transform:rotate(360deg)}}
76%{{transform:rotate(360deg);animation-timing-function:cubic-bezier(.7,0,.2,1)}}{BACK}%,100%{{transform:rotate(-720deg)}}}}
.h-m{{animation-name:hm}}
@keyframes hm{{0%{{transform:rotate(0);animation-timing-function:linear}}72%,76%{{transform:rotate(30deg);animation-timing-function:cubic-bezier(.7,0,.2,1)}}{BACK}%,100%{{transform:rotate(-360deg)}}}}
.h-h{{animation-name:hh}}
@keyframes hh{{0%{{transform:rotate(300deg);animation-timing-function:linear}}72%,76%{{transform:rotate(305deg);animation-timing-function:cubic-bezier(.7,0,.2,1)}}{BACK}%,100%{{transform:rotate(-60deg)}}}}

.nm use{{stroke-dasharray:1;animation:draw 2.8s cubic-bezier(.6,.1,.2,1) both}}
@keyframes draw{{0%{{stroke-dashoffset:1;fill-opacity:0}}62%{{stroke-dashoffset:0;fill-opacity:0}}100%{{stroke-dashoffset:0;fill-opacity:1}}}}
.kana use{{animation:kana .7s ease both}}
@keyframes kana{{from{{opacity:0;transform:translateY(-8px)}}}}
.shine{{animation:shine {T}s infinite}}
@keyframes shine{{0%,18%{{transform:translateX(0)}}34%,100%{{transform:translateX({name_w + 200:.0f}px)}}}}

.jit{{animation:jit {T}s infinite}}
@keyframes jit{{0%,{DIE}%{{transform:none}}{DIE + 1}%{{transform:translate(-6px,1px)}}{DIE + 2}%{{transform:translate(5px,-2px)}}
{DIE + 3}%{{transform:translate(-3px,0)}}{DIE + 4}%{{transform:translate(3px,1px)}}{DIE + 5}%{{transform:none}}
{BACK - 3}%{{transform:translate(-2px,0)}}{BACK - 2}%{{transform:translate(3px,0)}}{BACK - 1}%,100%{{transform:none}}}}
.gl{{opacity:0;animation:gl {T}s steps(1,end) infinite}}
@keyframes gl{{0%,{DIE}%{{opacity:0;transform:none}}{DIE + .5}%{{opacity:.8;transform:translate(-6px,0)}}
{DIE + 2}%{{opacity:.55;transform:translate(4px,0)}}{DIE + 4}%{{opacity:0}}{DIE + 6}%{{opacity:.7;transform:translate(-3px,0)}}
{DIE + 7}%{{opacity:0}}{BACK - 3}%{{opacity:.8;transform:translate(5px,0)}}{BACK - 1}%,100%{{opacity:0;transform:none}}}}
.gl.b{{animation-delay:-.06s}}

.st-a{{animation:sta {T}s infinite}}
@keyframes sta{{0%,{DIE - .1}%{{opacity:1}}{DIE}%,100%{{opacity:0}}}}
.st-d{{opacity:0;animation:std {T}s infinite}}
@keyframes std{{0%,{DIE - .1}%{{opacity:0}}{DIE}%,{BACK - .1}%{{opacity:1}}{BACK}%,100%{{opacity:0}}}}
.st-r{{opacity:0;animation:str {T}s infinite}}
@keyframes str{{0%,{BACK - .1}%{{opacity:0}}{BACK}%,100%{{opacity:1}}}}
.pulse{{animation:pulse 1.4s ease-in-out infinite}}
@keyframes pulse{{50%{{opacity:.3}}}}
.caret{{animation:blink 1s steps(1,end) infinite}}
@keyframes blink{{50%{{opacity:0}}}}

.wr{{opacity:0;animation:wr {T}s infinite}}
@keyframes wr{{0%,{DIE - .5}%{{opacity:0;transform:translateX(var(--r))}}{DIE + 2.5}%{{opacity:1;transform:translateX(6px)}}
{DIE + 5}%{{transform:translateX(0)}}{DIE + 10}%{{transform:translateX(-5px)}}{BACK - 1}%{{opacity:1;transform:translateX(0)}}
{BACK + 3}%,100%{{opacity:0;transform:translateX(var(--r))}}}}
.stamp{{opacity:0;animation:stamp {T}s infinite}}
@keyframes stamp{{0%,{DIE + .4}%{{opacity:0;transform:scale(2.4)}}{DIE + 1.4}%{{opacity:1;transform:scale(.9)}}
{DIE + 2.4}%{{transform:scale(1)}}{BACK - 1.5}%{{opacity:1;transform:scale(1)}}{BACK}%,100%{{opacity:0;transform:scale(1.08)}}}}
.flash{{opacity:0;animation:flash {T}s infinite}}
@keyframes flash{{0%,{DIE - .3}%{{opacity:0}}{DIE + .3}%{{opacity:.42}}{DIE + 4}%{{opacity:.12}}{BACK - 2}%,100%{{opacity:0}}}}
.vig{{opacity:0;animation:vig {T}s infinite}}
@keyframes vig{{0%,{DIE - .3}%{{opacity:0}}{DIE + 1}%{{opacity:1}}{BACK - 3}%{{opacity:.75}}{BACK}%,100%{{opacity:0}}}}
.rew{{opacity:0;animation:rew {T}s infinite}}
@keyframes rew{{0%,{DIE + 3}%{{opacity:0}}{DIE + 4}%,{BACK - 1}%{{opacity:1}}{BACK}%,100%{{opacity:0}}}}
.white{{opacity:0;animation:white {T}s infinite}}
@keyframes white{{0%,{BACK - .4}%{{opacity:0}}{BACK + .4}%{{opacity:.3}}{BACK + 6}%,100%{{opacity:0}}}}
.jp{{opacity:.6;animation:jp {T}s infinite}}
@keyframes jp{{0%,{DIE}%{{opacity:.6}}{DIE + .4}%{{opacity:1}}{DIE + 2}%{{opacity:.3}}{DIE + 3}%{{opacity:1}}{BACK}%{{opacity:.9}}{BACK + 3}%,100%{{opacity:.6}}}}
.prog{{transform-box:fill-box;transform-origin:0 0;animation:prog {T}s infinite}}
@keyframes prog{{0%{{transform:scaleX(0);animation-timing-function:linear}}{DIE}%,{BACK}%{{transform:scaleX(1)}}100%{{transform:scaleX(0)}}}}
.one{{animation:roll1 {10 * T}s steps(10,end) infinite;animation-delay:-{T - T * BACK / 100:.2f}s}}
@keyframes roll1{{to{{transform:translateY(-260px)}}}}
.ten{{animation:roll1 {100 * T}s steps(10,end) infinite;animation-delay:-{100 * T / 10 - (T * BACK / 100 + T * 2):.2f}s}}
.chip{{animation:chip .7s cubic-bezier(.2,.9,.3,1.2) both}}
@keyframes chip{{from{{opacity:0;transform:translateY(10px)}}}}
"""
    )

    b = d.body.append
    b('<g clip-path="url(#card)">')
    b(f'<rect width="{W}" height="{H}" fill="{G["night"]}"/>')
    b(hero_background(W, H))
    b(f'<rect width="{W}" height="{H}" fill="url(#shade)"/><rect width="{W}" height="{H}" fill="url(#vfade)"/>')
    b(f'<circle cx="{CX}" cy="{CY}" r="200" fill="url(#halo)" class="halo"/>')
    b(f'<ellipse cx="690" cy="190" rx="360" ry="170" fill="url(#backdrop)"/>')

    b('<g class="jit">')
    # -- a ghostly wadokei floating over the stairs --------------------------
    ring = "ゼロから始める異世界生活・死に戻り・" * 4
    step = 360 / len(ring)
    b(f'<g class="spin" fill="{G["acid"]}" fill-opacity=".8">')
    for i, ch in enumerate(ring):
        b(f'<g transform="rotate({i * step:.2f} {CX} {CY})">{d.text(ch, CX, CY - MR - 30, 9.5, "serif-md", "middle")}</g>')
    b("</g>")
    b(f'<circle cx="{CX}" cy="{CY}" r="{MR + 22}" fill="none" stroke="{G["acid"]}" stroke-opacity=".5"/>')
    b(f'<circle cx="{CX}" cy="{CY}" r="{MR + 16}" fill="none" stroke="{G["neon"]}" stroke-opacity=".6" stroke-dasharray="1 5" class="spin-r"/>')
    b(f'<circle cx="{CX}" cy="{CY}" r="{MR}" fill="url(#face)" stroke="{G["neon"]}" stroke-opacity=".55" stroke-width="1.2"/>')
    ticks = []
    for i in range(60):
        major = i % 5 == 0
        x1, y1 = polar(CX, CY, MR - (12 if major else 7), i * 6)
        x2, y2 = polar(CX, CY, MR - 3, i * 6)
        ticks.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{G["acid"] if major else G["neon"]}" '
                     f'stroke-width="{1.6 if major else .8}" stroke-opacity="{.95 if major else .45}"/>')
    b("".join(ticks))
    b(f'<circle cx="{CX}" cy="{CY}" r="{MR - 44}" fill="none" stroke="{G["neon"]}" stroke-opacity=".25"/>')
    for i, ch in enumerate(ZODIAC):
        x, y = polar(CX, CY, MR - 28, i * 30)
        b(d.text(ch, x, y + 6, 16, "serif", "middle", attrs=fill(G["acid"])))
    b(f'<g class="hand-c h-h"><polygon points="{CX - 4},{CY + 10} {CX - 2.2},{CY - 42} {CX},{CY - 52} {CX + 2.2},{CY - 42} {CX + 4},{CY + 10}" fill="{C["kinari"]}"/></g>')
    b(f'<g class="hand-c h-m"><polygon points="{CX - 2.8},{CY + 14} {CX - 1.4},{CY - 70} {CX},{CY - 80} {CX + 1.4},{CY - 70} {CX + 2.8},{CY + 14}" fill="{C["kinari"]}"/></g>')
    b(f'<g class="hand-c h-s"><line x1="{CX}" y1="{CY + 22}" x2="{CX}" y2="{CY - 96}" stroke="{G["neon"]}" stroke-width="1.6" stroke-linecap="round"/>'
      f'<circle cx="{CX}" cy="{CY + 16}" r="4" fill="{G["neon"]}"/></g>')
    b(f'<circle cx="{CX}" cy="{CY}" r="6.5" fill="{G["acid"]}"/><circle cx="{CX}" cy="{CY}" r="2.4" fill="{G["night"]}"/>')

    # -- name block (drop shadow keeps it legible over the moving scene) ----------------
    b('<g filter="url(#ts)">')
    b(d.text(PROFILE["tag"], NX, 72, 10.5, "mono", ls=2.2, attrs=fill("#b4c9bd")))
    b(d.text(PROFILE["kana"], NX, 108, 17, "serif", ls=7, attrs=f' class="kana"{fill(G["acid"])}',
             char_attrs=lambda i, ch: f' style="animation-delay:{.1 + i * .07:.2f}s"'))
    b(d.text(PROFILE["name"], NX, NY, size, "serif", ls=4, attrs=f' class="gl"{fill(C["shu"])}'))
    b(d.text(PROFILE["name"], NX, NY, size, "serif", ls=4, attrs=f' class="gl b"{fill(G["neon"])}'))
    b(d.text(PROFILE["name"], NX, NY, size, "serif", ls=4,
             attrs=f' class="nm" fill="url(#metal)" stroke="#fbffe8" stroke-width="{1 / k:.0f}"',
             char_attrs=lambda i, ch: f' style="animation-delay:{.5 + i * .09:.2f}s"'))
    b(f'<g mask="url(#nmask)"><polygon class="shine" points="{NX - 150},{NY - 60} {NX - 110},{NY - 60} {NX - 150},{NY + 20} {NX - 190},{NY + 20}" fill="url(#shine)"/></g>')
    b(f'<rect x="{NX}" y="186" width="56" height="2" fill="{G["acid"]}"/><rect x="{NX + 62}" y="184" width="6" height="6" fill="{C["shu"]}" transform="rotate(45 {NX + 65} 187)"/>')

    RY, RS = 222, 18
    cw = RS * 0.6
    b(d.text("›", NX, RY, RS, "mono-b", attrs=fill(G["neon"])))
    rx0 = NX + cw * 2
    TT = T * len(PROFILE["roles"])
    caret = []
    for i, role in enumerate(PROFILE["roles"]):
        t0 = i * T + 0.35
        ev = [(0, 0)] + [(t0 + n * 0.05, n * cw) for n in range(1, len(role) + 1)] + [(i * T + T * BACK / 100, 0)]
        caret += [(t0 + n * 0.05, rx0 + n * cw) for n in range(0, len(role) + 1)] + [(i * T + T * BACK / 100, rx0)]
        kt, vals = smil_steps(TT, ev)
        d.defs.append(
            f'<clipPath id="role{i}"><rect x="{rx0}" y="{RY - 22}" width="0" height="30">'
            f'<animate attributeName="width" dur="{TT}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{kt}" values="{vals}"/>'
            "</rect></clipPath>")
        b(f'<g clip-path="url(#role{i})">{d.text(role, rx0, RY, RS, "mono", attrs=fill("#eef3dc"))}</g>')
    kt, vals = smil_steps(TT, caret)
    b(f'<rect class="caret" x="{rx0}" y="{RY - 15}" width="{cw * .9:.1f}" height="19" fill="{G["acid"]}">'
      f'<animate attributeName="x" dur="{TT}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{kt}" values="{vals}"/></rect>')

    SY = 258
    b(f'<g class="st-a"><circle cx="{NX + 5}" cy="{SY - 4}" r="4" fill="{G["neon"]}" class="pulse"/>'
      + d.text("生存 ALIVE", NX + 17, SY, 12.5, "mono-b", ls=1.5, attrs=fill(G["neon"]))
      + d.text("·  checkpoint saved", NX + 118, SY, 12, "mono", attrs=fill(G["mist"])) + "</g>")
    b('<g class="st-d">' + d.text("✕ 死亡 DEAD", NX, SY, 12.5, "mono-b", ls=1.5, attrs=fill(C["shu"]))
      + d.text("·  return_by_death() triggered", NX + 118, SY, 12, "mono", attrs=fill(C["sakura"])) + "</g>")
    b('<g class="st-r">' + d.text("◆ 復帰 RESTORED", NX, SY, 12.5, "mono-b", ls=1.5, attrs=fill(G["acid"]))
      + d.text("·  back to the checkpoint, loop +1", NX + 140, SY, 12, "mono", attrs=fill(G["mist"])) + "</g>")

    x = NX
    for i, chip in enumerate(PROFILE["chips"]):
        w = d.measure(chip, "mono", 11.5) + 22
        b(f'<g class="chip" style="animation-delay:{1.8 + i * .12:.2f}s">'
          f'<rect x="{x}" y="284" width="{w:.1f}" height="25" rx="3" fill="{G["night"]}" fill-opacity=".8" stroke="{G["acid"]}" stroke-opacity=".5"/>'
          + d.text(chip, x + 11, 300.5, 11.5, "mono", attrs=fill("#eef3dc")) + "</g>")
        x += w + 8
    b("</g>")  # /shadow
    b("</g>")  # /jit

    b(petals(rng, 14, W, H, [G["acid"], C["kinari"], G["acid"]]))

    # vertical 死に戻り and loop seal
    b(f'<g filter="url(#ts)"><g class="jp">{d.vtext("死に戻り", 968, 112, 27, "brush", 1.2, attrs=fill(C["shu"]))}</g>'
      + d.vtext("ゼロから始める", 938, 118, 10.5, "serif-md", 1.35, attrs=f'{fill(G["acid"])} fill-opacity=".8"') + "</g>")
    b(f'<g filter="url(#rough)"><rect x="848" y="22" width="122" height="40" rx="4" fill="{C["shu"]}"/>'
      f'<rect x="852" y="26" width="114" height="32" rx="2" fill="none" stroke="{C["kinari"]}" stroke-opacity=".7"/></g>')
    b(d.text("ループ", 862, 47, 11, "serif", ls=1, attrs=fill(C["kinari"])))
    dw = max(d.measure(str(n), "serif", 20) for n in range(10))
    b(d.text("0", 912, 49, 20, "serif", attrs=fill(C["kinari"])))
    for cls, x0, start in (("ten", 912 + dw + 1, 4), ("one", 912 + 2 * (dw + 1), 7)):
        d.defs.append(f'<clipPath id="w-{cls}"><rect x="{x0 - 1:.1f}" y="30" width="{dw + 2:.1f}" height="25"/></clipPath>')
        digits = "".join(d.text(str((start + n) % 10), x0, 49 + n * 26, 20, "serif") for n in range(10))
        b(f'<g clip-path="url(#w-{cls})"><g class="{cls}" fill="{C["kinari"]}">{digits}</g></g>')

    # -- death: the Witch's hands, the seal, the rewind ----------------------------------
    b(f'<rect width="{W}" height="{H}" fill="{C["shu"]}" class="flash"/>')
    b(f'<rect width="{W}" height="{H}" fill="url(#vig)" class="vig"/>')

    # The Witch's Unseen Hands reach in from the card's edges toward the clock and
    # the seal: solid silhouettes with clawed fingers, a violet rim and miasma.
    d.defs.append(WITCH_RIM + '<filter id="miasma" x="-60%" y="-60%" width="220%" height="220%">'
                  '<feGaussianBlur stdDeviation="14"/></filter>')
    # The wrist sits just inside the card, near an edge or corner; `ang` points
    # the fingers inward (toward the clock, name or seal) with the forearm
    # trailing the opposite way, straight out through that nearby edge — so a
    # clean stretch of arm is always visible between the wrist and the frame.
    # (wrist x, wrist y, angle, scale, mirrored, grip, reach distance in local units)
    for i, (hx, hy, ang, sc, mir, grip, reach) in enumerate((
            (50, 330, -45, 1.45, False, .5, 110),   # bottom-left corner → up toward the clock
            (42, 110, 0, 1.1, True, .7, 90),        # left edge → right toward the clock/name
            (480, 332, -90, 1.3, False, .65, 95),   # bottom edge → up toward the tags
            (935, 48, 135, 1.45, True, .55, 110),   # top-right corner → down-left toward the name
            (630, 42, 90, 1.1, False, .75, 90),     # top edge → down toward the tags
            (935, 332, -135, 1.1, True, .6, 90))):  # bottom-right corner → up-left toward the seal
        haze = (f'<g filter="url(#miasma)" opacity=".55"><ellipse cx="20" cy="0" rx="70" ry="34" fill="{WITCH["haze"]}"/>'
                f'<ellipse cx="62" cy="0" rx="30" ry="26" fill="{WITCH["rim"]}" opacity=".5"/></g>')
        b(f'<g transform="translate({hx} {hy}) rotate({ang}) scale({sc} {-sc if mir else sc})">'
          f'<g class="wr" style="--r:-{reach}px;animation-delay:{i * .05:.2f}s">{haze}'
          f'<g filter="url(#wrim)" fill="{WITCH["body"]}">{hand(rng, grip)}</g></g></g>')
    b(f'<g transform="translate(712 176) rotate(-9)"><g class="stamp"><g filter="url(#rough)">{seal(d, "死", 108, "brush")}</g></g></g>')
    b(f'<g class="rew"><rect width="{W}" height="{H}" fill="{G["neon"]}" fill-opacity=".05"/>'
      f'<rect x="22" y="336" width="186" height="26" rx="3" fill="{G["night"]}" fill-opacity=".85" stroke="{G["acid"]}" stroke-opacity=".5"/>'
      + d.text("«« 巻き戻し  REWIND", 34, 354, 12, "mono-b", ls=1.5, attrs=fill("#eef3dc")) + "</g>")
    b(f'<rect width="{W}" height="{H}" fill="#eef3dc" class="white"/>')
    b(f'<rect x="0" y="{H - 3}" width="{W}" height="3" fill="#0b1a16"/>')
    b(f'<rect x="0" y="{H - 3}" width="{W}" height="3" fill="url(#bar)" class="prog"/>')
    b("</g>")
    b(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="none" stroke="{G["acid"]}" stroke-opacity=".45"/>'
      + corners(0, 0, W, H, G["acid"]))
    d.save("hero.svg")


# ================================================================== DIVIDER
def divider(tone: str = "dark") -> None:
    ink = INK[tone]
    W, H = 1000, 40
    rng = random.Random(2)
    d = Doc(W, H, "divider", "A brush-stroke divider with a turning mitsudomoe.")
    d.css.append(
        """
.run{animation:run 3.4s cubic-bezier(.5,0,.5,1) infinite}
@keyframes run{0%{transform:translateX(0);opacity:0}15%{opacity:1}85%{opacity:1}100%{transform:translateX(var(--d));opacity:0}}
.tomoe{transform-origin:500px 20px;animation:spin 8s linear infinite reverse}
@keyframes spin{to{transform:rotate(360deg)}}
.ring{transform-origin:500px 20px;animation:spin 14s linear infinite}
"""
    )
    b = d.body.append
    b(f'<path d="{brush(rng, 0, 414, 20, 3.2)}" fill="{ink["brush"]}" transform="translate(474 0) scale(-1 1)" opacity=".85"/>')
    b(f'<path d="{brush(rng, 526, 940, 20, 3.2)}" fill="{ink["brush"]}" opacity=".85"/>')
    b(f'<circle cx="474" cy="20" r="2.4" fill="{ink["mark"]}" class="run" style="--d:-400px"/>')
    b(f'<circle cx="526" cy="20" r="2.4" fill="{ink["mark"]}" class="run" style="--d:400px"/>')
    b(f'<circle cx="500" cy="20" r="13" fill="none" stroke="{ink["brush"]}" stroke-width="1.2" stroke-dasharray="2 3" class="ring"/>')
    b(f'<path d="{tomoe(500, 20, 8.5)}" fill="{ink["mark"]}" class="tomoe"/>')
    d.save("divider.svg" if tone == "dark" else "divider-light.svg")


# =========================================================== SECTION HEADERS
def header(file: str, num: str, jp: str, title: str, tone: str = "dark") -> None:
    ink = INK[tone]
    W, H = 1000, 96
    rng = random.Random(len(title))
    d = Doc(W, H, title.title(), f"Section title: {title}")
    size, ls, hs, gap = 26, 6, 40, 20
    tw = d.measure(title, "serif", size, ls)
    x0 = 500 - (hs + gap + tw) / 2
    tx = x0 + hs + gap
    k = size / 1000
    d.defs.append(
        f'<linearGradient id="g" gradientUnits="userSpaceOnUse" x1="{tx - 150:.0f}" x2="{tx + tw + 150:.0f}" spreadMethod="reflect">'
        f'<stop offset="0" stop-color="{ink["lo"]}"/><stop offset=".4" stop-color="{ink["mid"]}"/>'
        f'<stop offset=".5" stop-color="{ink["hi"]}"/><stop offset=".6" stop-color="{ink["mid"]}"/><stop offset="1" stop-color="{ink["lo"]}"/>'
        f'<animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="{tw + 300:.0f} 0" dur="6s" repeatCount="indefinite"/>'
        "</linearGradient>"
        f'<mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
        + d.text(title, tx, 70, size, "serif", ls=ls, attrs=' fill="#fff"') + "</mask>"
        + rough_filter("rough", 1.6)
        + f'<clipPath id="u"><rect x="{tx}" y="74" width="0" height="12">'
          f'<animate attributeName="width" from="0" to="{tw + 30:.0f}" begin=".7s" dur="1s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".3 0 .2 1"/></rect></clipPath>'
    )
    d.css.append(
        """
.st use{stroke-dasharray:1;animation:draw 2s cubic-bezier(.6,.1,.2,1) both}
@keyframes draw{0%{stroke-dashoffset:1;opacity:1}70%{stroke-dashoffset:0;opacity:1}100%{stroke-dashoffset:0;opacity:0}}
.fill{animation:fill 2s ease both}
@keyframes fill{0%,55%{opacity:0}100%{opacity:1}}
.seal{animation:seal .55s .15s cubic-bezier(.3,1.6,.5,1) both}
@keyframes seal{from{opacity:0;transform:scale(1.9)}}
.jp use{animation:jp .6s ease both}
@keyframes jp{from{opacity:0}}
"""
    )
    b = d.body.append
    b(f'<g transform="translate({x0 + hs / 2:.1f} 56) rotate(-4)"><g class="seal"><g filter="url(#rough)">{seal(d, num, hs)}</g></g></g>')
    b(d.text(jp, tx, 38, 12.5, "serif-md", ls=5, attrs=f' class="jp"{fill(C["shu"])}',
             char_attrs=lambda i, ch: f' style="animation-delay:{.3 + i * .06:.2f}s"'))
    b(d.text(title, tx, 70, size, "serif", ls=ls,
             attrs=f' class="st" fill="none" stroke="{ink["mid"]}" stroke-width="{.9 / k:.0f}"',
             char_attrs=lambda i, ch: f' style="animation-delay:{i * .05:.2f}s"'))
    b(f'<g mask="url(#m)" class="fill"><rect x="0" y="30" width="{W}" height="50" fill="url(#g)"/></g>')
    b(f'<g clip-path="url(#u)"><path d="{brush(rng, tx, tx + tw + 24, 80, 3.4)}" fill="{C["shu"]}" opacity=".9"/></g>')
    d.save(file if tone == "dark" else file.replace(".svg", "-light.svg"))


# ================================================================ TERMINAL
APPLE = [
    "........SS......",
    ".......SS.LLL...",
    ".......S.LLLLL..",
    "...RRRRSRRRL....",
    "..RRHHRRRRRRR...",
    ".RRHHRRRRRRRRR..",
    ".RHHRRRRRRRRRRR.",
    ".RHRRRRRRRRRRRR.",
    ".RRRRRRRRRRRRRD.",
    ".RRRRRRRRRRRRRD.",
    ".RRRRRRRRRRRRDD.",
    "..RRRRRRRRRRRDD.",
    "..RRRRRRRRRRDD..",
    "...RRRRRRRDDD...",
    "....RRDDDDDD....",
    ".....DD..DD.....",
]
_BR, _BC, _RAD = 7.6, 15.2, 3.7  # bite circle, in pixel rows/cols
BITE = {(r, c) for r in range(16) for c in range(16) if math.hypot(r - _BR, c - _BC) < _RAD}
FLESH = {(r, c) for r in range(16) for c in range(16)
         if (r, c) not in BITE and APPLE[r][c] in "RHD" and math.hypot(r - _BR, c - _BC) < _RAD + 1.05}


def terminal(tone: str = "dark") -> None:
    p = TONE[tone]
    W, H, T = 1000, 450, 18.0
    DIE, CLEAR = 15.2, 17.2
    d = Doc(W, H, "neofetch — bintang@lugunica", "An animated terminal typing out a neofetch profile beside a pixel-art ringa apple.")
    P = lambda t: pct(t, T)
    d.css.append(STAR_CSS.replace(C["kinari"], p["star"]))
    d.css.append(
        f"""
.bob{{animation:bob 3s ease-in-out infinite}}
@keyframes bob{{50%{{transform:translateY(-6px)}}}}
.shadow{{transform-box:fill-box;transform-origin:center;animation:shadow 3s ease-in-out infinite}}
@keyframes shadow{{50%{{transform:scaleX(.82);opacity:.35}}}}
.bite{{animation:bite {T}s infinite steps(1,end)}}
@keyframes bite{{0%,{P(8.6)}{{opacity:1}}{P(8.7)},{P(DIE + .4)}{{opacity:0}}{P(DIE + .7)}{{opacity:1}}{P(DIE + .9)}{{opacity:0}}{P(DIE + 1.2)},100%{{opacity:1}}}}
.flesh{{opacity:0;animation:flesh {T}s infinite steps(1,end)}}
@keyframes flesh{{0%,{P(8.6)}{{opacity:0}}{P(8.7)},{P(DIE + .4)}{{opacity:1}}{P(DIE + .7)}{{opacity:0}}{P(DIE + .9)}{{opacity:1}}{P(DIE + 1.2)},100%{{opacity:0}}}}
.crumb{{opacity:0;animation:crumb {T}s infinite}}
@keyframes crumb{{0%,{P(8.6)}{{opacity:0;transform:none}}{P(8.7)}{{opacity:1;transform:none}}{P(9.6)},100%{{opacity:0;transform:translate(var(--dx),var(--dy))}}}}
.caret{{animation:blink 1s steps(1,end) infinite}}
@keyframes blink{{50%{{opacity:0}}}}
.jit{{animation:jit {T}s infinite}}
@keyframes jit{{0%,{P(DIE)}{{transform:none}}{P(DIE + .1)}{{transform:translate(-6px,0)}}{P(DIE + .2)}{{transform:translate(5px,1px)}}{P(DIE + .3)}{{transform:translate(-2px,0)}}{P(DIE + .45)},{P(CLEAR - .3)}{{transform:none}}{P(CLEAR - .2)}{{transform:translate(4px,0)}}{P(CLEAR)},100%{{transform:none}}}}
.ghost{{opacity:0;animation:ghost {T}s infinite}}
@keyframes ghost{{0%,{P(DIE)}{{opacity:0}}{P(DIE + .3)}{{opacity:{p["ghost"]}}}{P(CLEAR - .2)}{{opacity:{p["ghost"] / 2}}}{P(CLEAR)},100%{{opacity:0}}}}
"""
    )
    b = d.body.append
    # a header rule and three lamps, but no window around them
    b(f'<path d="M30 44H{W - 30}" stroke="{p["rule"]}"/>')
    for x, col in ((38, p["shu"]), (58, p["acid"]), (78, p["neon"])):
        b(f'<rect x="{x - 4.5}" y="21.5" width="9" height="9" fill="{col}" transform="rotate(45 {x} 26)"/>')
    b(d.text("bintang@lugunica: ~/mathers-domain — zsh", 500, 30, 12, "mono", "middle", attrs=fill(p["dim"])))

    rng = random.Random(3)
    PX, AX, AY = 12, 58, 84
    cols = {"R": "#d93a2b", "H": "#f28b6e", "D": "#8f2217", "S": "#6b4423", "L": "#7d9a4a"}
    b(f'<ellipse cx="{AX + 8 * PX}" cy="{AY + 16 * PX + 22}" rx="70" ry="7" fill="#000" opacity="{p["shadow"]}" class="shadow"/>')
    b('<g class="bob">')
    whole, bite, flesh = [], [], []
    for r, row in enumerate(APPLE):
        for c, ch in enumerate(row):
            x, y = AX + c * PX, AY + r * PX
            if (r, c) in FLESH and ch != ".":
                flesh.append(f'<rect x="{x}" y="{y}" width="{PX}" height="{PX}" fill="#f3e3b5"/>')
            if ch == ".":
                continue
            rect = f'<rect x="{x}" y="{y}" width="{PX}" height="{PX}" fill="{cols[ch]}"/>'
            (bite if (r, c) in BITE or (r, c) in FLESH else whole).append(rect)
    b("".join(whole) + f'<g class="bite">{"".join(bite)}</g><g class="flesh">{"".join(flesh)}</g>')
    for dx, dy in ((34, -26), (46, 4), (28, 30)):
        b(f'<rect x="{AX + 13 * PX}" y="{AY + 7 * PX}" width="5" height="5" fill="#f3e3b5" class="crumb" style="--dx:{dx}px;--dy:{dy}px"/>')
    b("</g>")
    b(stars(rng, 14, 280, 320))
    b(d.text("リンガ · ringa.png", AX + 8 * PX, 336, 12, "mono-b", "middle", attrs=fill(p["ink"])))
    b(d.text("fig.1 — where every loop begins", AX + 8 * PX, 356, 10, "mono", "middle", attrs=fill(p["dim"])))
    b(f'<line x1="292" y1="66" x2="292" y2="420" stroke="{p["rule"]}" stroke-dasharray="3 5"/>')

    X0, Y0, LH, FS = 318, 80, 23.5, 13.5
    cw = FS * 0.6
    b('<g class="jit">')
    lines = []

    def prompt(y: float) -> tuple[str, float]:
        parts = [("bintang", p["neon"], "mono-b"), ("@", p["dim"], "mono"), ("lugunica", p["acid"], "mono-b"),
                 (" ~ ", p["ink"], "mono"), ("❯ ", p["acid"], "mono-b")]
        out, x = [], X0
        for s, col, f in parts:
            out.append(d.text(s, x, y, FS, f, attrs=fill(col)))
            x += len(s) * cw
        return "".join(out), x

    pm, cmd_x = prompt(Y0)
    b(pm)
    cmd = "neofetch --loop"
    lines.append((Y0, d.text(cmd, cmd_x, Y0, FS, "mono", attrs=fill(p["ink"])), len(cmd), cmd_x, 0.5, 0.07))
    t = 0.5 + len(cmd) * 0.07 + 0.35
    y = Y0 + LH
    lines.append((y, d.text("bintang@lugunica", X0, y, FS, "mono-b", attrs=fill(p["neon"])), 16, X0, t, 0.012))
    y += LH
    lines.append((y, d.text("─" * 16, X0, y, FS, "mono", attrs=fill(p["dim"])), 16, X0, t + .12, 0.012))
    for i, (key, val) in enumerate(NEOFETCH):
        y += LH
        mk = d.text(key, X0, y, FS, "mono-b", attrs=fill(p["acid"])) + d.text(val, X0 + 11 * cw, y, FS, "mono", attrs=fill(p["ink"]))
        lines.append((y, mk, 11 + len(val), X0, t + .24 + i * .12, 0.012))
    y += LH
    pal = [(C["sumi0"], "夜"), (C["neon"], "翠"), (C["acid"], "黄"), (C["teal"], "青"), (C["shu"], "朱"),
           (C["muted"], "霧"), (C["gin"], "銀"), (C["kinari"], "白")]
    mk = "".join(f'<rect x="{X0 + j * 30}" y="{y - 12}" width="28" height="14" fill="{c}" stroke="{p["rule"]}"/>' for j, (c, _) in enumerate(pal))
    mk += "".join(d.text(n, X0 + j * 30 + 14, y - 1, 9, "serif", "middle", attrs=fill(C["kinari"] if j in (0, 3, 4) else C["sumi0"]))
                  for j, (_, n) in enumerate(pal))
    lines.append((y, mk, 30, X0, t + .24 + len(NEOFETCH) * .12, 0.008))
    y += LH
    last_y = y
    t_prompt = t + .36 + len(NEOFETCH) * .12
    pm2, px2 = prompt(last_y)

    for j, (ly, mk, n, xs, ts, dt) in enumerate(lines):
        steps_n = n if dt > .05 else min(n, 12)
        unit = cw if dt > .05 else cw * n / steps_n
        ev = [(0, 0)] + [(ts + q * dt, (q + 1) * unit) for q in range(steps_n)] + [(CLEAR, 0)]
        kt, vals = smil_steps(T, ev)
        d.defs.append(
            f'<clipPath id="ln{j}"><rect x="{xs}" y="{ly - 16}" width="0" height="22">'
            f'<animate attributeName="width" dur="{T}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{kt}" values="{vals}"/></rect></clipPath>')
        b(f'<g clip-path="url(#ln{j})">{mk}</g>')

    kt, vals = smil_steps(T, [(0, 0), (t_prompt, 900), (DIE, 0)])
    d.defs.append(f'<clipPath id="pp"><rect x="{X0}" y="{last_y - 16}" width="0" height="22">'
                  f'<animate attributeName="width" dur="{T}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{kt}" values="{vals}"/></rect></clipPath>')
    b(f'<g clip-path="url(#pp)">{pm2}</g>')
    msg = "✕ return_by_death() → restoring checkpoint..."
    ev = [(0, 0)] + [(DIE + .15 + q * .018, (q + 1) * cw) for q in range(len(msg))] + [(CLEAR, 0)]
    kt, vals = smil_steps(T, ev)
    d.defs.append(f'<clipPath id="dm"><rect x="{X0}" y="{last_y - 16}" width="0" height="22">'
                  f'<animate attributeName="width" dur="{T}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{kt}" values="{vals}"/></rect></clipPath>')
    b(f'<g clip-path="url(#dm)">{d.text(msg, X0, last_y, FS, "mono-b", attrs=fill(p["shu"]))}</g>')

    caret = [(0.5 + q * .07, cmd_x + q * cw) for q in range(len(cmd) + 1)] + [(t_prompt, px2), (DIE, -50), (T - .05, cmd_x)]
    kt, xs = smil_steps(T, caret)
    kty, ys = smil_steps(T, [(0, Y0 - 13), (t_prompt, last_y - 13)])
    b(f'<rect class="caret" x="{cmd_x}" y="{Y0 - 13}" width="{cw:.1f}" height="17" fill="{p["acid"]}">'
      f'<animate attributeName="x" dur="{T}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{kt}" values="{xs}"/>'
      f'<animate attributeName="y" dur="{T}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{kty}" values="{ys}"/></rect>')
    b("</g>")
    b(f'<g class="ghost">{d.text("死に戻り", 640, 280, 120, "brush", "middle", attrs=fill(p["shu"]))}</g>')
    d.save(out_name("terminal.svg", tone))


# ==================================================================== SINS
def sins(tone: str = "dark") -> None:
    p = TONE[tone]
    W, H, T = 1000, 500, 12.0
    rng = random.Random(7)
    d = Doc(W, H, "Witch Cult Archive — skill levels",
            "The seven sins of the Witch Cult in kanji, each painted as a brush-stroke skill level.")
    d.css.append(STAR_CSS.replace(C["kinari"], p["star"]) + PETAL_CSS)
    d.css.append(
        f"""
.lv{{animation:lv .8s 1.2s ease both}}
@keyframes lv{{from{{opacity:0;transform:translateX(10px)}}}}
.kj{{animation:kj .8s ease both}}
@keyframes kj{{from{{opacity:0;transform:translateY(-6px)}}}}
.env-a{{animation:enva 3.2s steps(1,end) infinite}}
@keyframes enva{{0%,38%{{opacity:1}}40%,43%{{opacity:0}}45%,66%{{opacity:1}}68%,100%{{opacity:0}}}}
.env-b{{opacity:0;animation:envb 3.2s steps(1,end) infinite}}
@keyframes envb{{0%,38%{{opacity:0}}40%,43%{{opacity:1}}45%,66%{{opacity:0}}68%,100%{{opacity:1}}}}
.flick{{animation:flick 2.3s steps(1,end) infinite}}
@keyframes flick{{0%,70%{{opacity:1}}72%{{opacity:.2}}74%{{opacity:1}}80%{{opacity:.4}}82%,100%{{opacity:1}}}}
.envk{{animation:envk 2.3s steps(1,end) infinite}}
@keyframes envk{{0%,70%{{fill:{p["sin"]["ENVY"]}}}72%{{fill:{p["shu"]}}}76%,100%{{fill:{p["sin"]["ENVY"]}}}}}
"""
    )
    b = d.body.append
    b(d.text("魔", 890, 470, 300, "brush", "middle", attrs=f'{fill(p["neon"])} fill-opacity="{p["ghost"] / 4}"'))
    b(stars(rng, 30, W, H))
    b(petals(rng, 8, W, H, p["petals"]))
    b(d.text("大罪司教  ·  ARCHBISHOPS OF THE SEVEN SINS", 32, 40, 10.5, "mono", ls=2, attrs=fill(p["dim"])))
    b(d.text("魔女教  ·  CLASSIFIED", 968, 40, 10.5, "mono", "end", ls=2, attrs=fill(p["shu"])))
    b(f'<line x1="32" y1="54" x2="968" y2="54" stroke="{p["rule"]}"/>')

    BX, BW = 330, 520
    for r, (kanji, sin, _c, skill, lvl, flavour) in enumerate(SINS):
        col = p["sin"][sin]
        yc = 70 + r * 58 + 29
        envy = sin == "ENVY"
        t0 = .3 + r * .2
        if r:
            b(f'<line x1="32" y1="{yc - 29}" x2="968" y2="{yc - 29}" stroke="{p["rule"]}" stroke-opacity=".5"/>')
        kcls = "kj" + (" envk" if envy else "")
        b(f'<g class="{kcls}" style="animation-delay:{t0:.2f}s">{d.text(kanji, 34, yc + 10, 27, "brush", attrs=fill(col))}</g>')
        b(d.text(sin, 104, yc - 3, 12, "serif", ls=2.5, attrs=fill(col) + (' class="flick"' if envy else "")))
        if envy:
            b(f'<g class="env-a">{d.text(skill, 104, yc + 15, 12, "mono", attrs=fill(p["ink"]))}</g>')
            b(f'<g class="env-b">{d.text("█" * len(skill), 104, yc + 15, 12, "mono", attrs=fill(p["track"]))}</g>')
        else:
            b(d.text(skill, 104, yc + 15, 12, "mono", attrs=fill(p["ink"])))
        b(f'<path d="{brush(rng, BX, BX + BW, yc - 5, 12)}" fill="{p["track"]}"/>')
        lw = BW * lvl / 100
        d.defs.append(
            f'<clipPath id="bar{r}"><rect x="{BX - 2}" y="{yc - 16}" width="0" height="24">'
            f'<animate attributeName="width" dur="{T}s" repeatCount="indefinite" begin="{t0:.2f}s" calcMode="spline" '
            f'values="0;0;{lw + 4:.0f};{lw + 4:.0f};0;0" keyTimes="0;.01;.13;.9;.95;1" '
            f'keySplines="0 0 1 1;.25 0 .2 1;0 0 1 1;.5 0 .5 1;0 0 1 1"/></rect></clipPath>')
        stroke = f' stroke="{p["shu"]}" stroke-opacity=".7"' if envy else ""
        b(f'<g clip-path="url(#bar{r})"><path d="{brush(rng, BX, BX + lw, yc - 5, 13)}" fill="{p["track"] if envy else col}"{stroke}'
          + (' class="flick"' if envy else "") + "/></g>")
        b(d.text(flavour, BX, yc + 20, 10.5, "mono", attrs=fill(p["dim"])))
        dan = KANJI_NUM[lvl // 10] + "段"
        b(f'<g class="lv" style="animation-delay:{1 + t0:.2f}s">'
          + d.text(dan, 968, yc + 3, 20, "serif", "end", attrs=fill(p["shu"] if envy else col))
          + d.text(f"LV.{lvl}", 968, yc + 20, 10, "mono", "end", attrs=fill(p["dim"])) + "</g>")
    d.save(out_name("sins.svg", tone))


# =================================================================== ORBIT
def badge(d: Doc, kind: str, col: str) -> str:
    s = 24
    ink = "#f2f7f0"
    base = f'<rect x="{-s / 2}" y="{-s / 2}" width="{s}" height="{s}" rx="3" fill="{col}"/>'
    if kind == "react":
        e = "".join(f'<ellipse rx="9.5" ry="3.6" fill="none" stroke="{ink}" stroke-width="1.2" transform="rotate({a})"/>' for a in (0, 60, 120))
        return base + e + f'<circle r="1.8" fill="{ink}"/>'
    if kind == "node":
        pts = " ".join(f"{8.5 * math.cos(math.radians(a - 90)):.1f},{8.5 * math.sin(math.radians(a - 90)):.1f}" for a in range(0, 360, 60))
        return base + f'<polygon points="{pts}" fill="none" stroke="{ink}" stroke-width="1.4"/>'
    if kind == "docker":
        blocks = "".join(f'<rect x="{-8 + i * 4.8:.1f}" y="{-1 + j * -4.8:.1f}" width="3.8" height="3.8" fill="{ink}"/>'
                         for j, row in enumerate((4, 3, 1)) for i in range(row))
        return base + f'<g transform="translate(0 3)">{blocks}</g>'
    label = {"ts": "TS", "js": "JS", "next": "N", "nest": "Ne", "pg": "Pg", "py": "Py"}[kind]
    return base + d.text(label, 0, 4, 10.5, "mono-b", "middle", attrs=fill(ink))


def orbit(tone: str = "dark") -> None:
    p = TONE[tone]
    W, H, T = 1000, 440, 10.0
    CX, CY = 500, 212
    d = Doc(W, H, "Spirit contracts — tech stack", "Tech stack seals orbiting a mitsudomoe inside a brushed ensō.")
    rng = random.Random(21)
    d.defs.append(
        f'<radialGradient id="halo"><stop offset="0" stop-color="{p["neon"]}" stop-opacity=".2"/>'
        f'<stop offset=".45" stop-color="{p["neon"]}" stop-opacity=".06"/><stop offset="1" stop-color="{p["neon"]}" stop-opacity="0"/></radialGradient>'
    )
    d.css.append(STAR_CSS.replace(C["kinari"], p["star"]) + PETAL_CSS)
    d.css.append(
        f"""
.halo{{transform-origin:{CX}px {CY}px;animation:halo 5s ease-in-out infinite}}
@keyframes halo{{50%{{transform:scale(1.12);opacity:.7}}}}
.spin{{transform-origin:{CX}px {CY}px;animation:spin 16s linear infinite reverse}}
.spin-r{{transform-origin:{CX}px {CY}px;animation:spin 40s linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.flow{{animation:flow 30s linear infinite}}
@keyframes flow{{to{{stroke-dashoffset:-400}}}}
.flow-r{{animation:flow 40s linear infinite reverse}}
.enso{{animation:enso {T}s ease infinite}}
@keyframes enso{{0%,84%{{opacity:1}}94%,100%{{opacity:0}}}}
"""
    )
    b = d.body.append
    b(stars(rng, 55, W, H))
    b(petals(rng, 10, W, H, p["petals"]))
    n_sp = len(INNER_SPIRITS) + len(OUTER_SPIRITS)
    b(d.text(f"精霊術  ·  SPIRIT ARTS  ·  {KANJI_NUM[n_sp]}体契約  ·  {n_sp} SPIRITS BOUND",
             CX, 40, 10.5, "mono", "middle", ls=2, attrs=fill(p["dim"])))

    orbits = [(255, 72, 28, True, INNER_SPIRITS, p["seal-a"]), (420, 138, 42, False, OUTER_SPIRITS, p["seal-b"])]

    def ellipse_path(rx: float, ry: float, cw: bool) -> str:
        s = 1 if cw else 0
        return f"M{CX + rx},{CY} A{rx},{ry} 0 1 {s} {CX - rx},{CY} A{rx},{ry} 0 1 {s} {CX + rx},{CY}"

    for rx, ry, _, cw, _, _ in orbits:
        b(f'<ellipse cx="{CX}" cy="{CY}" rx="{rx}" ry="{ry}" fill="none" stroke="{p["rule"]}" '
          f'stroke-dasharray="2 7" class="{"flow" if cw else "flow-r"}"/>')

    for _, _, _, _, spirits, col in orbits:
        for label, kind in spirits:
            w = 24 + 10 + d.measure(label, "mono", 13) + 22
            x0 = -w / 2
            d.defs.append(
                f'<g id="chip-{kind}"><rect x="{x0:.1f}" y="-18" width="{w:.1f}" height="36" rx="4" fill="{p["chip"]}" '
                f'stroke="{p["rule"]}"/>'
                f'<g transform="translate({x0 + 8 + 12:.1f} 0)">{badge(d, kind, col)}</g>'
                + d.text(label, x0 + 8 + 24 + 10, 4.6, 13, "mono", attrs=fill(p["ink"])) + "</g>")

    def chips(front: bool) -> str:
        out = []
        for rx, ry, dur, cw, spirits, _ in orbits:
            path = ellipse_path(rx, ry, cw)
            n = len(spirits)
            if cw:  # first half of the path is the near side
                scale, op, vis = "1;1.12;1;.8;1", "1;1;1;.4;1", "1;0"
            else:
                scale, op, vis = "1;.8;1;1.12;1", "1;.4;1;1;1", "0;1"
            for i, (_, kind) in enumerate(spirits):
                common = f'dur="{dur}s" begin="-{dur * i / n:.2f}s" repeatCount="indefinite"'
                vis_anim = (f'<animate attributeName="opacity" values="{vis}" keyTimes="0;.5" calcMode="discrete" {common}/>' if front
                            else f'<animate attributeName="opacity" values="{op}" keyTimes="0;.25;.5;.75;1" {common}/>')
                out.append(
                    f'<g><animateMotion path="{path}" {common}/>{vis_anim}'
                    f'<g><animateTransform attributeName="transform" type="scale" values="{scale}" keyTimes="0;.25;.5;.75;1" '
                    f'calcMode="spline" keySplines=".4 0 .6 1;.4 0 .6 1;.4 0 .6 1;.4 0 .6 1" {common}/>'
                    f'<use href="#chip-{kind}"/></g></g>')
        return "".join(out)

    b(chips(front=False))
    # the centre: a brushed ensō around a turning mitsudomoe
    b(f'<circle cx="{CX}" cy="{CY}" r="150" fill="url(#halo)" class="halo"/>')
    R = 80
    sx, sy = polar(CX, CY, R, 215)
    ex, ey = polar(CX, CY, R, 215 + 335)
    arc = f"M{sx:.1f} {sy:.1f}A{R} {R} 0 1 1 {ex:.1f} {ey:.1f}"
    d.defs.append(
        f'<mask id="em" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
        f'<path d="{arc}" pathLength="1" fill="none" stroke="#fff" stroke-width="40" stroke-linecap="round" stroke-dasharray="1 1">'
        f'<animate attributeName="stroke-dashoffset" values="1;0;0" keyTimes="0;.18;1" dur="{T}s" repeatCount="indefinite" '
        f'calcMode="spline" keySplines=".5 0 .3 1;0 0 1 1"/></path></mask>')
    bristles = []
    for i in range(7):
        rr = R + (i - 3) * 2.6
        a0, a1 = polar(CX, CY, rr, 215 + rng.uniform(-3, 3)), polar(CX, CY, rr, 215 + 335 - abs(i - 3) * 6 + rng.uniform(-4, 4))
        dash = f"{rng.uniform(.62, .8):.2f} .02 {rng.uniform(.05, .12):.2f} {rng.uniform(.02, .06):.2f} .06 .1"
        bristles.append(f'<path d="M{a0[0]:.1f} {a0[1]:.1f}A{rr:.1f} {rr:.1f} 0 1 1 {a1[0]:.1f} {a1[1]:.1f}" pathLength="1" fill="none" '
                        f'stroke="{p["ink"]}" stroke-opacity="{rng.uniform(.55, .9):.2f}" stroke-width="{rng.uniform(2.2, 4.2):.1f}" '
                        f'stroke-linecap="round" stroke-dasharray="{dash}"/>')
    b(f'<g class="enso"><g mask="url(#em)">{"".join(bristles)}</g></g>')
    b(f'<circle cx="{CX}" cy="{CY}" r="50" fill="none" stroke="{p["acid"]}" stroke-opacity=".6"/>')
    b(f'<circle cx="{CX}" cy="{CY}" r="56" fill="none" stroke="{p["acid"]}" stroke-opacity=".35" stroke-dasharray="1 4" class="spin-r"/>')
    b(f'<path d="{tomoe(CX, CY, 42)}" fill="{p["neon"]}" class="spin"/>')
    b(chips(front=True))
    b(d.text("◆  contracted spirits  ·  精霊術師  ·  bound since 2020  ◆", CX, 410, 11, "mono", "middle", ls=1, attrs=fill(p["dim"])))
    d.save(out_name("orbit.svg", tone))


# ================================================================== FOOTER
def footer(tone: str = "dark") -> None:
    p = TONE[tone]
    W, H, T = 1000, 262, 10.0
    FLAT, DARK, BACK = 58, 70, 88
    d = Doc(W, H, "Thanks for visiting", "A heart monitor flatlines, 死に戻り rises, and the heartbeat returns.")
    BL, X0, X1, BEAT = 112, 40, 960, 230
    rng = random.Random(9)

    def beat_path() -> str:
        q = [f"M{X0},{BL}"]
        for bx in range(X0, X1, BEAT):
            q.append(f"L{bx + 60},{BL} Q{bx + 77},{BL - 13} {bx + 94},{BL} L{bx + 108},{BL} L{bx + 115},{BL + 9} "
                     f"L{bx + 123},{BL - 56} L{bx + 131},{BL + 22} L{bx + 138},{BL} L{bx + 160},{BL} "
                     f"Q{bx + 182},{BL - 18} {bx + 204},{BL} L{min(bx + BEAT, X1)},{BL}")
        return " ".join(q)

    trace, flat = beat_path(), f"M{X0},{BL} L{X1},{BL}"
    d.defs.append(
        f'<pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">'
        f'<path d="M20 0H0V20" fill="none" stroke="{p["rule"]}" stroke-opacity=".55"/></pattern>'
        '<filter id="scrf" x="-10%" y="-25%" width="120%" height="150%"><feGaussianBlur stdDeviation="11"/></filter>'
        f'<mask id="scr" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
        f'<g filter="url(#scrf)"><rect x="40" y="38" width="920" height="122" rx="26" fill="#fff"/></g></mask>'
        f'<linearGradient id="tg" gradientUnits="userSpaceOnUse" x1="{W / 2 - 260}" x2="{W / 2 + 260}" spreadMethod="reflect">'
        f'<stop offset="0" stop-color="{p["acid"]}"/><stop offset=".5" stop-color="{p["acid-hi"]}"/><stop offset="1" stop-color="{p["acid"]}"/>'
        '<animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="1040 0" dur="6s" repeatCount="indefinite"/></linearGradient>'
        + rough_filter("rough", 2)
    )
    d.css.append(STAR_CSS.replace(C["kinari"], p["star"]) + PETAL_CSS)
    d.css.append(
        f"""
.alive{{animation:alive {T}s infinite}}
@keyframes alive{{0%,{FLAT - .1}%{{opacity:1}}{FLAT}%,{BACK - .1}%{{opacity:0}}{BACK}%,100%{{opacity:1}}}}
.dead{{opacity:0;animation:dead {T}s infinite}}
@keyframes dead{{0%,{FLAT - .1}%{{opacity:0}}{FLAT}%,{BACK - .1}%{{opacity:1}}{BACK}%,100%{{opacity:0}}}}
.heart{{transform-box:fill-box;transform-origin:center;animation:heart .625s ease-out infinite}}
@keyframes heart{{0%{{transform:scale(1.25)}}40%,100%{{transform:scale(1)}}}}
.blink{{animation:blink .5s steps(1,end) infinite}}
@keyframes blink{{50%{{opacity:.2}}}}
.jp{{opacity:0;transform-origin:500px 100px;animation:jp {T}s infinite}}
@keyframes jp{{0%,{DARK + 2}%{{transform:scale(1.25);opacity:0}}{DARK + 7}%{{transform:scale(1);opacity:1}}{BACK - 3}%{{transform:scale(.97);opacity:1}}{BACK - 2}%{{transform:translateX(8px)}}{BACK}%,100%{{opacity:0}}}}
.stamp{{opacity:0;animation:stamp {T}s infinite}}
@keyframes stamp{{0%,{DARK + 6}%{{opacity:0;transform:scale(2.2)}}{DARK + 8}%{{opacity:1;transform:scale(.9)}}{DARK + 9}%{{transform:scale(1)}}{BACK - 2}%{{opacity:1}}{BACK}%,100%{{opacity:0}}}}
"""
    )
    b = d.body.append
    b(stars(rng, 30, W, H))
    # graph paper for the trace, faded out at its edges — no screen bezel
    b(f'<g mask="url(#scr)"><rect x="24" y="24" width="952" height="150" fill="url(#grid)"/></g>')
    b(d.text("VITALS  ·  bintang@lugunica", 66, 50, 10.5, "mono", ls=2, attrs=fill(p["dim"])))
    heart = "M850 44c-3-6-12-5-12 2 0 5 7 9 12 13 5-4 12-8 12-13 0-7-9-8-12-2z"
    b('<g class="alive">'
      + d.text("● 安定 STABLE", 500, 50, 10.5, "mono-b", "middle", ls=2, attrs=fill(p["neon"]))
      + f'<path class="heart" d="{heart}" fill="{p["shu"]}"/>'
      + d.text("96", 878, 58, 20, "mono-b", attrs=fill(p["ink"]))
      + d.text("BPM", 906, 58, 9.5, "mono", attrs=fill(p["dim"])) + "</g>")
    b('<g class="dead">'
      + d.text("✕ 心停止 FLATLINE", 500, 50, 10.5, "mono-b", "middle", ls=2, attrs=f'{fill(p["shu"])} class="blink"')
      + f'<path d="{heart}" fill="none" stroke="{p["shu"]}"/>'
      + d.text("00", 878, 58, 20, "mono-b", attrs=f'{fill(p["shu"])} class="blink"')
      + d.text("BPM", 906, 58, 9.5, "mono", attrs=fill(p["dim"])) + "</g>")

    sweep = ('stroke-dasharray=".93 .07"><animate attributeName="stroke-dashoffset" from=".93" to="-.07" '
             'dur="2.5s" repeatCount="indefinite"/></path>')

    def ecg(path: str, col: str) -> str:
        return (f'<path d="{path}" pathLength="1" fill="none" stroke="{col}" stroke-width="6" stroke-opacity=".16" stroke-linejoin="round" {sweep}'
                f'<path d="{path}" pathLength="1" fill="none" stroke="{col}" stroke-width="1.8" stroke-linejoin="round" {sweep}'
                f'<g><animateMotion path="{path}" dur="2.5s" repeatCount="indefinite"/>'
                f'<circle r="7" fill="{col}" fill-opacity=".25"/><circle r="3" fill="{p["ink"]}"/></g>')

    b(f'<g mask="url(#scr)"><g class="alive">{ecg(trace, p["neon"])}</g>'
      f'<g class="dead">{ecg(flat, p["shu"])}</g></g>')
    b(f'<g class="jp">{d.text("死に戻り", 500, 116, 50, "brush", "middle", ls=10, attrs=fill(p["shu"]))}'
      + d.text("RETURN  BY  DEATH", 500, 150, 11, "mono-b", "middle", ls=6, attrs=fill(p["dim"])) + "</g>"
      f'<g transform="translate(680 92) rotate(8)"><g class="stamp"><g filter="url(#rough)">{seal(d, "戻", 46, "brush")}</g></g></g>')
    b(petals(rng, 10, W, H, p["petals"]))

    tmask = d.text("THANKS FOR VISITING", 500, 214, 19, "serif", "middle", ls=6, attrs=' fill="#fff"')
    d.defs.append(f'<mask id="tm" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">{tmask}</mask>')
    b(f'<g mask="url(#tm)"><rect x="0" y="190" width="{W}" height="36" fill="url(#tg)"/></g>')
    b(d.text('"kalau gagal, ulangi dari checkpoint — selalu ada loop berikutnya."', 500, 240, 11, "mono", "middle",
             attrs=fill(p["dim"])))
    d.save(out_name("footer.svg", tone))


if __name__ == "__main__":
    print("building static SVGs")
    hero()
    for tone in INK:
        divider(tone)
        for f, (num, jp, t) in HEADERS.items():
            header(f, num, jp, t, tone)
        terminal(tone)
        sins(tone)
        orbit(tone)
        footer(tone)
