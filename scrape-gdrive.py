#!/usr/bin/env python3
"""Scrape Google Drive files and Google Docs content into the corpus (account-aware).

Account = vertical (see google_auth.py + accounts.example.json): each
configured account scrapes into its own vertical directory,
e.g. <vertical>/gdrive/

  docs/<docId>.json     — Google Docs (text content via Docs API)
  sheets/<fileId>.json  — Google Sheets (content via CSV export)
  slides/<fileId>.json  — Google Slides (content via text export)
  files/<fileId>        — binary files (PDFs, images, etc. — downloaded)

Usage: python3 scrape-gdrive.py [account] [max_files]   # default 5000
"""
import json, mimetypes, os, re, sys, time, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from google_auth import resolve, api as google_api

ACCOUNT = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("work", "personal") else "work"
MAX = int(sys.argv[-1]) if sys.argv[-1].isdigit() else 5000
RATE = 0.3
OUT = resolve(ACCOUNT)["vertical"] / "gdrive"


def api(url, binary=False):
    return google_api(url, ACCOUNT, binary=binary)


def list_files():
    files, page_token = [], None
    while len(files) < MAX:
        url = ("https://www.googleapis.com/drive/v3/files?pageSize=200"
               "&fields=nextPageToken,files(id,name,mimeType,modifiedTime,size,parents,webViewLink)")
        if page_token:
            url += f"&pageToken={page_token}"
        d = api(url)
        files.extend(d.get("files", []))
        page_token = d.get("nextPageToken")
        if not page_token:
            break
        time.sleep(RATE)
    return files[:MAX]


def fetch_doc(doc_id):
    """Google Docs content via the Docs API."""
    d = api(f"https://docs.googleapis.com/v1/documents/{doc_id}")
    # extract text from all structural elements
    parts = []
    for element in d.get("body", {}).get("content", []):
        if "paragraph" in element:
            for run in element["paragraph"].get("elements", []):
                if "textRun" in run:
                    parts.append(run["textRun"].get("content", ""))
        elif "table" in element:
            for row in element["table"].get("tableRows", []):
                cells = []
                for cell in row.get("tableCells", []):
                    cell_text = " ".join(
                        r.get("textRun", {}).get("content", "")
                        for p in cell.get("content", [])
                        for r in p.get("paragraph", {}).get("elements", []))
                    cells.append(cell_text.strip())
                parts.append(" | ".join(cells))
    return d.get("title", ""), "\n".join(parts)


def export_file(file_id, mime_type):
    """Export a Drive file in a plain-text format."""
    export_map = {
        "application/vnd.google-apps.document": "text/plain",
        "application/vnd.google-apps.spreadsheet": "text/csv",
        "application/vnd.google-apps.presentation": "text/plain",
        "application/vnd.google-apps.drawing": "image/png",
    }
    export_mime = export_map.get(mime_type, "text/plain")
    url = (f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
           f"?mimeType={urllib.parse.quote(export_mime)}")
    return api(url, binary=True)


def main():
    for sub in ["docs", "sheets", "slides", "files"]:
        (OUT / sub).mkdir(parents=True, exist_ok=True)
    print(f"account={ACCOUNT} ({resolve(ACCOUNT)['email']}) -> {OUT}", flush=True)
    files = list_files()
    print(f"{len(files)} Drive files listed", flush=True)
    saved = 0
    for i, f in enumerate(files):
        fid, name, mime = f["id"], f.get("name", ""), f.get("mimeType", "")
        try:
            if mime == "application/vnd.google-apps.document":
                out = OUT / "docs" / f"{fid}.json"
                if out.exists():
                    continue
                title, text = fetch_doc(fid)
                out.write_text(json.dumps({
                    "url": f.get("webViewLink", ""),
                    "title": title or name,
                    "content": text[:400_000],
                    "mimeType": mime,
                    "modifiedTime": f.get("modifiedTime", ""),
                }))
            elif mime in ("application/vnd.google-apps.spreadsheet",
                          "application/vnd.google-apps.presentation"):
                subdir = "sheets" if "spreadsheet" in mime else "slides"
                out = OUT / subdir / f"{fid}.json"
                if out.exists():
                    continue
                content = export_file(fid, mime)
                if isinstance(content, bytes):
                    content = content.decode("utf-8", "replace")
                out.write_text(json.dumps({
                    "url": f.get("webViewLink", ""),
                    "title": name,
                    "content": content[:400_000],
                    "mimeType": mime,
                    "modifiedTime": f.get("modifiedTime", ""),
                }))
            else:
                # binary file (PDF, image, etc.) — download if small enough
                size = int(f.get("size", 0))
                if size > 50_000_000:  # skip >50MB
                    continue
                out = OUT / "files" / fid
                if out.exists():
                    continue
                content = api(f"https://www.googleapis.com/drive/v3/files/{fid}?alt=media",
                              binary=True)
                out.write_bytes(content)
            saved += 1
            if saved % 25 == 0:
                print(f"  {saved} saved ({i+1}/{len(files)})", flush=True)
        except Exception as e:
            print(f"  {name[:40]}: {e}", flush=True)
        time.sleep(RATE)
    print(f"GDRIVE DONE: {saved} files", flush=True)


if __name__ == "__main__":
    main()
