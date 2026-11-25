#!/usr/bin/env python3
"""Per-PDF metadata manifest for a corpus (change detection).

Walks every *.pdf under the configured roots and writes one JSONL line
per file:
  {path, size, sha256, mtime, magic_ok}
magic_ok = file starts with %PDF (catches ciphertext masquerading as
PDFs — e.g. client-side-encrypted Drive exports — and truncated
downloads). Unreadable files produce {path, error} records instead of
aborting the run.

Config (env):
  HARVEST_PDF_ROOTS    colon-separated roots (default ~/corpus/public:~/corpus/private)
  HARVEST_PDF_MANIFEST output path (default ~/corpus/pdf-manifest.jsonl)

Output is written to <out>.tmp then atomically moved into place.
Re-run any time; an ingestion ledger can diff successive manifests to
find new/changed/removed PDFs. Hashing runs under nice with a worker
pool, streaming in chunks (no whole-file reads).
"""
import hashlib, json, os, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOTS = [Path(p) for p in
         (os.environ.get("HARVEST_PDF_ROOTS")
          or f"{Path.home() / 'corpus/public'}:{Path.home() / 'corpus/private'}").split(":")
         if p.strip()]
OUT = Path(os.environ.get("HARVEST_PDF_MANIFEST")
           or Path.home() / "corpus/pdf-manifest.jsonl")
WORKERS = 8


def _init_worker():
    # nice ONCE per worker process — os.nice(10) is additive, so calling
    # it per file would creep to the cap (19)
    try:
        os.nice(10)
    except OSError:
        pass


def hash_one(p):
    p = Path(p)
    try:
        st = p.stat()
        with open(p, "rb") as f:
            magic = f.read(4)
            h = hashlib.file_digest(f, "sha256").hexdigest()
        return {"path": str(p), "size": st.st_size, "sha256": h,
                "mtime": st.st_mtime, "magic_ok": magic == b"%PDF"}
    except OSError as e:
        return {"path": str(p), "error": repr(e)}


def _walk_err(exc):
    print(f"  walk error: {exc}", file=sys.stderr, flush=True)


def collect_pdfs():
    # os.walk(followlinks=True), NOT rglob — stores with symlinked
    # subdirectories are silently skipped by Path.rglob (it refuses to
    # descend into symlinked dirs; a real run missed 3,151 of 10,427
    # PDFs that `find -L` sees). followlinks can loop on symlink
    # cycles, so directories are pruned by (dev, ino).
    pdfs = []
    seen_dirs = set()
    for root in ROOTS:
        if not root.exists():
            print(f"root missing, skipped: {root}", file=sys.stderr, flush=True)
            continue
        try:
            st = os.stat(root)
            seen_dirs.add((st.st_dev, st.st_ino))
        except OSError as exc:
            _walk_err(exc)
            continue
        for dirpath, dirs, names in os.walk(root, followlinks=True,
                                            onerror=_walk_err):
            pruned = []
            for d in dirs:
                try:
                    dst = os.stat(os.path.join(dirpath, d))
                except OSError:
                    continue
                key = (dst.st_dev, dst.st_ino)
                if key not in seen_dirs:
                    seen_dirs.add(key)
                    pruned.append(d)
            dirs[:] = pruned
            for n in names:
                if n.lower().endswith(".pdf"):
                    p = Path(dirpath) / n
                    if p.is_file():
                        pdfs.append(str(p))
    return sorted(set(pdfs))


def main():
    pdfs = collect_pdfs()
    print(f"{len(pdfs)} PDFs to manifest", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_name(OUT.name + ".tmp")
    n = bad = errs = 0
    with tmp.open("w") as f, ProcessPoolExecutor(WORKERS,
                                                 initializer=_init_worker) as pool:
        for rec in pool.map(hash_one, pdfs, chunksize=32):
            f.write(json.dumps(rec) + "\n")
            n += 1
            if "error" in rec:
                errs += 1
            else:
                bad += not rec["magic_ok"]
            if n % 1000 == 0:
                print(f"  {n}/{len(pdfs)}", flush=True)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(OUT)
    print(f"PDF MANIFEST DONE: {n} files, {bad} failed magic check, "
          f"{errs} unreadable", flush=True)


if __name__ == "__main__":
    main()
