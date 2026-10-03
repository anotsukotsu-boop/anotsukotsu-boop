"""Builds assets/stats.svg from live GitHub data.

    GITHUB_TOKEN=... python tools/build_stats.py [username]

With a token it uses the GraphQL API (language sizes in bytes). Without one it
falls back to the public REST API plus the public contribution calendar, so it
also works locally with no setup. The workflow in .github/workflows runs this
once a day and commits the result.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import random
import re
import sys
import urllib.request
from collections import Counter

from svgkit import PETAL_CSS, STAR_CSS, Doc, fill, petals, stars

USER = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GH_USER", "Bintangilham10")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
# e.g. HIDE_LANGS="HTML,Blade" to keep noise out of the language bar
HIDE_LANGS = {x.strip() for x in os.environ.get("HIDE_LANGS", "").split(",") if x.strip()}

# The card sits straight on the page, with no panel behind it, so it ships a
# dark and a light variant. Languages are coloured by rank, not by brand.
TONE = {
    "dark": {"ink": "#eef3dc", "dim": "#8fa89a", "rule": "#2c4c42", "star": "#eef3dc",
             "ranks": ["#24e33d", "#d9e67a", "#1f8a70", "#e07b39", "#e8a0b4", "#c9cdd4", "#2c3f38"],
             "levels": ["#10231c", "#0f3d2b", "#16863a", "#24e33d", "#d9e67a"],
             "petals": ["#d9e67a", "#eef3dc", "#d9e67a", "#5fd97a"],
             "accents": ["#d9e67a", "#24e33d", "#e03c31", "#1f8a70"]},
    "light": {"ink": "#16231d", "dim": "#5a6b63", "rule": "#c2d0c9", "star": "#9aada3",
              "ranks": ["#11823a", "#8a7a12", "#17695a", "#b2541b", "#b8537a", "#5c6b73", "#9aa8a1"],
              "levels": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
              "petals": ["#8a9a3a", "#9aada3", "#8a9a3a", "#3f9e5c"],
              "accents": ["#8a7a12", "#11823a", "#c42a1f", "#17695a"]},
}


def get(url: str, data: dict | None = None) -> str:
    headers = {"User-Agent": "loop-stats", "Accept": "application/vnd.github+json"}
    if TOKEN and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {TOKEN}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8")


QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""
LEVEL_MAP = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def via_graphql() -> dict:
    res = json.loads(get("https://api.github.com/graphql", {"query": QUERY, "variables": {"login": USER}}))
    if res.get("errors"):
        raise RuntimeError(res["errors"])
    u = res["data"]["user"]
    langs: Counter = Counter()
    colors = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            langs[e["node"]["name"]] += e["size"]
            colors[e["node"]["name"]] = e["node"]["color"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    days = [(d["date"], d["contributionCount"], LEVEL_MAP[d["contributionLevel"]])
            for w in cal["weeks"] for d in w["contributionDays"]]
    return {
        "source": "GraphQL",
        "total": cal["totalContributions"],
        "days": days,
        "repos": u["repositories"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in u["repositories"]["nodes"]),
        "followers": u["followers"]["totalCount"],
        "langs": langs,
        "lang_unit": "code size",
        "colors": colors,
    }


def via_public() -> dict:
    user = json.loads(get(f"https://api.github.com/users/{USER}"))
    repos = json.loads(get(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner"))
    own = [r for r in repos if not r["fork"]]
    langs = Counter(r["language"] for r in own if r["language"])
    page = get(f"https://github.com/users/{USER}/contributions")
    days, counts = [], {}
    for m in re.finditer(r'<tool-tip[^>]*for="(contribution-day-component-[\d-]+)"[^>]*>([^<]*)</tool-tip>', page):
        n = re.match(r"(\d[\d,]*) contribution", m.group(2))
        counts[m.group(1)] = int(n.group(1).replace(",", "")) if n else 0
    for m in re.finditer(r"<td[^>]*ContributionCalendar-day[^>]*>", page):
        tag = m.group(0)
        date = re.search(r'data-date="([\d-]+)"', tag)
        level = re.search(r'data-level="(\d)"', tag)
        cid = re.search(r'id="([^"]+)"', tag)
        if date and level:
            lvl = int(level.group(1))
            days.append((date.group(1), counts.get(cid.group(1) if cid else "", lvl), lvl))
    days.sort()
    total = re.search(r"([\d,]+)\s+contributions?\s+in the last year", " ".join(page.split()))
    return {
        "source": "public API",
        "total": int(total.group(1).replace(",", "")) if total else sum(c for _, c, _ in days),
        "days": days,
        "repos": len(own),
        "stars": sum(r["stargazers_count"] for r in own),
        "followers": user["followers"],
        "langs": langs,
        "lang_unit": "repo count",
        "colors": {},
    }


def streaks(days: list[tuple[str, int, int]]) -> tuple[int, int]:
    active = [c > 0 for _, c, _ in days]
    longest = run = 0
    for a in active:
        run = run + 1 if a else 0
        longest = max(longest, run)
    cur, i = 0, len(active) - 1
    if i >= 0 and not active[i]:  # today may simply not have started yet
        i -= 1
    while i >= 0 and active[i]:
        cur += 1
        i -= 1
    return cur, longest


# ---------------------------------------------------------------- render
def render(data: dict, tone: str = "dark") -> Doc:
    p = TONE[tone]
    W, H, T = 1000, 440, 12.0
    d = Doc(W, H, "Loop records — GitHub stats",
            f"{data['total']} contributions in the last year, live GitHub stats for {USER}.")
    cur, best = streaks(data["days"])
    d.defs.append(
        f'<linearGradient id="band" x1="0" x2="1"><stop offset="0" stop-color="{p["ink"]}" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="{p["ink"]}" stop-opacity=".18"/><stop offset="1" stop-color="{p["ink"]}" stop-opacity="0"/></linearGradient>'
    )
    d.css.append(STAR_CSS.replace("#eef3dc", p["star"]) + PETAL_CSS)
    d.css.append(
        f"""
