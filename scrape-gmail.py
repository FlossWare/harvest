#!/usr/bin/env python3
"""Scrape Gmail messages into the corpus via the Gmail API (account-aware).

Account = vertical (see google_auth.py + accounts.example.json): each
configured account scrapes into its own vertical directory,
e.g. <vertical>/gmail/messages/<id>.json

Each message: {url, title(subject), content(from+subject+body), date, labels}.

Usage:
  python3 scrape-gmail.py [account] [max_messages]
  # account: work (default) | personal; max_messages default 10000
"""
import base64, json, sys, time, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from google_auth import resolve, token as oauth_token

ACCOUNT = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("work", "personal") else "work"
MAX = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 10000
RATE = 0.3  # Gmail API is generous but stay polite
OUT = resolve(ACCOUNT)["vertical"] / "gmail/messages"
API = "https://gmail.googleapis.com/gmail/v1/users/me"


def gmail(method, path):
    req = urllib.request.Request(f"{API}/{path}", method=method, headers={
        "Authorization": f"Bearer {oauth_token(ACCOUNT)}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"{}")


def decode_body(payload):
    """Extract text from a Gmail message payload."""
    if not payload:
        return ""
    parts = [payload] + payload.get("parts", [])
    texts = []
    for p in parts:
        if p.get("mimeType", "").startswith("text/") and p.get("body", {}).get("data"):
            data = base64.urlsafe_b64decode(p["body"]["data"])
            texts.append(data.decode("utf-8", "replace"))
    return "\n\n".join(texts)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"account={ACCOUNT} ({resolve(ACCOUNT)['email']}) -> {OUT}", flush=True)
    saved = len(list(OUT.glob("*.json")))
    print(f"{saved} present; listing messages...", flush=True)
    msgs, page_token = [], None
    while len(msgs) < MAX:
        params = f"messages?maxResults=500"
        if page_token:
            params += f"&pageToken={page_token}"
        d = gmail("GET", params)
        batch = d.get("messages", [])
        msgs.extend(batch)
        page_token = d.get("nextPageToken")
        if not page_token or not batch:
            break
        time.sleep(RATE)
    print(f"{len(msgs)} messages listed; fetching bodies...", flush=True)
    for i, m in enumerate(msgs[:MAX]):
        mid = m["id"]
        f = OUT / f"{mid}.json"
        if f.exists():
            continue
        try:
            msg = gmail("GET", f"messages/{mid}?format=full")
        except Exception as e:
            print(f"  {mid} fail: {e}", flush=True)
            time.sleep(RATE)
            continue
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        body = decode_body(msg.get("payload", {}))
        f.write_text(json.dumps({
            "url": f"https://mail.google.com/#inbox/{mid}",
            "title": headers.get("Subject", "(no subject)"),
            "content": (f"From: {headers.get('From', '')}\n"
                        f"Subject: {headers.get('Subject', '')}\n\n"
                        f"{body}")[:400_000],
            "from": headers.get("From", ""),
            "date": headers.get("Date", ""),
            "labels": msg.get("labelIds", []),
            "snippet": msg.get("snippet", ""),
        }))
        saved += 1
        if saved % 100 == 0:
            print(f"  {saved} saved ({i+1}/{len(msgs)})", flush=True)
        time.sleep(RATE)
    print(f"GMAIL DONE: {saved} messages", flush=True)


if __name__ == "__main__":
    main()
