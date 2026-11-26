#!/usr/bin/env python3
"""Polite arXiv category scraper via the official export API.

Usage: python3 scrape-arxiv-cat.py <category> [category ...]
  e.g. python3 scrape-arxiv-cat.py quant-ph cs.AI cs.LG stat.ML cs.NE

Writes JSON items to ~/.FlossWare/sources/web-scrape/raw-arxiv-<cat>/
same shape as other raw-* scrapes. 3s between API pages (arXiv etiquette),
100 results per page, resumable via .progress.json per category.
"""
import json, sys, time, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path

DEST = Path.home() / ".FlossWare/sources/web-scrape"
BASE = "https://export.arxiv.org/api/query"
UA = {"User-Agent": "FlossWare-corpus/1.0 (research; contact: sfloess)"}
NS = {"a": "http://www.w3.org/2005/Atom"}
PER_PAGE = 100
MAX_PER_CAT = 20000
RATE = 3


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def scrape_cat(cat):
    out = DEST / f"raw-arxiv-{cat.replace('/', '-')}"
    out.mkdir(parents=True, exist_ok=True)
    prog_file = out / ".progress.json"
    start = 0
    if prog_file.exists():
        try:
            start = json.loads(prog_file.read_text()).get("start", 0)
        except ValueError:
            start = 0
    print(f"[{cat}] resuming at result {start}", flush=True)
    total = None
    while total is None or start < min(total, MAX_PER_CAT):
        url = (f"{BASE}?search_query=cat:{cat}&start={start}"
               f"&max_results={PER_PAGE}&sortBy=submittedDate&sortOrder=descending")
        for attempt in range(3):
            try:
                body = fetch(url)
                break
            except Exception as e:
                print(f"[{cat}] fetch fail (attempt {attempt+1}): {e}", flush=True)
                time.sleep(30)
        else:
            print(f"[{cat}] giving up at {start}", flush=True)
            return
        root = ET.fromstring(body)
        entries = root.findall("a:entry", NS)
        if not entries:
            break
        if total is None:
            tt = root.find("{http://a9.com/-/spec/opensearch/1.1/}totalResults")
            total = int(tt.text) if tt is not None else 0
            print(f"[{cat}] {total} total results", flush=True)
        for e in entries:
            aid = e.find("a:id", NS).text.split("/abs/")[-1]
            title = " ".join(e.find("a:title", NS).text.split())
            abstract = " ".join((e.find("a:summary", NS).text or "").split())
            authors = [a.find("a:name", NS).text for a in e.findall("a:author", NS)]
            pub = e.find("a:published", NS).text
            (out / f"{aid.replace('/', '_')}.json").write_text(json.dumps({
                "url": f"https://arxiv.org/abs/{aid}", "title": title,
                "content": f"{title}\n\n{abstract}",
                "authors": authors, "published": pub, "category": cat}))
        start += len(entries)
        prog_file.write_text(json.dumps({"start": start, "total": total}))
        print(f"[{cat}] {start}/{total}", flush=True)
        time.sleep(RATE)
    print(f"[{cat}] DONE", flush=True)


if __name__ == "__main__":
    for cat in sys.argv[1:]:
        try:
            scrape_cat(cat)
        except Exception as e:
            print(f"[{cat}] FATAL: {e}", flush=True)
