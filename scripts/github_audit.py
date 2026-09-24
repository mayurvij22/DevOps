#!/usr/bin/env python3
"""
GitHub audit script: finds STALE repositories and repos WITHOUT branch protection.

Typical platform-support task: "Give me a list of repos nobody has touched in
90 days so we can decommission them" or "Which repos are missing protection on main?"

Interview talking points shown here:
  1. Authentication with a token from an environment variable (never hardcoded)
  2. PAGINATION: GitHub returns max 100 items per page; follow the "next" link
  3. RATE LIMITS: check X-RateLimit-Remaining and wait if we run out
  4. Output a CSV report the team can open in Excel

Usage:
  pip install requests
  export GITHUB_TOKEN=ghp_xxx          # token with repo read access
  python scripts/github_audit.py --owner YOUR_USERNAME --days 90
  python scripts/github_audit.py --owner some-org --org --days 90
"""
import argparse
import csv
import os
import sys
import time
from datetime import datetime, timezone

import requests

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")  # GHES: https://HOST/api/v3


def get(session, url, params=None):
    """GET with rate-limit handling."""
    while True:
        resp = session.get(url, params=params, timeout=30)
        remaining = int(resp.headers.get("X-RateLimit-Remaining", "1"))
        if resp.status_code in (403, 429) and remaining == 0:
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(reset - int(time.time()), 1)
            print(f"Rate limit hit. Waiting {wait}s...", file=sys.stderr)
            time.sleep(wait)
            continue
        return resp


def list_repos(session, owner, is_org):
    """Yield every repo, following pagination links."""
    url = f"{API}/orgs/{owner}/repos" if is_org else f"{API}/users/{owner}/repos"
    params = {"per_page": 100}
    while url:
        resp = get(session, url, params)
        resp.raise_for_status()
        yield from resp.json()
        url = resp.links.get("next", {}).get("url")  # None on the last page
        params = None  # the "next" URL already contains the query string


def is_protected(session, owner, repo, branch):
    resp = get(session, f"{API}/repos/{owner}/{repo}/branches/{branch}")
    return resp.ok and resp.json().get("protected", False)


def main():
    parser = argparse.ArgumentParser(description="Audit GitHub repos")
    parser.add_argument("--owner", required=True, help="GitHub user or org name")
    parser.add_argument("--org", action="store_true", help="owner is an organization")
    parser.add_argument("--days", type=int, default=90, help="stale threshold in days")
    parser.add_argument("--out", default="repo_audit.csv")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("ERROR: set the GITHUB_TOKEN environment variable")

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    })

    now = datetime.now(timezone.utc)
    rows = []
    for repo in list_repos(session, args.owner, args.org):
        pushed = datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00"))
        days_idle = (now - pushed).days
        branch = repo["default_branch"]
        rows.append({
            "repo": repo["name"],
            "archived": repo["archived"],
            "last_push": pushed.date().isoformat(),
            "days_idle": days_idle,
            "stale": days_idle > args.days,
            "default_branch": branch,
            "branch_protected": is_protected(session, args.owner, repo["name"], branch),
        })

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else ["repo"])
        writer.writeheader()
        writer.writerows(rows)

    stale = sum(r["stale"] for r in rows)
    unprotected = sum(not r["branch_protected"] for r in rows)
    print(f"Scanned {len(rows)} repos | stale (> {args.days} days): {stale} "
          f"| default branch unprotected: {unprotected} | report: {args.out}")


if __name__ == "__main__":
    main()
