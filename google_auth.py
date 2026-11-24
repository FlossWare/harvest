#!/usr/bin/env python3
"""Shared Google OAuth helper for harvest scrapers. Account-aware.

Accounts are defined in a JSON config file that is NEVER committed:
  - $HARVEST_ACCOUNTS if set, else ~/.config/harvest/accounts.json
  - shape documented in accounts.example.json

Each account maps an OAuth credentials file to a corpus output
"vertical" directory. The account IS the vertical: whichever identity
owns the data decides where it lands, so separate accounts never mix.

Two credentials-file shapes are handled (per-account "format" key):
  tokens-nested: {tokens: {access_token, refresh_token, expiry_date}}
                 plus a separate OAuth keys file with client_id/secret
  flat:          {access_token, refresh_token, client_id, client_secret, ...}
"""
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

DEFAULT_CONFIG = Path.home() / ".config/harvest/accounts.json"


def _load():
    p = Path(os.environ.get("HARVEST_ACCOUNTS") or DEFAULT_CONFIG)
    if not p.exists():
        sys.exit(f"accounts config not found: {p} (see accounts.example.json)")
    accounts = {}
    for name, acct in json.loads(p.read_text()).items():
        acct = dict(acct)
        acct["creds"] = Path(acct["creds"]).expanduser()
        if acct.get("keys"):
            acct["keys"] = Path(acct["keys"]).expanduser()
        acct["vertical"] = Path(acct["vertical"]).expanduser()
        accounts[name] = acct
    return accounts


def resolve(account):
    accounts = _load()
    if account not in accounts:
        sys.exit(f"unknown account {account!r}; defined: {sorted(accounts)}")
    return accounts[account]


def token(account):
    """Return a valid access token, refreshing and persisting if needed."""
    acct = resolve(account)
    creds = json.loads(acct["creds"].read_text())
    fmt = acct.get("format", "flat")

    if fmt == "tokens-nested":
        tok = creds["tokens"]
        access, refresh = tok.get("access_token"), tok["refresh_token"]
        expiry = tok.get("expiry_date", 0)
        if access and expiry > time.time() * 1000 + 60000:
            return access
        keys = json.loads(acct["keys"].read_text())
        inst = keys.get("installed", keys.get("web", {}))
        client_id, client_secret = inst["client_id"], inst["client_secret"]
    else:
        access, refresh = creds.get("access_token"), creds["refresh_token"]
        expiry = creds.get("expiry_date", 0)
        if access and expiry > time.time() * 1000 + 60000:
            return access
        client_id, client_secret = creds["client_id"], creds["client_secret"]

    body = json.dumps({
        "client_id": client_id, "client_secret": client_secret,
        "refresh_token": refresh, "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        new = json.loads(r.read())
    if "access_token" not in new:
        sys.exit(f"token refresh failed for {account}: {new}")

    if fmt == "tokens-nested":
        tok["access_token"] = new["access_token"]
        tok["expiry_date"] = int(time.time() * 1000 + new.get("expires_in", 3600) * 1000)
        creds["tokens"] = tok
    else:
        creds["access_token"] = new["access_token"]
        creds["expiry_date"] = int(time.time() * 1000 + new.get("expires_in", 3600) * 1000)
    acct["creds"].write_text(json.dumps(creds, indent=2))
    return new["access_token"]


def api(url, account, binary=False, timeout=120):
    """Authenticated GET; returns parsed JSON or raw bytes."""
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token(account)}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if binary:
            return r.read()
        return json.loads(r.read() or b"{}")
