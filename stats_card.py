"""Draw the stats and languages cards of the profile README from my own GitHub numbers.

The hosted github-readme-stats cards are fetched with someone else's token, so they only see
public work: about a tenth of my commits, and hardly any of my Swift. This script reads GitHub's
GraphQL API with STATS_TOKEN, a classic token of mine with the `repo` and `read:user` scopes, so
private repositories count too. Both cards keep the github-readme-stats layout:

- assets/stats.svg: stars, commits, pull requests, issues and repositories; the ring shows the
  contributions of the last year instead of a rank.
- assets/top-langs.svg: the six largest languages across the repositories I own (forks left
  out), by bytes of code. Documents and notebooks are not code and are left out (HIDDEN).
  Percentages are of those six, as on the hosted card.

Usage:
    python stats_card.py assets              # reads the numbers with STATS_TOKEN
    python stats_card.py assets numbers.json # draws saved numbers

Without a token, or when GitHub answers with an error, the existing cards are left as they are
and the script exits 0, so a bad day never blanks the README.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from html import escape
from pathlib import Path

ACCENT = "#6E60D8"
TEXT = "#8B949E"
HIDDEN = {"TeX", "MDX", "HTML", "Jupyter Notebook"}
LANGUAGES_SHOWN = 6

STATS_QUERY = """
query {
  viewer {
    name
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, first: 100) {
      nodes { stargazerCount }
    }
    pullRequests { totalCount }
    issues { totalCount }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions }
      commitContributionsByRepository(maxRepositories: 100) { repository { id } }
      pullRequestContributionsByRepository(maxRepositories: 100) { repository { id } }
      issueContributionsByRepository(maxRepositories: 100) { repository { id } }
      pullRequestReviewContributionsByRepository(maxRepositories: 100) { repository { id } }
    }
  }
}
"""

LANGUAGES_QUERY = """
query($after: String) {
  viewer {
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, after: $after) {
      pageInfo { hasNextPage endCursor }
      nodes {
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

# Octicons, as github-readme-stats draws them.
ICONS = {
    "star": "M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25zm0 2.445L6.615 5.5a.75.75 0 01-.564.41l-3.097.45 2.24 2.184a.75.75 0 01.216.664l-.528 3.084 2.769-1.456a.75.75 0 01.698 0l2.77 1.456-.53-3.084a.75.75 0 01.216-.664l2.24-2.183-3.096-.45a.75.75 0 01-.564-.41L8 2.694v.001z",
    "commits": "M1.643 3.143L.427 1.927A.25.25 0 000 2.104V5.75c0 .138.112.25.25.25h3.646a.25.25 0 00.177-.427L2.715 4.215a6.5 6.5 0 11-1.18 4.458.75.75 0 10-1.493.154 8.001 8.001 0 101.6-5.684zM7.75 4a.75.75 0 01.75.75v2.992l2.028.812a.75.75 0 01-.557 1.392l-2.5-1A.75.75 0 017 8.25v-3.5A.75.75 0 017.75 4z",
    "prs": "M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 113 2.122v5.256a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 011.5 3.25zM11 2.5h-1V4h1a1 1 0 011 1v5.628a2.251 2.251 0 101.5 0V5A2.5 2.5 0 0011 2.5zm1 10.25a.75.75 0 111.5 0 .75.75 0 01-1.5 0zM3.75 12a.75.75 0 100 1.5.75.75 0 000-1.5z",
    "issues": "M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8zm9 3a1 1 0 11-2 0 1 1 0 012 0zm-.25-6.25a.75.75 0 00-1.5 0v3.5a.75.75 0 001.5 0v-3.5z",
    "contributed": "M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8zM5 12.25v3.25a.25.25 0 00.4.2l1.45-1.087a.25.25 0 01.3 0L8.6 15.7a.25.25 0 00.4-.2v-3.25a.25.25 0 00-.25-.25h-3.5a.25.25 0 00-.25.25z",
}

ROWS = [
    ("star", "Total Stars Earned:", "stars"),
    ("commits", "Total Commits (last year):", "commits"),
    ("prs", "Total PRs:", "prs"),
    ("issues", "Total Issues:", "issues"),
    ("contributed", "Contributed to (last year):", "contributed"),
]

STYLE = f"""
    .header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: {ACCENT}; animation: fadeIn 0.8s ease-in-out forwards; }}
    .stat {{ font: 700 14px 'Segoe UI', Ubuntu, "Helvetica Neue", Sans-Serif; fill: {TEXT}; }}
    .lang-name {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TEXT}; }}
    .stagger {{ opacity: 0; animation: fadeIn 0.3s ease-in-out forwards; }}
    .icon {{ fill: {ACCENT}; display: block; }}
    .ring-rim {{ stroke: {ACCENT}; fill: none; stroke-width: 6; opacity: 0.2; }}
    .ring {{ stroke: {ACCENT}; fill: none; stroke-width: 6; stroke-linecap: round; opacity: 0.8;
      stroke-dasharray: 251.33; animation: ringIn 1s forwards ease-in-out; }}
    .ring-value {{ font: 800 20px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TEXT}; }}
    .ring-label {{ font: 400 10px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TEXT}; }}
    @supports(-moz-appearance: auto) {{ .header {{ font-size: 15.5px; }} .stat {{ font-size: 12px; }} }}
    @keyframes ringIn {{ from {{ stroke-dashoffset: 251.33; }} to {{ stroke-dashoffset: 0; }} }}
    @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
"""


def graphql(token: str, query: str, variables: dict | None = None) -> dict:
    """Run one GraphQL query and return its data."""
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-stats-card"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"][0].get("message", "GraphQL error"))
    return payload["data"]


def fetch_stats(token: str) -> dict:
    viewer = graphql(token, STATS_QUERY)["viewer"]
    work = viewer["contributionsCollection"]
    repositories = {
        node["repository"]["id"]
        for key in (
            "commitContributionsByRepository",
            "pullRequestContributionsByRepository",
            "issueContributionsByRepository",
            "pullRequestReviewContributionsByRepository",
        )
        for node in work[key]
    }
    return {
        "name": viewer["name"],
        "stars": sum(node["stargazerCount"] for node in viewer["repositories"]["nodes"]),
        "commits": work["totalCommitContributions"] + work["restrictedContributionsCount"],
        "prs": viewer["pullRequests"]["totalCount"],
        "issues": viewer["issues"]["totalCount"],
        "contributed": len(repositories),
        "contributions": work["contributionCalendar"]["totalContributions"],
    }


def fetch_languages(token: str) -> list[dict]:
    """Bytes per language across every repository I own, largest first."""
    totals: dict[str, dict] = {}
    after = None
    while True:
        page = graphql(token, LANGUAGES_QUERY, {"after": after})["viewer"]["repositories"]
        for repository in page["nodes"]:
            for edge in repository["languages"]["edges"]:
                name = edge["node"]["name"]
                entry = totals.setdefault(name, {"name": name, "color": edge["node"]["color"], "size": 0})
                entry["size"] += edge["size"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    return sorted(totals.values(), key=lambda entry: -entry["size"])


def short(value: int) -> str:
    """1234 -> 1.2k, as github-readme-stats writes it."""
    if value < 1000:
        return str(value)
    return f"{value / 1000:.1f}".rstrip("0").rstrip(".") + "k"


def draw_stats(numbers: dict) -> str:
    """The stats card, 467 x 195 like the hosted one."""
    rows = []
    for index, (icon, label, key) in enumerate(ROWS):
        rows.append(
            f"""
      <g transform="translate(0, {index * 25})">
        <g class="stagger" style="animation-delay: {450 + index * 150}ms" transform="translate(25, 0)">
          <svg class="icon" viewBox="0 0 16 16" width="16" height="16"><path fill-rule="evenodd" d="{ICONS[icon]}"/></svg>
          <text class="stat" x="25" y="12.5">{label}</text>
          <text class="stat" x="219.01" y="12.5">{short(numbers[key])}</text>
        </g>
      </g>"""
        )
    name = escape(numbers["name"])
    summary = ", ".join(f"{label} {numbers[key]}" for _, label, key in ROWS)
    contributions = numbers["contributions"]
    return f"""<svg width="467" height="195" viewBox="0 0 467 195" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="titleId descId">
  <title id="titleId">{name}'s GitHub Stats</title>
  <desc id="descId">{summary}. {contributions} contributions in the last year.</desc>
  <style>{STYLE}</style>
  <g transform="translate(25, 35)"><text x="0" y="0" class="header">{name}'s GitHub Stats</text></g>
  <g transform="translate(0, 55)">
    <g transform="translate(390.5, 47.5)">
      <circle class="ring-rim" cx="-10" cy="8" r="40"/>
      <circle class="ring" cx="-10" cy="8" r="40" transform="rotate(-90 -10 8)"/>
      <text class="ring-value" x="-10" y="8" text-anchor="middle">{short(contributions)}</text>
      <text class="ring-label" x="-10" y="24" text-anchor="middle">contributions</text>
    </g>{''.join(rows)}
  </g>
</svg>
"""


def draw_languages(languages: list[dict]) -> str:
    """The compact languages card, 300 x 165 like the hosted one."""
    shown = [entry for entry in languages if entry["name"] not in HIDDEN][:LANGUAGES_SHOWN]
    total = sum(entry["size"] for entry in shown) or 1
    bar, items, x = [], [], 0.0
    for index, entry in enumerate(shown):
        share = entry["size"] / total
        color = entry["color"] or TEXT
        width = share * 250
        bar.append(f'<rect mask="url(#bar)" x="{x:.2f}" y="0" width="{width:.2f}" height="8" fill="{color}"/>')
        x += width
        column, row = divmod(index, 3)
        items.append(
            f"""
      <g transform="translate({column * 150}, {25 + row * 25})">
        <g class="stagger" style="animation-delay: {450 + row * 150}ms">
          <circle cx="5" cy="6" r="5" fill="{color}"/>
          <text class="lang-name" x="15" y="10">{escape(entry['name'])} {share * 100:.2f}%</text>
        </g>
      </g>"""
        )
    summary = ", ".join(f"{entry['name']} {entry['size'] / total * 100:.2f}%" for entry in shown)
    return f"""<svg width="300" height="165" viewBox="0 0 300 165" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="langTitle langDesc">
  <title id="langTitle">Most Used Languages</title>
  <desc id="langDesc">{escape(summary)}</desc>
  <style>{STYLE}</style>
  <g transform="translate(25, 35)"><text x="0" y="0" class="header">Most Used Languages</text></g>
  <g transform="translate(25, 55)">
    <mask id="bar"><rect x="0" y="0" width="250" height="8" fill="white" rx="5"/></mask>
    {''.join(bar)}{''.join(items)}
  </g>
</svg>
"""


def main() -> int:
    out = Path(sys.argv[1])
    if len(sys.argv) > 2:
        data = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        stats, languages = data["stats"], data["languages"]
    else:
        token = os.environ.get("STATS_TOKEN")
        if not token:
            print("::warning::STATS_TOKEN is not set; kept the previous cards")
            return 0
        try:
            stats, languages = fetch_stats(token), fetch_languages(token)
        except Exception as error:  # a bad day keeps yesterday's cards
            print(f"::warning::kept the previous cards: {error}")
            return 0
    out.mkdir(parents=True, exist_ok=True)
    (out / "stats.svg").write_text(draw_stats(stats), encoding="utf-8")
    (out / "top-langs.svg").write_text(draw_languages(languages), encoding="utf-8")
    print(f"wrote {out}/stats.svg and {out}/top-langs.svg: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
