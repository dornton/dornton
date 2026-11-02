"""Pull public GitHub stats for the profile SVG.

Two sources: REST for counts and repos, GraphQL for the contribution calendar
(REST has no endpoint for it). Runs inside the scheduled Action with
GITHUB_TOKEN, or locally with no token (unauthenticated REST, no calendar).
Writes stats.json; make_svg.py renders it.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OWNER = os.environ.get("GH_OWNER", "eliutot")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = Path(__file__).with_name("stats.json")
API = "https://api.github.com"
CONTRIB_URL = f"https://github.com/users/{OWNER}/contributions"

CALENDAR = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def headers():
    h = {"Accept": "application/vnd.github+json", "User-Agent": f"{OWNER}-profile-readme"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


def get(url):
    req = urllib.request.Request(url, headers=headers())
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def graphql(query, variables):
    """None when there is no token, or the token cannot read the field."""
    if not TOKEN:
        print("note: no GITHUB_TOKEN, skipping the contribution calendar", file=sys.stderr)
        return None
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        f"{API}/graphql", data=body,
        headers={**headers(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        print(f"warn: graphql failed ({exc}); heatmap will render empty", file=sys.stderr)
        return None


def tally(days):
    """(weeks of 7 counts, total, current streak, best day) from [(date, count)]."""
    days = sorted(days)
    if not days:
        return [], 0, 0, "—"

    # GitHub's graph starts every column on Sunday
    pad = (datetime.strptime(days[0][0], "%Y-%m-%d").weekday() + 1) % 7
    flat = [0] * pad + [c for _, c in days]
    weeks = [flat[i:i + 7] + [0] * (7 - len(flat[i:i + 7]))
             for i in range(0, len(flat), 7)][-53:]  # the grid is exactly 53 columns wide

    streak = 0
    for i, (_, count) in enumerate(reversed(days)):
        if count > 0:
            streak += 1
        elif i == 0:
            continue  # today may simply not have registered yet
        else:
            break

    best = max(days, key=lambda d: d[1])
    return weeks, sum(c for _, c in days), streak, best[0] if best[1] else "—"


def from_graphql():
    """First choice: exact counts, but needs a token with user:read scope."""
    data = graphql(CALENDAR, {"login": OWNER})
    if not data or data.get("errors"):
        return [], 0, 0, "—"
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return tally([(d["date"], d["contributionCount"])
                  for w in cal["weeks"] for d in w["contributionDays"]])


LEVEL_COUNTS = {1: 1, 2: 3, 3: 6, 4: 10}  # only used when a tooltip is missing


def from_html():
    """Fallback: the public profile graph needs no token at all."""
    try:
        req = urllib.request.Request(CONTRIB_URL, headers={
            "User-Agent": f"{OWNER}-profile-readme", "Accept": "text/html"})
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8", "replace")
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        print(f"warn: could not read the contribution page ({exc})", file=sys.stderr)
        return [], 0, 0, "—"

    tips = {}
    for cell_id, text in re.findall(
            r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', html):
        digits = re.match(r"(\d+)", text.strip())
        tips[cell_id] = int(digits.group(1)) if digits else 0

    days = []
    for cell in re.findall(r"<td[^>]*>", html):
        date = re.search(r'data-date="([\d-]+)"', cell)
        if not date:
            continue
        cell_id = re.search(r'id="([^"]+)"', cell)
        count = tips.get(cell_id.group(1)) if cell_id else None
        if count is None:
            level = re.search(r'data-level="(\d)"', cell)
            count = LEVEL_COUNTS.get(int(level.group(1)), 0) if level else 0
        days.append((date.group(1), count))

    print(f"note: calendar from the public page ({len(days)} days)", file=sys.stderr)
    return tally(days)


def calendar():
    weeks, total, streak, best = from_graphql()
    if weeks:
        return weeks, total, streak, best
    return from_html()


def main():
    try:
        user = get(f"{API}/users/{OWNER}")
        repos, page = [], 1
        while True:
            batch = get(f"{API}/users/{OWNER}/repos?per_page=100&page={page}&sort=pushed")
            repos += batch
            if len(batch) < 100:
                break
            page += 1
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError) as exc:
        # fail loudly: a silently stale SVG is worse than a red action
        print(f"error: could not read GitHub API: {exc}", file=sys.stderr)
        return 1

    own = [r for r in repos if not r.get("fork")]
    stars = sum(r.get("stargazers_count", 0) for r in own)
    pushed = sorted((r.get("pushed_at") or "" for r in own), reverse=True)

    langs = {}
    for r in own:
        name = r.get("language")
        if name:
            langs[name] = langs.get(name, 0) + 1
    top_langs = sorted(langs.items(), key=lambda kv: (-kv[1], kv[0]))[:4]

    recent = [r["name"] for r in sorted(own, key=lambda r: r.get("pushed_at") or "", reverse=True)
              if r["name"].lower() != OWNER.lower()][:2]

    weeks, total, streak, best_day = calendar()

    stats = {
        "owner": OWNER,
        "repos": len(own),
        "stars": stars,
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "last_push": pushed[0][:10] if pushed and pushed[0] else "—",
        "contrib_total": total,
        "streak": streak,
        "best_day": best_day,
        "contributions": weeks,
        "langs": [[name, count] for name, count in top_langs],
        "recent": recent,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    OUT.write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    summary = {k: v for k, v in stats.items() if k != "contributions"}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"calendar: {len(weeks)} weeks · {total} contributions · {streak} day streak")
    return 0


if __name__ == "__main__":
    sys.exit(main())
