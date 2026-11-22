"""Generate self-hosted GitHub stats cards (no third-party image services).

Writes stats/overview.svg and stats/languages.svg. Runs daily from
.github/workflows/stats-cards.yml using the built-in GITHUB_TOKEN.
Standard library only.
"""
import datetime as dt
import json
import os
import urllib.request
from html import escape

USER = "rahulagarwal18"
NPM_PACKAGES = ["unmuzzled", "claudecut"]
SKIP_LANGS = {"HTML", "CSS", "SCSS", "Jupyter Notebook", "Dockerfile", "Makefile", "Batchfile", "Procfile"}
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "stats")

BG, LINE, INK, MUTED, ACCENT = "#0e0e0c", "#2a2925", "#edebe4", "#94918a", "#ff7a3d"
LANG_COLORS = ["#ff7a3d", "#ffb37a", "#c9c6bd", "#86a8ff", "#6fd39a", "#c7a0f2"]


def gql(query, **variables):
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def fetch():
    data = gql(
        """query($login: String!) {
          user(login: $login) {
            createdAt
            contributionsCollection {
              contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
            }
            repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
              totalCount
              nodes {
                stargazerCount
                languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } }
              }
            }
          }
        }""",
        login=USER,
    )["user"]
    cal = data["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    repos = data["repositories"]
    langs = {}
    for repo in repos["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            if name not in SKIP_LANGS:
                langs[name] = langs.get(name, 0) + edge["size"]
    return {
        "contributions": cal["totalContributions"],
        "days": days,
        "repos": repos["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos["nodes"]),
        "langs": langs,
        "created": data["createdAt"][:10],
    }


def streaks(days):
    today = dt.date.today().isoformat()
    counts = [d["contributionCount"] for d in days if d["date"] <= today]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    current = 0
    rev = counts[::-1]
    if rev and rev[0] == 0:  # today not counted yet: streak may still be alive from yesterday
        rev = rev[1:]
    for c in rev:
        if not c:
            break
        current += 1
    return current, longest


def npm_downloads():
    total = 0
    for pkg in NPM_PACKAGES:
        try:
            with urllib.request.urlopen(f"https://api.npmjs.org/downloads/point/last-year/{pkg}", timeout=20) as r:
                total += json.load(r).get("downloads", 0)
        except Exception:
            pass
    return total


def devto_articles():
    try:
        req = urllib.request.Request("https://dev.to/api/articles?username=rahul_agarwal18&per_page=1000",
                                     headers={"User-Agent": "profile-stats-cards"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return len(json.load(r))
    except Exception:
        return 0


def fmt(n):
    return f"{n:,}"


def card(width, height, title, body):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
<style>
  .t {{ font: 600 15px 'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif; fill: {ACCENT}; letter-spacing: .04em; }}
  .l {{ font: 400 13px 'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif; fill: {MUTED}; }}
  .v {{ font: 600 22px 'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif; fill: {INK}; }}
  .s {{ font: 400 12px 'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif; fill: {INK}; }}
  .fade {{ animation: fade .8s ease-out both; }}
  @keyframes fade {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: none; }} }}
</style>
<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="14" fill="{BG}" stroke="{LINE}"/>
<text x="24" y="36" class="t">{escape(title.upper())}</text>
{body}
</svg>
"""


def overview_svg(s, npm_total, articles):
    _, longest = streaks(s["days"])
    years = max(1, (dt.date.today() - dt.date.fromisoformat(s["created"])).days // 365)
    items = [
        ("Contributions (last year)", fmt(s["contributions"])),
        ("npm downloads", fmt(npm_total)),
        ("Public repositories", fmt(s["repos"])),
        ("Longest streak", f"{longest} days"),
        ("Technical articles", fmt(articles)),
        ("Years on GitHub", f"{years}+"),
    ]
    cells = []
    for i, (label, value) in enumerate(items):
        x = 24 + (i % 3) * 152
        y = 82 + (i // 3) * 70
        cells.append(
            f'<g class="fade" style="animation-delay:{i * 90}ms">'
            f'<text x="{x}" y="{y}" class="v">{escape(value)}</text>'
            f'<text x="{x}" y="{y + 22}" class="l">{escape(label)}</text></g>'
        )
    updated = dt.date.today().strftime("%d %b %Y")
    cells.append(f'<text x="24" y="226" class="l" style="font-size:11px">Updated {updated} · generated in this repo</text>')
    return card(495, 242, "GitHub at a glance", "\n".join(cells))


def languages_svg(langs):
    grand = sum(langs.values()) or 1
    ranked = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)
    top = [(n, v) for n, v in ranked if v / grand >= 0.01][:5]   # hide <1% noise
    other = grand - sum(v for _, v in top)
    if other / grand >= 0.005:
        top.append(("Other", other))
    total = grand
    parts, x = [], 24.0
    bar_w = 447
    for i, (name, size) in enumerate(top):
        w = bar_w * size / total
        parts.append(f'<rect x="{x:.1f}" y="58" width="{max(w - 2, 1):.1f}" height="10" rx="3" fill="{LANG_COLORS[i]}"/>')
        x += w
    for i, (name, size) in enumerate(top):
        cx = 24 + (i % 2) * 230
        cy = 104 + (i // 2) * 34
        parts.append(
            f'<g class="fade" style="animation-delay:{i * 90}ms">'
            f'<circle cx="{cx + 5}" cy="{cy - 5}" r="5" fill="{LANG_COLORS[i]}"/>'
            f'<text x="{cx + 18}" y="{cy}" class="s">{escape(name)}</text>'
            f'<text x="{cx + 200}" y="{cy}" class="l" text-anchor="end">{100 * size / total:.1f}%</text></g>'
        )
    parts.append('<text x="24" y="226" class="l" style="font-size:11px">By code size across public repos · HTML &amp; CSS excluded</text>')
    return card(495, 242, "Top languages", "\n".join(parts))


def main():
    stats = fetch()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "overview.svg"), "w", encoding="utf-8") as f:
        f.write(overview_svg(stats, npm_downloads(), devto_articles()))
    with open(os.path.join(OUT, "languages.svg"), "w", encoding="utf-8") as f:
        f.write(languages_svg(stats["langs"]))
    print("contributions", stats["contributions"], "| repos", stats["repos"], "| langs", sorted(stats["langs"], key=stats["langs"].get, reverse=True)[:6])


if __name__ == "__main__":
    main()
