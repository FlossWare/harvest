#!/usr/bin/env python3
"""Build/merge the master URL index for the scraped corpus.

Usage: build-url-master.py <master.jsonl> <scan_root> [seed.jsonl ...]

- Loads the existing master (if present) and seed manifests
  (provenance-tagged) into a URL-keyed dict.
- Walks scan_root, extracting url/link/_source fields from JSON records
  and line-by-line from JSONL files.
- Writes merged master: one record per unique URL with provenance list.
Run with nice; safe to re-run (idempotent merge by URL, existing master
is always loaded first and merged, never replaced).
"""
import json
import os
import sys
from multiprocessing import Pool

MAX_FILE_BYTES = 10 * 1024 * 1024  # skip giant single-record JSON files
MAX_LINE_BYTES = 10 * 1024 * 1024  # skip pathological JSONL lines


def _collect(rec, out):
    """Append (url, title, category) for each dict record in rec."""
    records = rec if isinstance(rec, list) else [rec]
    for r in records:
        if not isinstance(r, dict):
            continue
        for k in ("url", "link", "_source"):
            v = r.get(k)
            if isinstance(v, str) and v.startswith("http"):
                out.append((v, r.get("title"), r.get("category")))
                break


def extract_from_file(path):
    """Return ([(url, title, category)...], lines_skipped, file_skipped)."""
    file_skipped = 0
    lines_skipped = 0
    out = []
    if path.endswith(".jsonl"):
        # JSONL: one JSON record per line; parse line by line so
        # multi-record files contribute all their URLs. NO file-size
        # cap here — large JSONL is the common case and dropping a
        # whole file silently loses every URL in it.
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if len(line) > MAX_LINE_BYTES:
                        lines_skipped += 1
                        continue
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        lines_skipped += 1
                        continue
                    _collect(rec, out)
        except OSError:
            return [], lines_skipped, 1
    else:
        try:
            if os.path.getsize(path) > MAX_FILE_BYTES:
                return [], 0, 1
        except OSError:
            return [], 0, 1
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                rec = json.loads(f.read(MAX_FILE_BYTES))
        except Exception:
            return [], 0, 1
        _collect(rec, out)
    return out, lines_skipped, file_skipped


def main():
    if len(sys.argv) < 3:
        print(f"usage: {sys.argv[0]} <master.jsonl> <scan_root> [seed.jsonl ...]",
              file=sys.stderr)
        sys.exit(2)
    master_path, scan_root = sys.argv[1], sys.argv[2]
    seeds = sys.argv[3:]

    if not os.path.isdir(scan_root):
        print(f"error: scan_root {scan_root!r} is not a directory", file=sys.stderr)
        sys.exit(2)

    master = {}  # url -> record

    def load_seed(path, default_prov):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if not isinstance(r, dict):
                    continue
                u = r.get("url")
                if not isinstance(u, str) or not u.startswith("http"):
                    continue
                rec = master.setdefault(u, {"url": u})
                for k in ("category", "title", "content_hash", "fetched_at",
                          "http_status", "last_checked_at", "doc_id"):
                    if r.get(k) is not None and k not in rec:
                        rec[k] = r.get(k)
                prov = r.get("provenance") or [default_prov]
                if isinstance(prov, str):
                    prov = [prov]
                rec.setdefault("provenance", [])
                for p in prov:
                    if p not in rec["provenance"]:
                        rec["provenance"].append(p)

    # Existing master is always merged first (never replaced).
    if os.path.exists(master_path):
        load_seed(master_path, "existing-master")
    for seed in seeds:
        if not os.path.isfile(seed):
            print(f"error: seed {seed!r} not found", file=sys.stderr)
            sys.exit(2)
        load_seed(seed, "seed-file")

    # Collect JSON files to scan, excluding the master and seed files
    # themselves (they sit under scan_root in some layouts, and
    # re-ingesting them would tag every existing URL with false
    # provenance)
    exclude = {os.path.abspath(master_path)} | {os.path.abspath(s) for s in seeds}
    paths = []
    for dirpath, dirnames, filenames in os.walk(scan_root):
        dirnames.sort()
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            if (fn.endswith(".json") or fn.endswith(".jsonl")) \
                    and os.path.abspath(p) not in exclude:
                paths.append(p)
    sys.stderr.write(f"scanning {len(paths)} json/jsonl files under {scan_root}\n")

    scanned = 0
    skipped_files = 0
    skipped_lines = 0
    with Pool(4) as pool:
        for found, ls, fs in pool.imap_unordered(extract_from_file, paths, chunksize=256):
            scanned += 1
            skipped_lines += ls
            skipped_files += fs
            if scanned % 200000 == 0:
                sys.stderr.write(f"  {scanned}/{len(paths)} files, {len(master)} urls"
                                 f" (skipped files={skipped_files} lines={skipped_lines})\n")
            for url, title, category in found:
                rec = master.setdefault(url, {"url": url})
                if title and not rec.get("title"):
                    rec["title"] = title
                if category and not rec.get("category"):
                    rec["category"] = category
                rec.setdefault("provenance", [])
                if "web-scrape-corpus" not in rec["provenance"]:
                    rec["provenance"].append("web-scrape-corpus")

    tmp = master_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for u in sorted(master):
            f.write(json.dumps(master[u], ensure_ascii=False) + "\n")
    os.replace(tmp, master_path)
    print(f"master: {len(master)} unique urls -> {master_path} "
          f"(scanned {scanned} files; skipped files={skipped_files} "
          f"lines={skipped_lines})")


if __name__ == "__main__":
    main()
