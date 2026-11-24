#!/usr/bin/env python3
"""Polite gap re-scraper: fetches URLs from a gap manifest into the corpus.

Usage: gap-rescrape.py <gap.jsonl> <corpus_root>

- One record per URL; output <corpus_root>/<category>/<sha1(url)[:16]>.json
- Resumable: existing output files are skipped.
- Politeness: per-domain sequential with delay, 3 domains in parallel,
  timeout, bounded retries with backoff, honors Retry-After on 429.
- Skips *.example.com / test URLs.
"""
import hashlib
import json
import os
import sys
import threading
import time
from html.parser import HTMLParser
from queue import Queue

import requests

PER_DOMAIN_DELAY = 1.5
DOMAIN_WORKERS = 3
TIMEOUT = 30
MAX_TRIES = 3
UA = "FlossWare-corpus-rescrape/1.0 (personal knowledge base; contact: sfloess)"

SKIP_DOMAINS = ("example.com", "test-pipeline.example.com")


class TextExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript", "svg", "head"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._skip = 0
        self.title = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False
        if tag in ("p", "div", "br", "li", "h1", "h2", "h3", "h4", "pre", "tr"):
            self.parts.append("\n")

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_title:
            self.title = (self.title or "") + data
        else:
            self.parts.append(data)


def extract(rec, corpus_root):
    url = rec["url"]
    category = (rec.get("category") or "uncategorized").strip().replace(" ", "-") or "uncategorized"
    outdir = os.path.join(corpus_root, category)
    os.makedirs(outdir, exist_ok=True)
    name = hashlib.sha1(url.encode()).hexdigest()[:16] + ".json"
    outpath = os.path.join(outdir, name)
    if os.path.exists(outpath):
        return "skip"
    try:
        with requests.Session() as s:
            s.headers["User-Agent"] = UA
            resp = None
            for attempt in range(MAX_TRIES):
                try:
                    resp = s.get(url, timeout=TIMEOUT, allow_redirects=True)
                except requests.RequestException:
                    time.sleep(5 * (attempt + 1))
                    continue
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", "30") or 30)
                    time.sleep(min(retry_after, 120))
                    continue
                if resp.status_code >= 500:
                    time.sleep(10 * (attempt + 1))
                    continue
                break
            if resp is None or resp.status_code != 200:
                return f"fail:{resp.status_code if resp is not None else 'error'}"
        ctype = resp.headers.get("Content-Type", "")
        if "html" in ctype:
            p = TextExtractor()
            p.feed(resp.text)
            content = " ".join("".join(p.parts).split())
            title = (p.title or "").strip() or rec.get("title")
        else:
            content = resp.text[:2_000_000]
            title = rec.get("title")
        record = {
            "url": resp.url if resp.url.startswith("http") else url,
            "requested_url": url,
            "title": title,
            "content": content,
            "category": rec.get("category"),
            "content_type": ctype,
            "http_status": 200,
            "_scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "_source": "gap-rescrape-2026-11-22",
        }
        tmp = outpath + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False)
        os.replace(tmp, outpath)
        return "ok"
    except Exception as e:
        return f"error:{type(e).__name__}"


def domain_worker(q, results, lock):
    while True:
        item = q.get()
        if item is None:
            q.task_done()
            return
        domain, recs = item
        last_fetch = 0.0
        ok = fail = skip = 0
        for rec in recs:
            # politeness: wait between requests to same domain
            wait = PER_DOMAIN_DELAY - (time.time() - last_fetch)
            if wait > 0:
                time.sleep(wait)
            last_fetch = time.time()
            status = extract(rec, CORPUS_ROOT)
            if status == "ok":
                ok += 1
            elif status == "skip":
                skip += 1
            else:
                fail += 1
            results["total"] += 1
            n = results["total"]
            if n % 100 == 0:
                with lock:
                    print(f"  {n}/{results['grand']} done "
                          f"(ok={results['ok']}, fail={results['fail']}, skip={results['skip']})",
                          flush=True)
            if status == "ok":
                results["ok"] += 1
            elif status == "skip":
                results["skip"] += 1
            else:
                results["fail"] += 1
                with lock:
                    print(f"    {status} {rec['url'][:90]}", flush=True)
        with lock:
            print(f"domain {domain}: ok={ok} fail={fail} skip={skip}", flush=True)
        q.task_done()


def main():
    gap_path, corpus_root = sys.argv[1], sys.argv[2]
    global CORPUS_ROOT
    CORPUS_ROOT = corpus_root

    by_domain = {}
    for line in open(gap_path, encoding="utf-8"):
        rec = json.loads(line)
        url = rec["url"]
        if any(d in url for d in SKIP_DOMAINS):
            continue
        try:
            domain = url.split("/")[2]
        except IndexError:
            continue
        by_domain.setdefault(domain, []).append(rec)

    # largest domains first so long tails finish early
    items = sorted(by_domain.items(), key=lambda kv: -len(kv[1]))
    grand = sum(len(v) for _, v in items)
    print(f"{grand} urls across {len(items)} domains", flush=True)

    results = {"total": 0, "ok": 0, "fail": 0, "skip": 0, "grand": grand}
    lock = threading.Lock()
    q = Queue()
    for it in items:
        q.put(it)
    threads = []
    for _ in range(min(DOMAIN_WORKERS, len(items))):
        q.put(None)
    for _ in range(min(DOMAIN_WORKERS, len(items))):
        t = threading.Thread(target=domain_worker, args=(q, results, lock), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    print(f"FINAL: ok={results['ok']} fail={results['fail']} skip={results['skip']} "
          f"of {grand}", flush=True)


if __name__ == "__main__":
    main()
