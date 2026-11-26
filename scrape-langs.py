#!/usr/bin/env python3
"""Standalone language/framework/docs scraper — fully self-contained."""
import hashlib
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
    try:
        from targets_example import TARGETS
    except ImportError:
        # no targets file — the inline TARGETS += blocks below still work
        TARGETS = []

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
        self._skip_stack, self._in_main, self._main_stack = [], 0, []
        self._title, self._in_title = [], False
    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP: self._skip_stack.append(tag)
        if tag == "title": self._in_title = True
        if tag in ("main","article") or dict(attrs).get("role") == "main":
            self._in_main += 1
            self._main_stack.append(tag)
    def handle_endtag(self, tag):
        if tag in self._SKIP and tag in self._skip_stack:
            while self._skip_stack:
                if self._skip_stack.pop() == tag: break
        if tag in self._BLOCK:
            self._all.append("\n")
            if self._in_main: self._main.append("\n")
        if tag == "title": self._in_title = False
        # close the main region only on the tag that opened it (a
        # <div role="main"> must be closed by </div>, and a stray
        # </article> must not decrement a counter another tag opened)
        if self._main_stack and tag == self._main_stack[-1]:
            self._main_stack.pop()
            self._in_main -= 1
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
        data = r.read()
    if data[:2] == b"\x1f\x8b":  # gzip body (wireshark.org serves sitemap gzipped)
        import gzip
        data = gzip.decompress(data)
    return data.decode("utf-8", "replace")

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
        # namespace-agnostic: some sites use the ancient Google sitemap
        # namespace (http://www.google.com/schemas/sitemap/0.84 — e.g.
        # wireshark.org) instead of sitemaps.org/0.9
        for el in root.iter():
            tag = el.tag.rsplit("}", 1)[-1]
            if tag == "sitemap":
                for child in el:
                    if child.tag.rsplit("}", 1)[-1] == "loc" and child.text:
                        yield from sitemap_urls(child.text.strip(), seen)
            elif tag == "url":
                for child in el:
                    if child.tag.rsplit("}", 1)[-1] == "loc" and child.text:
                        yield child.text.strip()
    except ET.ParseError:
        # malformed XML: regex out the <loc> entries. Recurse only for
        # sitemap-index files — page URLs must be yielded directly, not
        # fetched as sitemaps (fetching every page as a "sitemap" is
        # impolite and yields nothing).
        is_index = "sitemapindex" in body[:2000].lower()
        for m in re.findall(r"<(?:sitemap:)?loc>\s*(https?://[^<\s]+)\s*</(?:sitemap:)?loc>", body):
            if m in seen:
                continue
            seen.add(m)
            if is_index:
                yield from sitemap_urls(m, seen)
            else:
                yield m

def scrape(name, sitemap_url, path_filter, max_pages):
    out = DEST / f"raw-{name}"
    out.mkdir(parents=True, exist_ok=True)
    done = {p.stem for p in out.glob("*.json")}
    count = len(done)
    print(f"[{name}] {count} present; enumerating...", flush=True)
    fetched = 0
    fails = 0
    for url in sitemap_urls(sitemap_url):
        if fetched >= max_pages: break
        path = urlparse(url).path
        if path_filter and not re.search(path_filter, url): continue
        if path.lower().endswith((".pdf",".png",".jpg",".jpeg",".gif",".zip",".xml",".dtd")): continue
        slug = re.sub(r"[^a-zA-Z0-9_-]+","_",path.strip("/"))[:180] or "index"
        slug = f"{urlparse(url).netloc.split('.')[0]}_{slug}"[:190]
        sf = out / f"{slug}.json"
        if sf.exists():
            try:
                if json.loads(sf.read_text(errors="replace")).get("url") == url:
                    continue
            except Exception:
                pass
            slug = f"{slug}_{hashlib.sha1(url.encode()).hexdigest()[:8]}"
            if (out / f"{slug}.json").exists():
                continue
        try:
            html = fetch(url)
        except Exception:
            # stay polite even when failing — hammering through failures
            # at full speed looks like an attack and prolongs throttling
            # (wireshark.org/cloudflare dropped 44K pages this way)
            fails += 1
            time.sleep(1)
            if fails % 100 == 0:
                print(f"[{name}] WARNING: {fails} fetch failures so far", flush=True)
            continue
        ex = TextExtractor()
        try: ex.feed(html)
        except Exception: continue
        title, text = ex.text()
        if len(text) < 200: continue
        (out / f"{slug}.json").write_text(json.dumps({"url":url,"title":title or path,"content":text[:400_000]}))
        count += 1; fetched += 1
        if fetched % 50 == 0: print(f"[{name}] {count} ({fetched} new)", flush=True)
        time.sleep(1)
    print(f"[{name}] DONE: {count} (fetch failures: {fails})", flush=True)

# Wolfram Research (2026-11-23)
TARGETS += [
    ("mathworld", "https://mathworld.wolfram.com/sitemap.xml", None, 15000),
    ("wolfram-language", "https://reference.wolfram.com/language/sitemap.xml", None, 15000),
    ("wolfram-nks", "https://www.wolframscience.com/sitemap.xml", None, 5000),
]
# Kali Linux (2026-11-24)
TARGETS += [
    ("kali-docs", "https://www.kali.org/sitemap.xml", None, 20000),
]
# Networking tools (2026-11-24)
# NB: wireshark.org's sitemap is 50K URLs — 46K are mailing-list
# archives; /docs/ is the actual documentation (~1.9K pages).
TARGETS += [
    ("wireshark-docs", "https://www.wireshark.org/sitemap.xml", r"wireshark\.org/docs/", 5000),
    ("wireshark-lists", "https://www.wireshark.org/sitemap.xml", r"wireshark\.org/lists/", 50000),
    ("netbird-docs", "https://docs.netbird.io/sitemap.xml", None, 10000),
    ("wireguard-docs", "https://www.wireguard.com/sitemap.xml", None, 5000),
]
# VPN / security / productivity tools (2026-11-24)
# Authy + Trello apps are closed-source: docs only (Trello docs already
# covered via the Atlassian wave). FreeOTP docs live in repo READMEs.
TARGETS += [
    ("openvpn-docs", "https://openvpn.net/sitemap.xml", None, 15000),
    ("bitwarden-docs", "https://bitwarden.com/sitemap.xml", None, 15000),
    ("authy-docs", "https://developers.twilio.com/sitemap.xml", r"/authy/", 10000),
    ("notion-docs", "https://developers.notion.com/sitemap.xml", None, 10000),
]

# NOTE: keep the __main__ block LAST — TARGETS appended after it are
# invisible to the CLI (that bug silently skipped scrapes twice).
if __name__ == "__main__":
    import sys
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for name, sitemap, flt, mx in TARGETS:
        if only and only != name: continue
        try: scrape(name, sitemap, flt, mx)
        except Exception as exc: print(f"[{name}] FATAL: {exc}", flush=True)
