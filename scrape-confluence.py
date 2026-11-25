#!/usr/bin/env python3
"""Scrape Confluence Cloud pages via the REST API.

Usage:
  python3 scrape-confluence.py spaces                # list accessible spaces
  python3 scrape-confluence.py scrape KEY [KEY...]   # full page pull per space

Pages land in <out>/<SPACEKEY>/<pageId>.json with
{url, title, content(storage HTML), version, ancestors}.
Politeness: 0.5s between calls. Resumable (existing pageIds skipped).
Retries each page with 5/15/30s backoff on connection resets / throttling.

Auth (env): CONFLUENCE_HOST (e.g. https://your-company.atlassian.net/wiki),
CONFLUENCE_EMAIL, CONFLUENCE_TOKEN (API token).
Out dir (env): HARVEST_CONFLUENCE_DIR (default ~/corpus/confluence).

Pagination note: the Cloud API returns no totalSize — page via
_links.next presence.
"""
import base64, html, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

BASE = (os.environ.get("CONFLUENCE_HOST")
        or "https://example.atlassian.net/wiki").rstrip("/") + "/rest/api"
OUT = Path(os.environ.get("HARVEST_CONFLUENCE_DIR") or Path.home() / "corpus/confluence")
RATE = 0.5


def creds():
    email, token = os.environ.get("CONFLUENCE_EMAIL"), os.environ.get("CONFLUENCE_TOKEN")
    if not email or not token:
        sys.exit("set CONFLUENCE_HOST, CONFLUENCE_EMAIL, CONFLUENCE_TOKEN (API token)")
    if not os.environ.get("CONFLUENCE_HOST"):
        # never send real credentials to the placeholder fallback host
        sys.exit("set CONFLUENCE_HOST (e.g. https://your-company.atlassian.net/wiki)")
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    return {"Authorization": f"Basic {auth}", "Accept": "application/json"}


HDR = creds()


def api(path, params=None):
    url = f"{BASE}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HDR)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def list_spaces():
    start, spaces = 0, []
    while True:
        d = api("space", {"limit": 100, "start": start})
        spaces.extend(d["results"])
        if not d["results"] or "_links" in d and d["_links"].get("next") is None and len(d["results"]) < 100:
            break
        start += 100
        time.sleep(RATE)
    print(f"{len(spaces)} accessible spaces")
    for s in spaces:
        print(f"  {s['key']:12s} {s.get('name', '')[:60]}")


def strip_html(storage_html):
    """Crude storage-format -> text for a content preview; keep the full
    storage XML in the item body since ingestion chunkers handle it."""
    text = re.sub(r"<br\s*/?>", "\n", storage_html or "")
    text = re.sub(r"</p>|</h[1-6]>|</li>|</tr>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(re.sub(r"\n{3,}", "\n\n", text).strip())


def fetch_page(pid):
    """Fetch one page with 5/15/30s backoff retries (transient errors only)."""
    expand = {"expand": "body.storage,ancestors,version"}
    try:
        return api(f"content/{pid}", expand)
    except urllib.error.HTTPError as e:
        if e.code not in (429, 500, 502, 503, 504):
            raise  # permanent (401/403/404...) — don't burn 50s of backoff
        last_e = e
        for wait in (5, 15, 30):
            time.sleep(wait)
            try:
                return api(f"content/{pid}", expand)
            except urllib.error.HTTPError as e2:
                last_e = e2
                if e2.code not in (429, 500, 502, 503, 504):
                    raise
                continue
            except Exception as e2:
                last_e = e2
                continue
        raise last_e
    except Exception as first_e:
        last_e = first_e
        for wait in (5, 15, 30):
            time.sleep(wait)
            try:
                return api(f"content/{pid}", expand)
            except Exception as e2:
                last_e = e2
                continue
        raise last_e


def scrape_space(key, since=None):
    """since='YYYY-MM-DD' → incremental mode: only pages modified since
    that date, overwriting what's on disk. None → full pull, skip existing."""
    out = OUT / key
    out.mkdir(parents=True, exist_ok=True)
    saved = len(list(out.glob("*.json")))
    overwrite = since is not None
    cql = f'space="{key}" and type=page'
    if since:
        cql += f' and lastModified >= "{since}"'
    print(f"[{key}] {saved} present; enumerating pages via CQL"
          f"{' (since ' + since + ')' if since else ''}...", flush=True)
    # Pagination: follow _links.next VERBATIM (it carries a cursor).
    # The `start` param is IGNORED by content/search beyond shallow
    # depths (start=500 re-serves page 1), which causes an infinite loop.
    params = {"cql": cql, "limit": 50}
    while True:
        d = api("content/search", params=params)
        results = d.get("results", [])
        for r in results:
            pid = r["id"]
            f = out / f"{pid}.json"
            if f.exists() and not overwrite:
                continue
            try:
                page = fetch_page(pid)
            except Exception as e:
                print(f"[{key}] page {pid} fail after retries: {e}", flush=True)
                time.sleep(RATE)
                continue
            storage = page.get("body", {}).get("storage", {}).get("value", "")
            tmp = out / f"{pid}.json.tmp"
            tmp.write_text(json.dumps({
                "url": f"{BASE.split('/rest')[0]}/pages/{pid}",
                "title": page.get("title", ""),
                "content": storage[:400_000],
                "text_preview": strip_html(storage)[:4000],
                "version": page.get("version", {}).get("number"),
                "space": key,
                "ancestors": [a.get("title") for a in page.get("ancestors", [])],
            }))
            tmp.replace(f)  # atomic: a crash never leaves a truncated skip-forever file
            saved += 1
            if saved % 50 == 0:
                print(f"[{key}] {saved} saved", flush=True)
            time.sleep(RATE)
        nxt = d.get("_links", {}).get("next")
        # follow the cursor until it is absent — a short page can still
        # carry a next cursor (permission filtering), and stopping early
        # silently loses the rest of the space
        if not nxt:
            break
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(nxt).query))
    print(f"[{key}] DONE: {saved} pages", flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "spaces":
        list_spaces()
    elif cmd == "scrape":
        for key in sys.argv[2:]:
            scrape_space(key)
    elif cmd == "update":
        # incremental: pages modified in the last 2 days, overwrite
        import datetime
        since = (datetime.date.today() - datetime.timedelta(days=2)).isoformat()
        for key in sys.argv[2:]:
            scrape_space(key, since=since)
    else:
        print(__doc__)
