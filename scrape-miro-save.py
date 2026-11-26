#!/usr/bin/env python3
"""Save Miro board inventory from content_search results as corpus items.

Reads board data from stdin (JSON lines from the MCP tool output) and
writes corpus-format JSON to private/redhat/miro/.
"""
import json, re, sys
from pathlib import Path

OUT = Path.home() / ".FlossWare/corpus/private/redhat/miro"
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
    if bid and not re.fullmatch(r"[A-Za-z0-9_.=-]+", bid):
        # allowlist: a crafted board id must never shape the filename
        bid = ""
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
    record = {
        "url": board.get("miro_url", ""),
        "title": board.get("name", ""),
        "content": content[:400_000],
        "type": board.get("miro_type", "board"),
        "last_modified": board.get("last_modified", ""),
        "highlights": highlights,
    }
    # atomic: a crash mid-write must not leave a truncated file that the
    # exists-skip then treats as done forever
    item = json.dumps(record)
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(item)
    tmp.replace(f)
    print(f"saved: {board.get('name', '?')[:50]}")

print("DONE")
