#!/usr/bin/env python3
"""Save Miro board inventory from content_search results as corpus items.

Reads board data from stdin (JSON lines from the MCP tool output) and
writes corpus-format JSON to the output dir given as argv[1].
"""
import json, re, sys
from pathlib import Path

if len(sys.argv) < 2:
    sys.exit("usage: scrape-miro-save.py <out-dir>")
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        board = json.loads(line)
    except Exception:
        continue
    bid = board.get("miro_url", "").rstrip("/").split("/")[-1].replace("=", "")
    if not bid:
        continue
    f = OUT / f"{bid}.json"
    if f.exists():
        continue
    highlights = board.get("highlights", [])
    content = f"Board: {board.get('name', '')}\n\n"
    if board.get("description"):
        content += f"Description: {board['description']}\n\n"
    content += "Content snippets:\n" + "\n".join(f"- {h}" for h in highlights)
    f.write_text(json.dumps({
        "url": board.get("miro_url", ""),
        "title": board.get("name", ""),
        "content": content[:400_000],
        "type": board.get("miro_type", "board"),
        "last_modified": board.get("last_modified", ""),
        "highlights": highlights,
    }))
    print(f"saved: {board.get('name', '?')[:50]}")

print("DONE")
