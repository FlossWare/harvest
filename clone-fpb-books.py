#!/usr/bin/env python3
"""Parse the free-programming-books catalog and shallow-clone the
GitHub-hosted books (bounded, deduped, polite to github.com).

Usage: python3 clone-fpb-books.py [max_repos]
"""
import re
import subprocess
import sys
from pathlib import Path

REPOS = Path.home() / ".FlossWare/sources/web-scrape/repos"
CATALOG = REPOS / "free-programming-books/books/free-programming-books.md"
MAX_REPOS = int(sys.argv[1]) if len(sys.argv) > 1 else 500
MAX_WORKERS = 2

existing = {p.name for p in REPOS.iterdir() if p.is_dir()}

urls = set()
for md in sorted((REPOS / "free-programming-books/books").glob("*.md")):
    urls.update(re.findall(r'https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)', md.read_text(errors="replace")))

SKIP_PREFIX = ("EbookFoundation/",)
candidates = []
for u in sorted(urls):
    owner, repo = u.split("/")
    repo = repo.removesuffix(".git")
    if u in SKIP_PREFIX or owner in ("github", "features"):
        continue
    dirname = f"fpb-{repo}"
    if dirname in existing or repo in existing:
        continue
    candidates.append((u, dirname))

print(f"{len(urls)} GitHub URLs in catalog; {len(candidates)} not yet cloned; "
      f"capping at {MAX_REPOS}", flush=True)

done = 0
for u, dirname in candidates[:MAX_REPOS]:
    try:
        r = subprocess.run(
            ["git", "clone", "--depth", "1", "-q", f"https://github.com/{u}", dirname],
            cwd=str(REPOS), timeout=300)
        if r.returncode == 0:
            done += 1
            existing.add(dirname)
            if done % 25 == 0:
                print(f"  {done} cloned...", flush=True)
        else:
            print(f"  FAIL {u}", flush=True)
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT {u}", flush=True)

print(f"FPB DONE: {done} book repos cloned (of {len(candidates)} candidates)", flush=True)
