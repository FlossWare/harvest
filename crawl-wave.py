#!/usr/bin/env python3
"""Parallel crawler wave for sites without sitemaps (the 44 dead-sitemap
targets). One crawl per domain at a time, all domains in parallel.
Targets that fail just move on (user directive 2026-11-23)."""
import subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SOURCES = Path.home() / ".FlossWare/sources"

# (name, allow_regex, max_pages, seeds...)
WAVE = [
    ("gnu-bash-manual", r"^https://www\.gnu\.org/software/bash/manual/", 1200, ["https://www.gnu.org/software/bash/manual/"]),
    ("gnu-gawk-manual", r"^https://www\.gnu\.org/software/gawk/manual/", 1200, ["https://www.gnu.org/software/gawk/manual/"]),
    ("gnu-sed-manual", r"^https://www\.gnu\.org/software/sed/manual/", 500, ["https://www.gnu.org/software/sed/manual/"]),
    ("gnu-grep-manual", r"^https://www\.gnu\.org/software/grep/manual/", 500, ["https://www.gnu.org/software/grep/manual/"]),
    ("gnu-coreutils-manual", r"^https://www\.gnu\.org/software/coreutils/manual/", 1500, ["https://www.gnu.org/software/coreutils/manual/"]),
    ("gnu-findutils-manual", r"^https://www\.gnu\.org/software/findutils/manual/", 400, ["https://www.gnu.org/software/findutils/manual/"]),
    ("gnu-make-manual", r"^https://www\.gnu\.org/software/make/manual/", 1200, ["https://www.gnu.org/software/make/manual/"]),
    ("gnu-bison-manual", r"^https://www\.gnu\.org/software/bison/manual/", 600, ["https://www.gnu.org/software/bison/manual/"]),
    ("man7-pages", r"^https://man7\.org/", 3000, ["https://man7.org/linux/man-pages/"]),
    ("gcc-docs", r"^https://gcc\.gnu\.org/onlinedocs/", 3000, ["https://gcc.gnu.org/onlinedocs/"]),
    ("gdb-docs", r"^https://sourceware\.org/gdb/", 2000, ["https://sourceware.org/gdb/current/onlinedocs/gdb/"]),
    ("perldoc", r"^https://perldoc\.perl\.org/", 5000, ["https://perldoc.perl.org/"]),
    ("haskell-docs", r"^https://www\.haskell\.org/", 2000, ["https://www.haskell.org/documentation/"]),
    ("typescript-docs", r"^https://www\.typescriptlang\.org/docs/", 3000, ["https://www.typescriptlang.org/docs/"]),
    ("swift-docs", r"^https://docs\.swift\.org/", 3000, ["https://docs.swift.org/"]),
    ("erlang-docs", r"^https://www\.erlang\.org/doc/", 3000, ["https://www.erlang.org/docs/"]),
    ("openbsd-docs", r"^https://www\.openbsd\.org/", 2000, ["https://www.openbsd.org/faq/"]),
    ("netbsd-docs", r"^https://www\.netbsd\.org/docs/", 2000, ["https://www.netbsd.org/docs/"]),
    ("dragonflybsd-docs", r"^https://www\.dragonflybsd\.org/docs/", 1500, ["https://www.dragonflybsd.org/docs/"]),
    ("zsh-docs", r"^https://zsh\.sourceforge\.io/Docs/", 2000, ["https://zsh.sourceforge.io/Docs/"]),
    ("lua-docs", r"^https://www\.lua\.org/(pil|manual|doc)/", 1500, ["https://www.lua.org/pil/", "https://www.lua.org/manual/"]),
    ("fish-docs", r"^https://fishshell\.com/docs/", 1500, ["https://fishshell.com/docs/"]),
    ("nim-docs", r"^https://nim-lang\.org/", 1500, ["https://nim-lang.org/documentation.html"]),
    ("r-cran-docs", r"^https://cran\.r-project\.org/(manuals|faqs)/", 1000, ["https://cran.r-project.org/manuals.html"]),
    ("rails-guides", r"^https://guides\.rubyonrails\.org/", 3000, ["https://guides.rubyonrails.org/"]),
    ("grails-docs", r"^https://docs\.grails\.org/", 2000, ["https://docs.grails.org/"]),
    ("swi-prolog-docs", r"^https://www\.swi-prolog\.org/pldoc/", 2000, ["https://www.swi-prolog.org/pldoc/doc_for?object=manual"]),
    ("schemers-docs", r"^https://schemers\.org/", 1000, ["https://schemers.org/"]),
    ("javacc-docs", r"^https://javacc\.github\.io/javacc/", 1000, ["https://javacc.github.io/javacc/"]),
    ("antlr-docs", r"^https://www\.antlr\.org/", 1000, ["https://www.antlr.org/"]),
    ("util-linux-docs", r"^https://util-linux\.sourceforge\.net/", 500, ["https://util-linux.sourceforge.net/"]),
    ("kernel-man-pages", r"^https://www\.kernel\.org/doc/man-pages/", 1000, ["https://www.kernel.org/doc/man-pages/"]),
    ("freepascal-docs", r"^https://www\.freepascal\.org/docs/", 2000, ["https://www.freepascal.org/docs.html"]),
    ("cppreference", r"^https://en\.cppreference\.com/w/", 15000, ["https://en.cppreference.com/w/"]),
    ("beanshell-docs", r"^https://www\.beanshell\.org/", 500, ["https://www.beanshell.org/"]),
    ("lwn", r"^https://lwn\.net/", 3000, ["https://lwn.net/"]),
    ("sklearn-docs", r"^https://scikit-learn\.org/stable/", 4000, ["https://scikit-learn.org/stable/"]),
    ("fastai-course", r"^https://course\.fast\.ai/", 1000, ["https://course.fast.ai/"]),
    ("deeplearningbook", r"^https://www\.deeplearningbook\.org/", 500, ["https://www.deeplearningbook.org/"]),
]

# GNU manuals share gnu.org — run them sequentially in one lane.
GNU = [t for t in WAVE if t[0].startswith("gnu-")]
OTHERS = [t for t in WAVE if not t[0].startswith("gnu-")]


def run_target(t):
    name, allow, mx, seeds = t
    log = f"/tmp/crawl-{name}.log"
    try:
        with open(log, "w") as f:
            subprocess.run(
                [sys.executable, str(SOURCES / "scrape-crawl.py"), name, allow, str(mx), *seeds],
                cwd=str(SOURCES), stdout=f, stderr=subprocess.STDOUT)
        n = len(list((SOURCES / "web-scrape" / f"raw-{name}").glob("*.json")))
        print(f"[{name}] done, {n} items", flush=True)
    except Exception as e:
        print(f"[{name}] DRIVER ERROR: {e}", flush=True)


def run_gnu_lane():
    for t in GNU:
        run_target(t)


print(f"{len(WAVE)} crawl targets ({len(GNU)} GNU sequential, {len(OTHERS)} parallel)", flush=True)
with ThreadPoolExecutor(max_workers=13) as ex:
    futures = [ex.submit(run_gnu_lane)] + [ex.submit(run_target, t) for t in OTHERS]
    for f in futures:
        f.result()
print("CRAWL WAVE DONE", flush=True)
