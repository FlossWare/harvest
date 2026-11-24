#!/usr/bin/env python3
"""Scrape Google Contacts into the corpus (account-aware).

Account = vertical (see google_auth.py + accounts.example.json):
  <vertical>/contacts.jsonl

Full rewrite each run (small dataset).

Usage: python3 scrape-gcontacts.py [account]   # work (default) | personal
"""
import json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from google_auth import resolve, api

ACCOUNT = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("work", "personal") else "work"
OUT = resolve(ACCOUNT)["vertical"] / "contacts.jsonl"
RATE = 0.3
FIELDS = "names,emailAddresses,phoneNumbers,organizations,biographies,addresses,birthdays,urls"


def main():
    print(f"account={ACCOUNT} ({resolve(ACCOUNT)['email']}) -> {OUT}", flush=True)
    people, token = [], None
    while True:
        url = (f"https://people.googleapis.com/v1/people/me/connections"
               f"?personFields={FIELDS}&pageSize=1000"
               "&fields=nextPageToken,connections(resourceName,names,emailAddresses,"
               "phoneNumbers,organizations,biographies,addresses,birthdays,urls)")
        if token:
            url += f"&pageToken={token}"
        try:
            d = api(url, ACCOUNT)
        except Exception as e:
            print(f"  fail: {e}", flush=True)
            break
        people.extend(d.get("connections", []))
        token = d.get("nextPageToken")
        if not token:
            break
        time.sleep(RATE)

    with OUT.open("w") as f:
        for p in people:
            name = (p.get("names", [{}])[0].get("displayName", ""))
            emails = ", ".join(e.get("value", "") for e in p.get("emailAddresses", []))
            phones = ", ".join(ph.get("value", "") for ph in p.get("phoneNumbers", []))
            orgs = ", ".join(
                f"{o.get('title','')} @ {o.get('name','')}".strip()
                for o in p.get("organizations", []))
            f.write(json.dumps({
                "url": f"https://contacts.google.com/{p.get('resourceName','')}",
                "title": name or "(no name)",
                "content": f"Name: {name}\nEmails: {emails}\nPhones: {phones}\n"
                           f"Organizations: {orgs}\nBio: {p.get('biographies',[{}])[0].get('value','') if p.get('biographies') else ''}",
                "resourceName": p.get("resourceName", ""),
                "raw": p,
            }) + "\n")
    print(f"CONTACTS DONE: {len(people)} people", flush=True)


if __name__ == "__main__":
    main()
