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
| `scrape-docs.py` | append-style `TARGETS +=` waves of language-docs targets for `scrape-langs.py` |
| `scrape-parallel.py` | domain-grouped parallel driver — one lane per domain across all targets |
| `crawl-wave.py` | batch crawler config for no-sitemap sites |
| `scrape-arxiv-cat.py <cat...>` | arXiv export API by category |
| `scrape-hn.py` | Hacker News via the Algolia API |
| `scrape-hf-models.py` | top-N Hugging Face model cards via the official API |
| `clone-one.sh <owner/repo> <dir>` | single shallow GitHub clone (use with `xargs -P 3 -n 2`) |
| `gitlab-clone-one.sh <group/project> <dir>` | single shallow GitLab SSH clone (`GITLAB_HOST`, `REPOS_DIR` env) |
| `clone-fpb-books.py` | parse the free-programming-books catalog, clone every GitHub-hosted book |
| `gap-rescrape.py <gap.jsonl> <corpus_root>` | polite gap re-scraper — per-domain sequential, 3 domains parallel, honors `Retry-After` |
| `wake.py <mac> [broadcast]` | Wake-on-LAN magic packet |

## Account-aware scrapers (private corpus)

These target your own authenticated accounts and write into per-account
"vertical" directories — the account that owns the data decides where it
lands, so separate accounts never mix. Accounts live in
`~/.config/harvest/accounts.json` (shape in `accounts.example.json`,
never commit the real one); credentials never sit inside corpus dirs.

| Tool | What it does |
|---|---|
| `google_auth.py` | shared account-aware OAuth (refresh + persist); config-driven, no hardcoded identities |
| `scrape-gmail.py [account] [max]` | Gmail messages → `<vertical>/gmail/messages/` |
| `scrape-gdrive.py [account] [max]` | Drive files + Docs/Sheets/Slides content → `<vertical>/gdrive/` |
| `scrape-gcalendar.py [account]` | all calendars, recurring events expanded → `<vertical>/calendar/` |
| `scrape-gcontacts.py [account]` | Contacts → `<vertical>/contacts.jsonl` |
| `scrape-gtasks.py [account]` | Tasks → `<vertical>/tasks.jsonl` |
| `google-oauth-listener.py` | one-shot localhost OAuth redirect listener that captures and stores tokens (mode 600) |
| `scrape-miro-save.py <out-dir>` | save Miro board inventory (JSON lines on stdin) as corpus items |
| `scrape-jira.py project KEY \\| personal \\| jql '<q>' <label>` | Jira Cloud via REST v3 — GET + cursor pagination; env `JIRA_HOST/EMAIL/TOKEN` |
| `scrape-confluence.py spaces \\| scrape KEY...` | Confluence Cloud pages; per-page retry backoff; env `CONFLUENCE_HOST/EMAIL/TOKEN` |

Org-specific details (which spaces, which projects, which JQL) are
configuration, not code — pass them as arguments; nothing
workplace-identifying is baked in.

## Not here

Store-side tooling — corpus integrity manifests, the URL master index,
PDF change detection — lives in
[FlossWare/silo](https://github.com/FlossWare/silo). This repo is the
harvest side only: everything that pulls data, nothing that verifies
the store.

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
