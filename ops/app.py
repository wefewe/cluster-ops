"""HTTP request handler (routes)."""
import hmac
import http.server
import json
import os
import time
import urllib.parse

from .auth import sign_session, verify_session, verify_token
from .audit import query_audit, record_audit
from .cluster_data import get_cluster_data
from .config import ADMIN_PASSWORD, OPS_READ_TOKEN, OPS_WRITE_TOKEN
from .ui import HTML_TEMPLATE

_TOKEN_REDACT_LEN = 4


def _api_token(headers):
    """Extract the caller's API token without logging it."""
    return headers.get("X-Ops-Token", "")


def _read_allowed(headers):
    cookie_header = headers.get("Cookie", "")
    if verify_session(cookie_header):
        return True
    return verify_token(_api_token(headers), OPS_READ_TOKEN)


def _write_allowed(headers):
    cookie_header = headers.get("Cookie", "")
    if verify_session(cookie_header):
        return True
    return verify_token(_api_token(headers), OPS_WRITE_TOKEN)


def _json(handler, code, obj):
    body = json.dumps(obj).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)

class OpsHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/data":
            if not _read_allowed(self.headers):
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"Unauthorized"}')
                return

            data = get_cluster_data()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
            return

        if path == "/api/auth-check":
            cookie_header = self.headers.get("Cookie", "")
            valid = verify_session(cookie_header)
            self.send_response(200 if valid else 401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"authenticated": valid}).encode('utf-8'))
            return

        if path == "/api/audit":
            if not _read_allowed(self.headers):
                _json(self, 401, {"error": "Unauthorized"})
                return
            qs = urllib.parse.parse_qs(parsed.query)
            items = query_audit(
                limit=qs.get("limit", ["50"])[0],
                actor=qs.get("actor", [None])[0],
                level=qs.get("level", [None])[0],
            )
            _json(self, 200, {"items": items})
            return

        # Default: serve Frontend HTML with dynamic cockpit items injected
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        rendered_html = HTML_TEMPLATE
        cockpit_env = os.environ.get("COCKPIT_ITEMS_JSON", "")
        if cockpit_env:
            inject_script = f"<script>window.__OPS_COCKPIT_ITEMS__ = {cockpit_env};</script>"
            rendered_html = rendered_html.replace("</head>", f"{inject_script}</head>")
        self.wfile.write(rendered_html.encode('utf-8'))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/login":
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body.decode('utf-8'))
                pwd = payload.get("password", "")
                if hmac.compare_digest(pwd, ADMIN_PASSWORD):
                    ts = str(int(time.time()))
                    token = f"{ts}.{sign_session(ts)}"
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Set-Cookie", f"ops_token={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000")
                    self.end_headers()
                    self.wfile.write(b'{"status":"ok"}')
                    return
            except Exception:
                pass
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"Invalid password"}')
            return

        if path == "/api/logout":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie", "ops_token=; Path=/; HttpOnly; Max-Age=0")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return

        if path == "/api/audit":
            if not _write_allowed(self.headers):
                _json(self, 401, {"error": "Unauthorized"})
                return
            length = int(self.headers.get('Content-Length', 0))
            if length <= 0 or length > 65536:
                _json(self, 400, {"error": "bad body length"})
                return
            try:
                payload = json.loads(self.rfile.read(length).decode('utf-8'))
            except Exception:
                _json(self, 400, {"error": "invalid JSON"})
                return
            row_id, err = record_audit(payload)
            if err:
                _json(self, 400, {"error": err})
                return
            _json(self, 200, {"status": "ok", "id": row_id})
            return

        self.send_response(404)
        self.end_headers()

