#!/usr/bin/env python3
"""One-shot OAuth listener for the personal Google account.

Waits on http://localhost:8477 for Google's redirect, validates state,
exchanges the authorization code for tokens, and writes them to
~/.gmail-mcp/personal-credentials.json (mode 600).
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE = os.path.expanduser('~/.gmail-mcp')
STATE_FILE = os.path.join(BASE, 'oauth-flow-state.json')
OUT_FILE = os.path.join(BASE, 'personal-credentials.json')
PORT = 8477

with open(STATE_FILE) as f:
    flow = json.load(f)

# Client secret read from ~/flossware_bashrc, never passed on argv
secret = None
for line in open(os.path.expanduser('~/flossware_bashrc')):
    m = re.match(r'(?:export\s+)?PERSONAL_GOOGLE_CLIENT_SECRET=(.+)$', line.strip())
    if m:
        secret = m.group(1).strip().strip("'\"")
        break
if not secret:
    sys.exit('FATAL: PERSONAL_GOOGLE_CLIENT_SECRET not found in ~/flossware_bashrc')

result = {'status': 'waiting'}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if 'code' not in qs:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'No code in callback. Restart the flow.')
            result['status'] = 'error: no code'
            return
        if qs.get('state', [None])[0] != flow['state']:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'State mismatch. Restart the flow.')
            result['status'] = 'error: state mismatch'
            return
        result['code'] = qs['code'][0]
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<h1>Authorization captured.</h1>'
                         b'<p>You can close this tab.</p>')

    def log_message(self, fmt, *args):
        pass


server = HTTPServer(('127.0.0.1', PORT), Handler)
server.timeout = 600  # bail after 10 min of silence
server.handle_request()

if 'code' not in result:
    sys.exit(f"FATAL: no code captured ({result.get('status', 'timeout')})")

# Exchange; retry with port-less redirect_uri in case of mismatch on the
# port-qualified variant (desktop clients accept loopback with any port).
for redirect_uri in (f'http://localhost:{PORT}', 'http://localhost'):
    data = urllib.parse.urlencode({
        'code': result['code'],
        'client_id': flow['client_id'],
        'client_secret': secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    }).encode()
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data)
    try:
        resp = json.load(urllib.request.urlopen(req, timeout=15))
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f'exchange failed for redirect_uri={redirect_uri}: {e.code} {err}')
        continue
    if 'refresh_token' not in resp:
        print('exchange succeeded but NO refresh_token in response:')
        print(json.dumps({k: v for k, v in resp.items()}, indent=2)[:500])
        sys.exit(1)
    payload = {
        'client_id': flow['client_id'],
        'client_secret': secret,
        'refresh_token': resp['refresh_token'],
        'access_token': resp['access_token'],
        'expires_in': resp.get('expires_in'),
        'scopes': flow['scopes'],
        'redirect_uri_used': redirect_uri,
        'created': __import__('datetime').datetime.now().isoformat(),
    }
    import os as _os
    tmp = OUT_FILE + '.tmp'
    fd = _os.open(tmp, _os.O_WRONLY | _os.O_CREAT | _os.O_TRUNC, 0o600)
    with _os.fdopen(fd, 'w') as f:
        json.dump(payload, f, indent=2)
        f.flush()
        _os.fsync(f.fileno())
    _os.replace(tmp, OUT_FILE)
    print('SUCCESS: refresh token stored in', OUT_FILE)
    print('scopes granted:', resp.get('scope'))
    sys.exit(0)

sys.exit(1)
