#!/usr/bin/env python3
"""Parallel scrape driver — one scrape at a time per DOMAIN, all domains
in parallel (per 01-scraping-prompt.md politeness rules).

- Loads every TARGETS entry from scrape-langs.py
- Skips targets whose raw-<name>/ dir already has content (dedup)
- Skips targets whose sitemap doesn't respond (failure -> move on)
- Groups remaining targets by domain; runs each domain's targets
  sequentially, all domains concurrently (bounded pool)
- Per-target logs at /tmp/scrape-<name>.log
"""
import importlib.util
import subprocess
import sys
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

SOURCES = Path.home() / ".FlossWare/sources"
DEST = SOURCES / "web-scrape"
UA = {"User-Agent": "FlossWare-corpus/1.0 (research; contact: sfloess)"}
MAX_DOMAIN_WORKERS = 12

spec = importlib.util.spec_from_file_location("sl", SOURCES / "scrape-langs.py")
sl = importlib.util.module_from_spec(spec)
sys.modules["sl"] = sl
spec.loader.exec_module(sl)


def raw_count(name):
    d = DEST / f"raw-{name}"
    return len(list(d.glob("*.json"))) if d.is_dir() else 0


def sitemap_ok(url):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200
    except Exception:
        return False


eligible, skipped_done, skipped_dead = [], [], []
for name, sitemap, flt, mx in sl.TARGETS:
    if (DEST / f"raw-{name}" / ".done").exists():
        skipped_done.append(name)
        continue
    if not sitemap_ok(sitemap):
        skipped_dead.append(name)
        continue
    eligible.append((name, urlparse(sitemap).netloc))

by_domain = defaultdict(list)
for name, domain in eligible:
    by_domain[domain].append(name)

print(f"TARGETS total: {len(sl.TARGETS)}", flush=True)
print(f"already scraped (skip): {len(skipped_done)}: {', '.join(sorted(skipped_done))}", flush=True)
print(f"sitemap dead (skip): {len(skipped_dead)}: {', '.join(sorted(skipped_dead))}", flush=True)
print(f"eligible: {len(eligible)} targets across {len(by_domain)} domains", flush=True)
for d, names in sorted(by_domain.items()):
    print(f"  {d}: {', '.join(names)}", flush=True)


def run_domain(domain):
    for name in by_domain[domain]:
        log = f"/tmp/scrape-{name}.log"
        try:
            with open(log, "w") as f:
                r = subprocess.run(
                    [sys.executable, str(SOURCES / "scrape-langs.py"), name],
                    cwd=str(SOURCES), stdout=f, stderr=subprocess.STDOUT)
            print(f"[{name}] exit {r.returncode}", flush=True)
            if r.returncode == 0:
                (DEST / f"raw-{name}" / ".done").write_text("ok")
        except Exception as e:
            print(f"[{name}] DRIVER ERROR: {e}", flush=True)


with ThreadPoolExecutor(max_workers=MAX_DOMAIN_WORKERS) as ex:
    list(ex.map(run_domain, list(by_domain)))
print("ALL DOMAINS DONE", flush=True)
