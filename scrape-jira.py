#!/usr/bin/env python3
"""Scrape Jira Cloud issues into the corpus via the REST v3 API.

Usage:
  python3 scrape-jira.py project KEY   # all issues in a project
  python3 scrape-jira.py personal      # assigned/reported/watched by you
  python3 scrape-jira.py jql '<query>' <label>   # arbitrary JQL

Issues land in <out>/<PROJECT>/<KEY>.json with
{url, title, content(summary+description+comments), status, labels, ...}.

Auth (env): JIRA_HOST (e.g. https://your-company.atlassian.net),
JIRA_EMAIL, JIRA_TOKEN (API token).
Out dir (env): HARVEST_JIRA_DIR (default ~/corpus/jira).

Notes: the v3 search endpoint is GET with cursor pagination
(nextPageToken/isLast); maxResults must be 1-5000.
"""
import base64, json, os, sys, time, urllib.parse, urllib.request
from pathlib import Path

BASE = (os.environ.get("JIRA_HOST") or "https://example.atlassian.net").rstrip("/") + "/rest/api/3"
OUT = Path(os.environ.get("HARVEST_JIRA_DIR") or Path.home() / "corpus/jira")
RATE = 0.4
BATCH = 50


def creds():
    email, token = os.environ.get("JIRA_EMAIL"), os.environ.get("JIRA_TOKEN")
    host = os.environ.get("JIRA_HOST")
    if not email or not token:
        sys.exit("set JIRA_HOST, JIRA_EMAIL, JIRA_TOKEN (API token)")
    if not host:
        # never send real credentials to the placeholder fallback host
        sys.exit("set JIRA_HOST (e.g. https://your-company.atlassian.net)")
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    return {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}


HDR = creds()


def api(method, path, body=None, params=None):
    url = f"{BASE}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=HDR, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"{}")


def extract_text(node):
    """Recursively extract text from Jira's Atlassian Document Format."""
    if isinstance(node, dict):
        if "text" in node:
            return node["text"]
        return " ".join(extract_text(v) for k, v in node.items() if k != "type")
    if isinstance(node, list):
        return "\n".join(filter(None, (extract_text(i) for i in node)))
    return ""


def scrape_query(jql, label, overwrite=False):
    """Run a JQL query and save all issues (GET with cursor pagination).

    overwrite=True re-fetches issues already on disk (incremental mode,
    where the JQL window already selects only recently-updated issues)."""
    fields = ["summary", "description", "status", "labels", "assignee",
              "reporter", "priority", "issuetype", "created", "updated",
              "resolution", "fixVersions", "components", "comment"]
    saved = 0
    page_token = None
    fails = 0
    print(f"[{label}] starting: {jql[:60]}...", flush=True)
    while True:
        params = {"jql": jql, "maxResults": BATCH, "fields": fields}
        if page_token:
            # NB: the request param is nextPageToken (same name as the
            # response field). `pageToken` is silently ignored -> infinite
            # loop re-fetching page 1 (verified 2026-11-24).
            params["nextPageToken"] = page_token
        try:
            d = api("GET", "search/jql", params=params)
            fails = 0
        except Exception as e:
            # bounded retries: a bad JQL (400), expired token (401) or
            # wrong host (404) must not loop forever
            fails += 1
            print(f"[{label}] search fail ({fails}/10): {e}", flush=True)
            if fails >= 10:
                print(f"[{label}] ABORT: too many search failures", flush=True)
                return
            time.sleep(10)
            continue
        issues = d.get("issues", [])
        for issue in issues:
            key = issue["key"]
            f_fields = issue.get("fields", {})
            project = key.split("-")[0]
            out_dir = OUT / project
            out_dir.mkdir(parents=True, exist_ok=True)
            f = out_dir / f"{key}.json"
            if f.exists() and not overwrite:
                continue
            desc = extract_text(f_fields.get("description")) if f_fields.get("description") else ""
            comments = []
            for c in (f_fields.get("comment", {}) or {}).get("comments", []):
                author = (c.get("author", {}) or {}).get("displayName", "?")
                body_text = extract_text(c.get("body")) if c.get("body") else ""
                comments.append(f"{author}: {body_text}")
            content = (
                f"Summary: {f_fields.get('summary', '')}\n\n"
                f"Description:\n{desc}\n\n"
                f"Status: {(f_fields.get('status', {}) or {}).get('name', '?')}\n"
                f"Type: {(f_fields.get('issuetype', {}) or {}).get('name', '?')}\n"
                f"Priority: {((f_fields.get('priority', {}) or {}).get('name', '?'))}\n"
                f"Resolution: {((f_fields.get('resolution', {}) or {}).get('name', 'Unresolved'))}\n"
                f"Labels: {', '.join(f_fields.get('labels', []))}\n"
                f"Fix Versions: {', '.join(v.get('name', '') for v in f_fields.get('fixVersions', []))}\n\n"
                f"Comments ({len(comments)}):\n" + "\n---\n".join(comments)
            )
            tmp = out_dir / f"{key}.json.tmp"
            tmp.write_text(json.dumps({
                "url": f"{BASE.split('/rest')[0]}/browse/{key}",
                "title": f"{key}: {f_fields.get('summary', '')}",
                "content": content[:400_000],
                "key": key,
                "status": (f_fields.get("status", {}) or {}).get("name", ""),
                "labels": f_fields.get("labels", []),
                "type": (f_fields.get("issuetype", {}) or {}).get("name", ""),
                "created": f_fields.get("created", ""),
                "updated": f_fields.get("updated", ""),
            }))
            tmp.replace(f)  # atomic: a crash never leaves a truncated skip-forever file
            saved += 1
        page_token = d.get("nextPageToken")
        # end on an absent token; a missing isLast must not stop early,
        # and isLast=false with no token must not restart from page 1
        is_last = d.get("isLast", page_token is None)
        if is_last or not page_token:
            break
        if saved % 50 == 0:
            print(f"[{label}] {saved} saved (isLast={is_last})", flush=True)
        time.sleep(RATE)
    print(f"[{label}] DONE: {saved} issues saved", flush=True)


def main():
    scope = sys.argv[1] if len(sys.argv) > 1 else ""
    if scope == "personal":
        scrape_query("assignee = currentUser()", "assigned")
        scrape_query("reporter = currentUser()", "reported")
        scrape_query("watcher = currentUser()", "watching")
    elif scope == "daily":
        # Incremental sync: only issues touched in the last 2 days,
        # overwriting what's on disk (edits + new issues).
        scrape_query(
            "(assignee = currentUser() OR reporter = currentUser()"
            " OR watcher = currentUser()) AND updated >= -2d",
            "personal-incr", overwrite=True)
    elif scope == "project":
        if len(sys.argv) < 3:
            print("usage: scrape-jira.py project KEY")
            sys.exit(1)
        scrape_query(f"project = {sys.argv[2]}", sys.argv[2])
    elif scope == "jql":
        if len(sys.argv) < 4:
            print("usage: scrape-jira.py jql '<query>' <label>")
            sys.exit(1)
        scrape_query(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