.wheel{{animation:wheel {T}s infinite both}}
@keyframes wheel{{0%,6%{{transform:translateY(0);animation-timing-function:cubic-bezier(.3,0,.1,1)}}24%,100%{{transform:translateY(var(--to))}}}}
.cell{{animation:cell .6s ease both}}
@keyframes cell{{from{{opacity:0}}}}
.band{{animation:band 7s cubic-bezier(.5,0,.5,1) infinite}}
@keyframes band{{0%,20%{{transform:translateX(0)}}70%,100%{{transform:translateX(1000px)}}}}
.today{{transform-box:fill-box;transform-origin:center;animation:today 1.6s ease-out infinite}}
@keyframes today{{from{{transform:scale(1);opacity:1}}to{{transform:scale(2.4);opacity:0}}}}
.seg{{transform-box:fill-box;transform-origin:0 50%;animation:seg 1.1s cubic-bezier(.2,.8,.2,1) both}}
@keyframes seg{{from{{transform:scaleX(0)}}}}
.glow{{animation:glow 3s ease-in-out infinite}}
@keyframes glow{{50%{{opacity:.35}}}}
"""
    )
    b = d.body.append
    rng = random.Random(12)
    b(stars(rng, 40, W, H))
    b(petals(rng, 7, W, H, p["petals"]))

    # -- tiles with odometer numbers ------------------------------------------
    tiles = [
        ("生還 · LOOPS SURVIVED", data["total"], "contributions · last 365 days", p["accents"][0]),
        ("連続 · CURRENT STREAK", cur, "days in a row" if cur != 1 else "day in a row", p["accents"][1]),
        ("最長 · LONGEST STREAK", best, "consecutive days · personal best", p["accents"][2]),
        ("工房 · REPOS FORGED", data["repos"], f"★ {data['stars']} star{'s' if data['stars'] != 1 else ''}  ·  {data['followers']} followers", p["accents"][3]),
    ]
    TW, TG, TY, TH = 226, 16, 24, 108
    size, h = 36, 44
    digit_w = max(d.measure(str(n), "serif", size) for n in range(10))
    col = 0
    for i, (label, value, sub, accent) in enumerate(tiles):
        x = 24 + i * (TW + TG)
        if i:  # a hairline between tiles instead of a box around each
            b(f'<line x1="{x - TG / 2:.0f}" y1="{TY + 14}" x2="{x - TG / 2:.0f}" y2="{TY + TH - 14}" stroke="{p["rule"]}"/>')
        b(f'<rect x="{x + 18}" y="{TY}" width="46" height="2.5" fill="{accent}" class="glow"/>')
        b(d.text(label, x + 18, TY + 26, 10, "mono", ls=2, attrs=fill(p["dim"])))
        text = f"{value:,}"
        nx, base = x + 18, TY + 70
        for ch in text:
            if not ch.isdigit():
                b(d.text(ch, nx, base, size, "serif", attrs=fill(accent)))
                nx += d.measure(ch, "serif", size) + 2
                continue
            dig = int(ch)
            cid = f"dg{col}"
            d.defs.append(f'<clipPath id="{cid}"><rect x="{nx - 2:.1f}" y="{base - size * .8:.1f}" width="{digit_w + 4:.1f}" height="{size * 1.02:.1f}"/></clipPath>')
            stack = "".join(
                d.text(str((dig + j) % 10), nx + digit_w / 2, base + j * h, size, "serif", "middle")
                for j in range(11)
            )
            b(f'<g clip-path="url(#{cid})"><g class="wheel" fill="{p["ink"]}" '
              f'style="--to:-{10 * h}px;animation-delay:{.2 + i * .25 + col * .06:.2f}s">{stack}</g></g>')
            nx += digit_w + 2
            col += 1
        b(d.text(sub, x + 18, TY + 92, 10, "mono", attrs=fill(p["dim"])))

    # -- contribution heatmap -----------------------------------------------------
    days = data["days"]
    CS, CG = 13, 3
    weeks: list[list[tuple[str, int, int]]] = []
    for day in days:
        wd = (dt.date.fromisoformat(day[0]).weekday() + 1) % 7  # Sunday = 0
        if not weeks or wd == 0:
            weeks.append([None] * 7)
        weeks[-1][wd] = day
    gw = len(weeks) * (CS + CG) - CG
    gx, gy = (W - gw) / 2 + 14, 196
    b(d.text("ループ履歴  ·  LOOP HISTORY  ·  every cell is one day of the loop", 24, 166, 10.5, "mono", ls=1.6, attrs=fill(p["dim"])))
    lx = W - 24 - d.measure("more", "mono", 10)
    b(d.text("more", W - 24, 166, 10, "mono", "end", attrs=fill(p["dim"])))
    for lv in reversed(range(5)):
        lx -= 16
        b(f'<rect x="{lx:.1f}" y="157" width="11" height="11" rx="2.5" fill="{p["levels"][lv]}"/>')
    b(d.text("less", lx - 6, 166, 10, "mono", "end", attrs=fill(p["dim"])))
    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        b(d.text(label, gx - 8, gy + row * (CS + CG) + 10, 9.5, "mono", "end", attrs=fill(p["dim"])))
    last_month = None
    cells = []
    for wi, week in enumerate(weeks):
        first = next((x for x in week if x), None)
        if first:
            m = dt.date.fromisoformat(first[0]).strftime("%b")
            if m != last_month and wi < len(weeks) - 2:
                if last_month is not None or dt.date.fromisoformat(first[0]).day <= 7:
                    b(d.text(m, gx + wi * (CS + CG), gy - 8, 9.5, "mono", attrs=fill(p["dim"])))
                last_month = m
        for wd, day in enumerate(week):
            if not day:
                continue
            x, y = gx + wi * (CS + CG), gy + wd * (CS + CG)
            cells.append(f'<rect x="{x:.1f}" y="{y}" width="{CS}" height="{CS}" rx="3" fill="{p["levels"][day[2]]}" '
                         f'class="cell" style="animation-delay:{.3 + wi * .018:.3f}s"/>')
    b("".join(cells))
    if days:
        tx = gx + (len(weeks) - 1) * (CS + CG) + CS / 2
        ty = gy + ((dt.date.fromisoformat(days[-1][0]).weekday() + 1) % 7) * (CS + CG) + CS / 2
        b(f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="6" fill="none" stroke="{p["accents"][0]}" stroke-width="1.5" class="today"/>')
    gh = 7 * (CS + CG) - CG
    d.defs.append(f'<clipPath id="gridc"><rect x="{gx}" y="{gy}" width="{gw}" height="{gh}"/></clipPath>')
    b(f'<g clip-path="url(#gridc)"><rect x="{gx - 120:.0f}" y="{gy}" width="80" height="{gh}" fill="url(#band)" class="band"/></g>')

    # -- languages ------------------------------------------------------------------
    ly = 346
    langs = {k: v for k, v in data["langs"].items() if k not in HIDE_LANGS}
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:6]
    total = sum(langs.values()) or 1
    other = total - sum(v for _, v in top)
    parts = [(n, v, p["ranks"][i]) for i, (n, v) in enumerate(top)]
    if other > 0:
        parts.append(("Other", other, p["ranks"][6]))
    b(d.text(f"属性  ·  AFFINITY  ·  languages by {data['lang_unit']}", 24, ly - 14, 10.5, "mono", ls=1.6, attrs=fill(p["dim"])))
    bx, bw = 24, W - 48
    d.defs.append(f'<clipPath id="barc"><rect x="{bx}" y="{ly}" width="{bw}" height="10" rx="2"/></clipPath>')
    b('<g clip-path="url(#barc)">')
    x = bx
    for i, (name, v, colr) in enumerate(parts):
        w = bw * v / total
        b(f'<rect x="{x:.1f}" y="{ly}" width="{max(w - 2, 1):.1f}" height="10" fill="{colr}" class="seg" style="animation-delay:{.5 + i * .12:.2f}s"/>')
        x += w
    b("</g>")
    x = bx
    step = bw / len(parts)
    for i, (name, v, colr) in enumerate(parts):
        cx = bx + i * step
        b(f'<circle cx="{cx + 5:.1f}" cy="{ly + 31}" r="5" fill="{colr}"/>')
        b(d.text(name, cx + 16, ly + 35, 11.5, "mono", attrs=fill(p["ink"])))
        b(d.text(f"{v / total * 100:.1f}%", cx + 16 + d.measure(name, "mono", 11.5) + 7, ly + 35, 11.5, "mono",
                 attrs=fill(p["dim"])))

    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    b(f'<line x1="24" y1="{H - 38}" x2="{W - 24}" y2="{H - 38}" stroke="{p["rule"]}"/>')
    b(d.text(f"last sync  {today}", 24, H - 16, 10, "mono", attrs=fill(p["dim"])))
    b(d.text(f"auto-rebuilt by github actions  ·  source: {data['source']}", W - 24, H - 16, 10, "mono", "end",
             attrs=fill(p["dim"])))
    return d


def main() -> None:
    print(f"fetching stats for {USER} ({'token' if TOKEN else 'no token'})")
    data = None
    if TOKEN:
        try:
            data = via_graphql()
        except Exception as e:  # fall back rather than leave the card stale
            print(f"  GraphQL failed ({e}); using public data")
    if data is None:
        data = via_public()
    if not data["days"]:
        raise SystemExit("no contribution data found; keeping the previous stats.svg")
    print(f"  {data['total']} contributions, {data['repos']} repos, {len(data['days'])} days")
    render(data, "dark").save("stats.svg")
    render(data, "light").save("stats-light.svg")


if __name__ == "__main__":
    main()
