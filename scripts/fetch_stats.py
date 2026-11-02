"""Pull public GitHub stats for the profile SVG.

Runs inside the scheduled Action with GITHUB_TOKEN, or locally with no token
(unauthenticated, 60 req/h). Writes stats.json; make_svg.py renders it.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OWNER = os.environ.get("GH_OWNER", "eliutot")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = Path(__file__).with_name("stats.json")


def get(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"{OWNER}-profile-readme"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    try:
        user = get(f"https://api.github.com/users/{OWNER}")
        repos, page = [], 1
        while True:
            batch = get(f"https://api.github.com/users/{OWNER}/repos?per_page=100&page={page}&sort=pushed")
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

    stats = {
        "owner": OWNER,
        "repos": len(own),
        "stars": stars,
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "last_push": pushed[0][:10] if pushed and pushed[0] else "—",
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    OUT.write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
