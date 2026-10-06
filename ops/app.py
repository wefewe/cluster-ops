"""HTTP request handler (routes)."""
import hmac
import http.server
import json
import os
import time
import urllib.parse

from .auth import sign_session, verify_session
from .cluster_data import get_cluster_data
from .config import ADMIN_PASSWORD
from .ui import HTML_TEMPLATE

class OpsHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/data":
            cookie_header = self.headers.get("Cookie", "")
            if not verify_session(cookie_header):
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

        self.send_response(404)
        self.end_headers()

