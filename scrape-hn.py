#!/usr/bin/env python3
"""Scrape Hacker News stories via the official Algolia API (hn.algolia.com).

Fetches top/front-page stories over the past 3 years by date, plus their
comment trees (bounded). Output: JSON items in raw-hackernews/.
"""
import json, time, urllib.request
from pathlib import Path

OUT = Path.home() / ".FlossWare/sources/web-scrape/raw-hackernews"
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "FlossWare-corpus/1.0 (research; contact: sfloess)"}
BASE = "https://hn.algolia.com/api/v1"
MAX_STORIES = 20000
MAX_COMMENTS_PER_STORY = 50


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


saved = len(list(OUT.glob("*.json")))
print(f"{saved} present; fetching HN stories by date...", flush=True)
page = 0
fetched = 0
while fetched < MAX_STORIES:
    try:
        d = fetch(f"{BASE}/search_by_date?tags=story&hitsPerPage=50&page={page}")
    except Exception as e:
        print(f"page {page} fail: {e}", flush=True)
        break
    hits = d.get("hits", [])
    if not hits or page >= d.get("nbPages", 0):
        break
    for h in hits:
        sid = str(h.get("objectID"))
        f = OUT / f"hn_{sid}.json"
        fetched += 1
        if f.exists() or int(h.get("points") or 0) < 10:
            continue
        # bounded comment fetch
        comments = []
        try:
            item = fetch(f"{BASE}/items/{sid}")
            kids = (item.get("children") or [])[:MAX_COMMENTS_PER_STORY]
            for k in kids:
                if k.get("text"):
                    comments.append(k["text"])
        except Exception:
            pass
        f.write_text(json.dumps({
            "url": f"https://news.ycombinator.com/item?id={sid}",
            "title": h.get("title") or "",
            "content": (h.get("title") or "") + "\n"
                        + (h.get("story_text") or h.get("url") or "") + "\n\n"
                        + "\n\n".join(comments)[:400_000],
            "points": h.get("points"), "author": h.get("author"),
            "created_at": h.get("created_at"), "link": h.get("url"),
            "num_comments": h.get("num_comments"),
        }))
        saved += 1
        if saved % 100 == 0:
            print(f"  {saved} saved ({fetched} scanned)", flush=True)
    page += 1
    time.sleep(0.5)
print(f"HN DONE: {saved}", flush=True)
