"""Draw the stats card of the profile README from my own GitHub numbers.

The hosted github-readme-stats card is fetched with someone else's token, so it only sees public
work: about a tenth of my commits. This script reads GitHub's GraphQL API with STATS_TOKEN, a
classic token of mine with the `repo` and `read:user` scopes, so private repositories count too.
It draws the card in the same layout as github-readme-stats; the ring shows the contributions of
the last year instead of a rank.

Usage:
    python stats_card.py assets/stats.svg              # reads the numbers with STATS_TOKEN
    python stats_card.py assets/stats.svg numbers.json  # draws saved numbers

Without a token, or when GitHub answers with an error, the existing card is left as it is and
the script exits 0, so a bad day never blanks the README.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from html import escape

QUERY = """
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

ACCENT = "#6E60D8"
TEXT = "#8B949E"

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


def fetch(token: str) -> dict:
    """Read my numbers from GitHub's GraphQL API."""
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-stats-card"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"][0].get("message", "GraphQL error"))
    viewer = payload["data"]["viewer"]
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


def short(value: int) -> str:
    """1234 -> 1.2k, as github-readme-stats writes it."""
    if value < 1000:
        return str(value)
    return f"{value / 1000:.1f}".rstrip("0").rstrip(".") + "k"


def draw(numbers: dict) -> str:
    """Return the card as SVG, 467 x 195 like the hosted card."""
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
  <style>
    .header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: {ACCENT}; animation: fadeIn 0.8s ease-in-out forwards; }}
    .stat {{ font: 700 14px 'Segoe UI', Ubuntu, "Helvetica Neue", Sans-Serif; fill: {TEXT}; }}
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
  </style>
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


def main() -> int:
    out = sys.argv[1]
    if len(sys.argv) > 2:
        with open(sys.argv[2], encoding="utf-8") as f:
            numbers = json.load(f)
    else:
        token = os.environ.get("STATS_TOKEN")
        if not token:
            print("::warning::STATS_TOKEN is not set; kept the previous stats card")
            return 0
        try:
            numbers = fetch(token)
        except Exception as error:  # a bad day keeps yesterday's card
            print(f"::warning::kept the previous stats card: {error}")
            return 0
    with open(out, "w", encoding="utf-8") as f:
        f.write(draw(numbers))
    print(f"wrote {out}: {numbers}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
