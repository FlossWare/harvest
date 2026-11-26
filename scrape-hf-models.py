#!/usr/bin/env python3
"""Scrape Hugging Face model cards for the top-N most-downloaded models.

Uses the public HF API (1 req/s) to list models, then fetches each model's
README (model card) via the raw resolve endpoint. Output: JSON items in
~/.FlossWare/sources/web-scrape/raw-hf-modelcards/ with url/title/content.
"""
import json, time, urllib.request
from pathlib import Path

OUT = Path.home() / ".FlossWare/sources/web-scrape/raw-hf-modelcards"
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "FlossWare-corpus/1.0 (research; contact: sfloess)"}
TOP = 2000


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


skip = 0
saved = len(list(OUT.glob("*.json")))
print(f"{saved} present; listing top {TOP} models...", flush=True)
listed = 0
while listed < TOP:
    url = (f"https://huggingface.co/api/models?sort=downloads&direction=-1"
           f"&limit=100&full=false&skip={skip}")
    try:
        models = json.loads(fetch(url))
    except Exception as e:
        print(f"list fail at skip={skip}: {e}", flush=True)
        break
    if not models:
        break
    for m in models:
        mid = m["id"]
        listed += 1
        slug = mid.replace("/", "_")
        f = OUT / f"{slug}.json"
        if f.exists():
            continue
        try:
            readme = fetch(f"https://huggingface.co/{mid}/raw/main/README.md")
        except Exception:
            readme = ""
        tags = m.get("tags") or []
        f.write_text(json.dumps({
            "url": f"https://huggingface.co/{mid}",
            "title": mid,
            "content": readme[:400_000] if readme else "(no model card)",
            "downloads": m.get("downloads"),
            "likes": m.get("likes"),
            "pipeline_tag": m.get("pipeline_tag"),
            "tags": tags,
        }))
        saved += 1
        if saved % 100 == 0:
            print(f"  {saved} saved ({listed} listed)", flush=True)
    skip += 100
    time.sleep(1)
print(f"HF MODELCARDS DONE: {saved}", flush=True)
