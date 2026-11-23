#!/usr/bin/env python3
"""Standalone language/framework/docs scraper — fully self-contained."""
import json, re, time, urllib.request, xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

DEST = Path.home() / ".FlossWare/sources/web-scrape"
UA = {"User-Agent": "FlossWare-corpus/1.0 (research; contact: sfloess)"}
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

try:
    from targets import TARGETS
except ImportError:
    from targets_example import TARGETS

class TextExtractor(HTMLParser):
    """Robust text extraction: only reliably-closed tags (script/style/
    noscript) are skipped via a stack; text inside a main-content region
    (<main>, <article>, role="main") is preferred, falling back to the
    whole page minus script/style. Survives sites with unclosed
    nav/header/footer tags (e.g. go.dev: 5 <nav> opens / 2 closes)."""
    _SKIP = {"script", "style", "noscript"}
    _BLOCK = ("p","div","li","h1","h2","h3","h4","tr","pre","section")
    def __init__(self):
        super().__init__()
        self._all, self._main = [], []
        self._skip_stack, self._in_main = [], 0
        self._title, self._in_title = [], False
    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP: self._skip_stack.append(tag)
        if tag == "title": self._in_title = True
        if tag in ("main","article") or dict(attrs).get("role") == "main":
            self._in_main += 1
    def handle_endtag(self, tag):
        if tag in self._SKIP and tag in self._skip_stack:
            while self._skip_stack:
                if self._skip_stack.pop() == tag: break
        if tag in self._BLOCK:
            self._all.append("\n")
            if self._in_main: self._main.append("\n")
        if tag == "title": self._in_title = False
        if tag in ("main","article") and self._in_main: self._in_main -= 1
    def handle_data(self, data):
        if self._skip_stack: return
        if self._in_title: self._title.append(data)
        self._all.append(data)
        if self._in_main: self._main.append(data)
    def text(self):
        main_body = re.sub(r"\n{3,}", "\n\n", "".join(self._main)).strip()
        all_body = re.sub(r"\n{3,}", "\n\n", "".join(self._all)).strip()
        body = main_body if len(main_body) >= 200 else all_body
        return " ".join("".join(self._title).split()), body

def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def sitemap_urls(url, seen=None):
    seen = seen if seen is not None else set()
    if url in seen: return
    seen.add(url)
    try:
        body = fetch(url)
    except Exception as e:
        print(f"  sitemap failed {url}: {e}", flush=True); return
    try:
        root = ET.fromstring(body)
        for loc in root.findall("sm:sitemap/sm:loc", NS):
            yield from sitemap_urls(loc.text.strip(), seen)
        for loc in root.findall("sm:url/sm:loc", NS):
            yield loc.text.strip()
    except ET.ParseError:
        for m in re.findall(r"<(?:sitemap:)?loc>\s*(https?://[^<\s]+)\s*</(?:sitemap:)?loc>", body):
            yield from sitemap_urls(m, seen)

def scrape(name, sitemap_url, path_filter, max_pages):
    out = DEST / f"raw-{name}"
    out.mkdir(parents=True, exist_ok=True)
    done = {p.stem for p in out.glob("*.json")}
    count = len(done)
    print(f"[{name}] {count} present; enumerating...", flush=True)
    fetched = 0
    for url in sitemap_urls(sitemap_url):
        if fetched >= max_pages: break
        path = urlparse(url).path
        if path_filter and not re.search(path_filter, url): continue
        if url.endswith((".pdf",".png",".jpg",".zip",".xml",".dtd")): continue
        slug = re.sub(r"[^a-zA-Z0-9_-]+","_",path.strip("/"))[:180] or "index"
        slug = f"{urlparse(url).netloc.split('.')[0]}_{slug}"[:190]
        if slug in done: continue
        try:
            html = fetch(url)
        except Exception: continue
        ex = TextExtractor()
        try: ex.feed(html)
        except Exception: continue
        title, text = ex.text()
        if len(text) < 200: continue
        (out / f"{slug}.json").write_text(json.dumps({"url":url,"title":title or path,"content":text[:400_000]}))
        count += 1; fetched += 1
        if fetched % 50 == 0: print(f"[{name}] {count} ({fetched} new)", flush=True)
        time.sleep(1)
    print(f"[{name}] DONE: {count}", flush=True)

# NOTE: keep the __main__ block LAST — TARGETS appended after it are
# invisible to the CLI (that bug silently skipped scrapes twice today).
if __name__ == "__main__":
    import sys
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for name, sitemap, flt, mx in TARGETS:
        if only and only != name: continue
        try: scrape(name, sitemap, flt, mx)
        except Exception as exc: print(f"[{name}] FATAL: {exc}", flush=True)
# Wolfram Research (2026-11-23)
TARGETS += [
    ("mathworld", "https://mathworld.wolfram.com/sitemap.xml", None, 15000),
    ("wolfram-language", "https://reference.wolfram.com/language/sitemap.xml", None, 15000),
    ("wolfram-nks", "https://www.wolframscience.com/sitemap.xml", None, 5000),
]
