#!/usr/bin/env python3
"""Cluster Ops Console - thin entrypoint (see ops/ package)."""
import threading
from http.server import ThreadingHTTPServer

from ops.app import OpsHTTPRequestHandler
from ops.config import PORT
from ops.telemetry import background_telemetry_loop


def main():
    t = threading.Thread(target=background_telemetry_loop, daemon=True)
    t.start()
    print(f"[*] Starting Cluster Ops Server on port {PORT}...")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), OpsHTTPRequestHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
