"""Generate an SVG card with the user's GitHub stats.

Usage: python stats.py <github_user> <output.svg>
Env:   GITHUB_TOKEN optional, raises the API rate limit
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://api.github.com"


def api(path, token):
    req = urllib.request.Request(API + path, headers={"Accept": "application/vnd.github+json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as res:
        return json.load(res)


def search_count(kind, query, token):
    return api(f"/search/{kind}?per_page=1&q={urllib.parse.quote(query)}", token)["total_count"]


def collect(user):
    token = os.environ.get("GITHUB_TOKEN")
    profile = api(f"/users/{user}", token)
    stars, page = 0, 1
    while batch := api(f"/users/{user}/repos?type=owner&per_page=100&page={page}", token):
        stars += sum(r["stargazers_count"] for r in batch if not r["fork"])
        page += 1
    created = datetime.fromisoformat(profile["created_at"].replace("Z", "+00:00"))
    return {
        "stars": stars,
        "commits": search_count("commits", f"author:{user}", token),
        "prs": search_count("issues", f"author:{user} type:pr", token),
        "issues": search_count("issues", f"author:{user} type:issue", token),
        "repos": profile["public_repos"],
        "followers": profile["followers"],
        "since": created.year,
        "years": datetime.now(timezone.utc).year - created.year,
    }


# 16x16 outline glyphs
ICONS = {
    "stars": "M8 1.5l1.9 4 4.4.5-3.3 3 .9 4.3L8 11.1l-3.9 2.2.9-4.3-3.3-3 4.4-.5z",
    "commits": "M8 5a3 3 0 1 1 0 6 3 3 0 0 1 0-6zM1 8h4M11 8h4",
    "prs": "M5.5 3a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0zM5.5 13a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0zM13.5 13a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0zM4 4.5v7M12 11.5v-5c0-1.5-1-2.5-2.5-2.5H7M8.5 2.5L7 4l1.5 1.5",
    "issues": "M8 1.5a6.5 6.5 0 1 1 0 13 6.5 6.5 0 0 1 0-13zM8 5v3.5M8 11v.5",
    "repos": "M3 2.5h9.5v10H4.5A1.5 1.5 0 0 0 3 14V2.5zM3 14a1.5 1.5 0 0 1 1.5-1.5",
    "followers": "M6 7a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM1.5 14c0-2.5 2-4.5 4.5-4.5s4.5 2 4.5 4.5M11 2.5a2.5 2.5 0 0 1 0 4.5M12.5 9.8c1.3.6 2 2 2 4.2",
}
ROWS = [
    ("stars", "Total Stars", "#f1fa8c"),
    ("commits", "Total Commits", "#50fa7b"),
    ("prs", "Pull Requests", "#8be9fd"),
    ("issues", "Issues", "#ffb86c"),
    ("repos", "Public Repos", "#bd93f9"),
    ("followers", "Followers", "#ff79c6"),
]


def render(user, s):
    rows = []
    for i, (key, label, color) in enumerate(ROWS):
        y = 70 + i * 29
        rows.append(f"""
    <g transform="translate(28 {y})">
      <path d="{ICONS[key]}" fill="none" stroke="{color}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
      <text x="26" y="12.5" class="label">{label}:</text>
      <text x="200" y="12.5" class="value">{s[key]:,}</text>
    </g>""")
    circ = 2 * 3.14159 * 46
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="250" viewBox="0 0 495 250" role="img" aria-label="{user}'s GitHub stats">
  <style>
    .title {{ font: 600 18px 'Segoe UI', Ubuntu, sans-serif; fill: #ff79c6; }}
    .label {{ font: 400 14px 'Segoe UI', Ubuntu, sans-serif; fill: #f8f8f2; }}
    .value {{ font: 700 14px 'Segoe UI', Ubuntu, sans-serif; fill: #f8f8f2; }}
    .big   {{ font: 700 28px 'Segoe UI', Ubuntu, sans-serif; fill: #f8f8f2; }}
    .small {{ font: 400 12px 'Segoe UI', Ubuntu, sans-serif; fill: #6272a4; }}
    .ring  {{ animation: fill 1.2s ease-out; }}
    @keyframes fill {{ from {{ stroke-dashoffset: {circ:.1f}; }} }}
  </style>
  <rect x="0.5" y="0.5" width="494" height="249" rx="10" fill="#282a36" stroke="#44475a"/>
  <text x="28" y="40" class="title">{user}'s GitHub Stats</text>{''.join(rows)}
  <g transform="translate(395 135)">
    <circle r="46" fill="none" stroke="#44475a" stroke-width="7"/>
    <circle r="46" fill="none" stroke="#bd93f9" stroke-width="7" stroke-linecap="round" class="ring"
            stroke-dasharray="{circ:.1f}" stroke-dashoffset="{circ * 0.25:.1f}" transform="rotate(-90)"/>
    <text y="6" text-anchor="middle" class="big">{s['years']}y</text>
    <text y="26" text-anchor="middle" class="small">since {s['since']}</text>
  </g>
</svg>
"""


if __name__ == "__main__":
    user, out = sys.argv[1], sys.argv[2]
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(user, collect(user)))
