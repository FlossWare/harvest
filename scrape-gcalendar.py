#!/usr/bin/env python3
"""Scrape Google Calendar events into the corpus (account-aware).

Account = vertical (see google_auth.py + accounts.example.json):
  <vertical>/calendar/<calId>/<eventId>.json

Full history (no timeMin), recurring events expanded (singleEvents=true).

Usage: python3 scrape-gcalendar.py [account]   # work (default) | personal
"""
import json, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from google_auth import resolve, api

ACCOUNT = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("work", "personal") else "work"
OUT = resolve(ACCOUNT)["vertical"] / "calendar"
RATE = 0.3


def safe(name):
    # no @ in dir names (rsync/scp/shell quirks); keep it readable
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)[:80]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"account={ACCOUNT} ({resolve(ACCOUNT)['email']}) -> {OUT}", flush=True)

    cals, token = [], None
    while True:
        url = ("https://www.googleapis.com/calendar/v3/users/me/calendarList"
               "?maxResults=250&fields=nextPageToken,items(id,summary,timeZone)")
        if token:
            url += f"&pageToken={token}"
        d = api(url, ACCOUNT)
        cals.extend(d.get("items", []))
        token = d.get("nextPageToken")
        if not token:
            break
        time.sleep(RATE)
    print(f"{len(cals)} calendars", flush=True)

    total = 0
    for cal in cals:
        cid = cal["id"]
        summary = cal.get("summary", cid)
        caldir = OUT / safe(cid)
        caldir.mkdir(parents=True, exist_ok=True)
        events, token = 0, None
        while True:
            url = (f"https://www.googleapis.com/calendar/v3/calendars/{cid}/events"
                   "?singleEvents=true&maxResults=250"
                   "&fields=nextPageToken,items(id,summary,description,status,"
                   "htmlLink,location,organizer(email,displayName),"
                   "attendees(email,displayName,responseStatus),"
                   "start,end,recurrence,created,updated)")
            if token:
                url += f"&pageToken={token}"
            try:
                d = api(url, ACCOUNT)
            except Exception as e:
                print(f"  {summary}: {e}", flush=True)
                break
            for ev in d.get("items", []):
                attendees = ", ".join(
                    a.get("email", a.get("displayName", "?"))
                    for a in ev.get("attendees", []))
                (caldir / f"{ev['id']}.json").write_text(json.dumps({
                    "url": ev.get("htmlLink", ""),
                    "title": ev.get("summary", "(no title)"),
                    "content": (f"Calendar: {summary}\n"
                                f"When: {ev.get('start', {})} - {ev.get('end', {})}\n"
                                f"Organizer: {ev.get('organizer', {}).get('email', '')}\n"
                                f"Attendees: {attendees}\n"
                                f"Location: {ev.get('location', '')}\n\n"
                                f"{ev.get('description', '')}")[:400_000],
                    "calendar": summary,
                    "calendarId": cid,
                    "start": ev.get("start"),
                    "end": ev.get("end"),
                    "status": ev.get("status"),
                    "created": ev.get("created"),
                    "updated": ev.get("updated"),
                }))
                events += 1
            token = d.get("nextPageToken")
            if not token:
                break
            time.sleep(RATE)
        total += events
        print(f"  {summary}: {events} events", flush=True)
    print(f"CALENDAR DONE: {total} events across {len(cals)} calendars", flush=True)


if __name__ == "__main__":
    main()
