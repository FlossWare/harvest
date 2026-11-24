#!/usr/bin/env python3
"""Scrape Google Tasks into the corpus (account-aware).

Account = vertical (see google_auth.py + accounts.example.json):
  <vertical>/tasks.jsonl

Full rewrite each run (small dataset).

Usage: python3 scrape-gtasks.py [account]   # work (default) | personal
"""
import json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from google_auth import resolve, api

ACCOUNT = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("work", "personal") else "work"
OUT = resolve(ACCOUNT)["vertical"] / "tasks.jsonl"
RATE = 0.3


def main():
    print(f"account={ACCOUNT} ({resolve(ACCOUNT)['email']}) -> {OUT}", flush=True)
    lists, token = [], None
    while True:
        url = ("https://tasks.googleapis.com/tasks/v1/users/@me/lists"
               "?maxResults=100&fields=nextPageToken,items(id,title,updated)")
        if token:
            url += f"&pageToken={token}"
        d = api(url, ACCOUNT)
        lists.extend(d.get("items", []))
        token = d.get("nextPageToken")
        if not token:
            break
        time.sleep(RATE)

    total = 0
    with OUT.open("w") as f:
        for tl in lists:
            tasks, token = [], None
            while True:
                url = (f"https://tasks.googleapis.com/tasks/v1/lists/{tl['id']}/tasks"
                       "?showCompleted=true&showHidden=true&maxResults=100"
                       "&fields=nextPageToken,items(id,title,notes,status,due,updated,completed)")
                if token:
                    url += f"&pageToken={token}"
                try:
                    d = api(url, ACCOUNT)
                except Exception as e:
                    print(f"  {tl.get('title')}: {e}", flush=True)
                    break
                tasks.extend(d.get("items", []))
                token = d.get("nextPageToken")
                if not token:
                    break
                time.sleep(RATE)
            for t in tasks:
                f.write(json.dumps({
                    "url": f"https://tasks.google.com/",
                    "title": t.get("title", "(no title)"),
                    "content": (f"List: {tl.get('title','')}\nStatus: {t.get('status','')}\n"
                                f"Due: {t.get('due','')}\n\n{t.get('notes','')}"),
                    "taskList": tl.get("title", ""),
                    "status": t.get("status"),
                    "due": t.get("due"),
                    "updated": t.get("updated"),
                }) + "\n")
                total += 1
            print(f"  {tl.get('title')}: {len(tasks)} tasks", flush=True)
    print(f"TASKS DONE: {total} tasks across {len(lists)} lists", flush=True)


if __name__ == "__main__":
    main()
