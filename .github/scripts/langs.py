"""Generate an SVG bar chart of the most used languages across the user's repos.

Usage: python langs.py <github_user> <output.svg>
Env:   LANGS_TOKEN  optional PAT (repo scope) to include private repos
       GITHUB_TOKEN fallback token, public repos only
"""
import json
import os
import sys
import urllib.request
from html import escape

TOP_N = 8
IGNORED = set()  # e.g. {"HTML", "Jupyter Notebook"} to hide languages

COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "Java": "#b07219", "PHP": "#4F5D95", "HTML": "#e34c26", "CSS": "#663399",
    "Shell": "#89e051", "C#": "#178600", "C++": "#f34b7d", "C": "#555555",
    "Go": "#00ADD8", "Rust": "#dea584", "Kotlin": "#A97BFF", "Dart": "#00B4AB",
    "Vue": "#41b883", "SCSS": "#c6538c", "PLSQL": "#dad8d8", "TSQL": "#e38c00",
    "Dockerfile": "#384d54", "Jupyter Notebook": "#DA5B0B", "Blade": "#f7523f",
    "Hack": "#878787", "Ruby": "#701516", "Swift": "#F05138",
    "Pug": "#a86454", "PowerShell": "#5391fe",
}
FALLBACK = ["#ff79c6", "#bd93f9", "#8be9fd", "#50fa7b", "#ffb86c", "#f1fa8c"]


def api(url, token):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as res:
        return json.load(res)


def repos(user, token, private):
    base = ("https://api.github.com/user/repos?affiliation=owner"
            if private else f"https://api.github.com/users/{user}/repos?type=owner")
    page = 1
    while True:
        batch = api(f"{base}&per_page=100&page={page}", token)
        if not batch:
            return
        yield from (r for r in batch if not r["fork"] and not r["archived"])
        page += 1


def collect(user):
    pat = os.environ.get("LANGS_TOKEN")
    token = pat or os.environ.get("GITHUB_TOKEN")
    totals = {}
    for repo in repos(user, token, private=bool(pat)):
        for lang, size in api(repo["languages_url"], token).items():
            if lang not in IGNORED:
                totals[lang] = totals.get(lang, 0) + size
    return sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]


def render(langs):
    width, row_h, top = 495, 30, 58
    height = top + row_h * len(langs) + 14
    total = sum(size for _, size in langs) or 1
    bar_x, bar_w = 150, 270
    rows = []
    for i, (lang, size) in enumerate(langs):
        pct = size / total * 100
        color = COLORS.get(lang, FALLBACK[i % len(FALLBACK)])
        y = top + i * row_h
        w = max(bar_w * pct / 100, 3)
        rows.append(f"""
  <g>
    <circle cx="30" cy="{y + 5}" r="6" fill="{color}"/>
    <text x="44" y="{y + 10}" class="lang">{escape(lang)}</text>
    <rect x="{bar_x}" y="{y}" width="{bar_w}" height="10" rx="5" fill="#44475a"/>
    <rect x="{bar_x}" y="{y}" width="{w:.1f}" height="10" rx="5" fill="{color}" class="bar"/>
    <text x="{bar_x + bar_w + 12}" y="{y + 10}" class="pct">{pct:.1f}%</text>
  </g>""")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Most used languages">
  <style>
    .title {{ font: 600 18px 'Segoe UI', Ubuntu, sans-serif; fill: #ff79c6; }}
    .lang  {{ font: 400 13px 'Segoe UI', Ubuntu, sans-serif; fill: #f8f8f2; }}
    .pct   {{ font: 600 12px 'Segoe UI', Ubuntu, sans-serif; fill: #bd93f9; }}
    .bar   {{ transform-box: fill-box; transform-origin: left; animation: grow .8s ease-out; }}
    @keyframes grow {{ from {{ transform: scaleX(0); }} }}
  </style>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="#282a36" stroke="#44475a"/>
  <text x="24" y="36" class="title">Most Used Languages</text>{''.join(rows)}
</svg>
"""


if __name__ == "__main__":
    user, out = sys.argv[1], sys.argv[2]
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(collect(user)))
