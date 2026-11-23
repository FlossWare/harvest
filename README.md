# harvest

Polite, resumable corpus-harvesting toolkit — turn docs sites, official
APIs, bulk dumps, and git repos into one uniform JSON corpus for
retrieval, RAG, and knowledge-graph pipelines.

Everything writes the same item shape — `{"url", "title", "content"}` —
into `raw-<name>/` directories, so every downstream consumer (chunkers,
embedders, indexers) treats all sources identically.

## The contract

- **1 request/second per domain** — parallel across domains, sequential
  within one. That's the politeness ceiling, by design.
- **Official surfaces only** — sitemaps, public APIs, published dumps.
  No auth walls, no JS-rendering, no robots.txt fights.
- **Resumable** — every scraper skips work already on disk.
- **Failures move on** — dead targets are logged and skipped, never fatal.

## Tools

| Tool | What it does |
|---|---|
| `scrape-crawl.py <name> <allow_regex> <max> <seeds...>` | polite seed crawler for sites without sitemaps; robust text extraction that survives unclosed `<nav>` tags |
| `scrape-langs.py <target>` | sitemap-driven docs scraper (97 targets in `targets_example.py`; copy to `targets.py`) |
| `scrape-parallel.py` | domain-grouped parallel driver — one lane per domain across all targets |
| `crawl-wave.py` | batch crawler config for no-sitemap sites |
| `scrape-arxiv-cat.py <cat...>` | arXiv export API by category |
| `scrape-hn.py` | Hacker News via the Algolia API |
| `scrape-hf-models.py` | top-N Hugging Face model cards via the official API |
| `clone-one.sh <owner/repo> <dir>` | single shallow clone (use with `xargs -P 3 -n 2`) |
| `clone-fpb-books.py` | parse the free-programming-books catalog, clone every GitHub-hosted book |

## Known gotchas (paid for in debugging)

- In `scrape-langs.py`, the `__main__` block must stay **after** every
  `TARGETS` definition — targets appended after it are silently
  invisible. This bug dropped entire scrape waves twice.
- Text extraction cannot rely on tag-close counting: real sites
  (go.dev: 5 `<nav>` opens, 2 closes) break skip counters. Use
  main-content detection with a script/style-only skip stack.
- The Hugging Face list API paginates with `skip`, not `page`.
- Sitemaps that return HTTP 200 can still be soft-404 redirects —
  validate the body, not the status code.

MIT licensed. Zero third-party dependencies — Python 3 stdlib only.
