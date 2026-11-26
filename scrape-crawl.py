#!/usr/bin/env python3
"""Polite seed crawler for sites without page-level sitemaps.

Same output format as scrape-langs.py (JSON items in
~/.FlossWare/sources/web-scrape/raw-<name>/), so ingestion treats
crawler output identically to sitemap-scraper output.

Usage:
  python3 scrape-crawl.py <name> <allow_regex> <max_pages> <seed_url> [seed_url ...]

  e.g. python3 scrape-crawl.py python '^https://docs\\.python\\.org/3/' 15000 \
           https://docs.python.org/3/

Rules honored (per 01-scraping-prompt.md): 1 req/s per site, official
pages only, proper User-Agent, resumable (skips slugs already on disk).
"""
import json, re, sys, time, urllib.request
from collections import deque
import hashlib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, urldefrag, urljoin

DEST = Path.home() / ".FlossWare/sources/web-scrape"
UA = {"User-Agent": "FlossWare-corpus/1.0 (research; contact: sfloess)"}
SKIP_EXT = (".pdf", ".png", ".jpg", ".zip", ".xml", ".dtd", ".gif", ".svg",
            ".css", ".js", ".woff", ".woff2", ".ttf", ".eot", ".ico")


class PageParser(HTMLParser):
    """Collects page text + hrefs.

    Robust against unclosed nav/header/footer tags (go.dev has 5 <nav>
    opens / 2 closes, which defeated the old counter approach): only
    reliably-closed tags (script/style/noscript) are skipped via a
    stack, and text inside a main-content region (<main>, <article>,
    or role="main") is preferred when present, falling back to
    whole-page text minus script/style.
    """
    _SKIP = {"script", "style", "noscript"}
    _BLOCK = ("p", "div", "li", "h1", "h2", "h3", "h4", "tr", "pre", "section")

    def __init__(self):
        super().__init__()
        self._all, self._main = [], []
        self._skip_stack, self._main_stack = [], []
        self._title, self._in_title = [], False
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_stack.append(tag)
        if tag == "title":
            self._in_title = True
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)
        if tag in ("main", "article") or dict(attrs).get("role") == "main":
            self._main_stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self._SKIP and tag in self._skip_stack:
            while self._skip_stack:
                if self._skip_stack.pop() == tag:
                    break
        if tag in self._BLOCK:
            self._all.append("\n")
            if self._main_stack:
                self._main.append("\n")
        if tag == "title":
            self._in_title = False
        if self._main_stack and tag == self._main_stack[-1]:
            self._main_stack.pop()

    def handle_data(self, data):
        if self._skip_stack:
            return
        if self._in_title:
            self._title.append(data)
        self._all.append(data)
        if self._main_stack:
            self._main.append(data)

    def text(self):
        main_body = re.sub(r"\n{3,}", "\n\n", "".join(self._main)).strip()
        all_body = re.sub(r"\n{3,}", "\n\n", "".join(self._all)).strip()
        body = main_body if len(main_body) >= 200 else all_body
        return " ".join("".join(self._title).split()), body


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def slug_for(url):
    path = urlparse(url).path
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", path.strip("/"))[:180] or "index"
    return f"{urlparse(url).netloc.split('.')[0]}_{slug}"[:190]


def crawl(name, allow, max_pages, seeds):
    out = DEST / f"raw-{name}"
    out.mkdir(parents=True, exist_ok=True)
    allow_re = re.compile(allow)
    seen = set()
    for p in out.glob("*.json"):
        try:
            u = json.loads(p.read_text(errors="replace")).get("url")
            if u:
                seen.add(u)
        except Exception:
            pass
    count = len(seen)
    queue = deque(seeds)
    fetched = 0
    print(f"[{name}] {count} present; crawling seeds {seeds}", flush=True)
    while queue and fetched < max_pages:
        url = queue.popleft()
        url, _ = urldefrag(url)
        if url in seen:
            continue
        seen.add(url)
        if not allow_re.search(url):
            continue
        if url.endswith(SKIP_EXT):
            continue
        slug = slug_for(url)
        try:
            html = fetch(url)
        except Exception as e:
            print(f"[{name}] fetch fail {url}: {e}", flush=True)
            time.sleep(1)
            continue
        parser = PageParser()
        try:
            parser.feed(html)
        except Exception:
            pass
        title, text = parser.text()
        # enqueue in-scope links (resolve relative hrefs against the page URL)
        for href in parser.links:
            if href.startswith(("mailto:", "javascript:", "tel:", "data:")):
                continue
            href = urljoin(url, href)
            href, _ = urldefrag(href)
            if href not in seen and allow_re.search(href) and not href.endswith(SKIP_EXT):
                queue.append(href)
        if len(text) < 200:
            time.sleep(1)
            continue
        f = out / f"{slug}.json"
        if f.exists():
            try:
                if json.loads(f.read_text(errors="replace")).get("url") == url:
                    continue
            except Exception:
                pass
            slug = f"{slug}_{hashlib.sha1(url.encode()).hexdigest()[:8]}"
        (out / f"{slug}.json").write_text(json.dumps(
            {"url": url, "title": title or urlparse(url).path, "content": text[:400_000]}))
        count += 1
        fetched += 1
        if fetched % 50 == 0:
            print(f"[{name}] {count} total ({fetched} new, {len(queue)} queued)", flush=True)
        time.sleep(1)
    print(f"[{name}] DONE: {count} items (fetched {fetched} new this run, "
          f"{len(queue)} unfetched in queue)", flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(2)
    crawl(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4:])
