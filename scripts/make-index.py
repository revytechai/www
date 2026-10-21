#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Build the organisation repository index from the GitHub API."""
import datetime
import json
import os
import re
import sys
import urllib.request

# A GitHub organisation login: alphanumerics and single hyphens, 1-39 chars.
# The value is interpolated into a URL, so it is validated rather than trusted.
ORG_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")

API_ROOT = "https://api.github.com"


def api_root() -> str:
    """The only host this program will talk to."""
    return API_ROOT


def fetch(org: str) -> list:
    url = api_root() + "/orgs/" + org + "/repos?per_page=100&sort=updated"
    if not url.startswith("https://"):
        raise ValueError("refusing a non-https URL")
    token = os.environ.get("GH_TOKEN", "")
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "cloudbsd-org-pages",
        },
    )
    # The URL is a fixed https API root plus a regex-validated org login, and
    # the scheme is asserted above. bandit and semgrep both want their
    # marker on the offending line, so it is one line and both are named.
    with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310 -- fixed https API root, regex-validated org login, scheme asserted; nosemgrep: dynamic-urllib-use-detected
        return json.load(resp)


def build(org: str) -> dict:
    out = []
    for r in fetch(org):
        if r.get("archived") or r.get("fork"):
            continue
        out.append(
            {
                "name": r["name"],
                "description": r.get("description") or "",
                "url": r["html_url"],
                "lang": r.get("language") or "",
                "topics": r.get("topics") or [],
                "stars": r.get("stargazers_count", 0),
                "updated": (r.get("pushed_at") or "")[:10],
            }
        )
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    return {"generated": now.isoformat(), "repos": out}


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: make-index.py <org> [--js]", file=sys.stderr)
        return 2
    org = sys.argv[1]
    if not ORG_RE.match(org):
        print(f"invalid organisation name: {org!r}", file=sys.stderr)
        return 2
    data = build(org)
    if "--js" in sys.argv:
        sys.stdout.write("window.__REPOS__ = ")
        json.dump(data, sys.stdout)
        sys.stdout.write(";\n")
    else:
        json.dump(data, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
