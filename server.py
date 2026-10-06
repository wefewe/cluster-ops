#!/usr/bin/env python3
"""Cluster Ops Console - thin entrypoint (see ops/ package)."""
import sys
import threading
from http.server import ThreadingHTTPServer

from ops.app import OpsHTTPRequestHandler
from ops.config import OPS_READ_TOKEN, OPS_WRITE_TOKEN, PORT
from ops.db import init_db
from ops.telemetry import background_telemetry_loop


def main():
    # Fail-fast: audit/approval APIs must never run without token auth.
    if not OPS_READ_TOKEN or not OPS_WRITE_TOKEN:
        print("[FATAL] OPS_READ_TOKEN / OPS_WRITE_TOKEN not set; refusing to start.",
              file=sys.stderr)
        print("[FATAL] Inject them via the stack environment.", file=sys.stderr)
        sys.exit(1)
    init_db()
    t = threading.Thread(target=background_telemetry_loop, daemon=True)
    t.start()
    print(f"[*] Starting Cluster Ops Server on port {PORT}...")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), OpsHTTPRequestHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
