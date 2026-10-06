"""Central configuration (environment-driven)."""
import os
import secrets

PORT = int(os.environ.get("PORT", "8080"))

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = secrets.token_urlsafe(16)
    print(f"[SECURITY] No ADMIN_PASSWORD provided. Generated temporary password: {ADMIN_PASSWORD}")

SESSION_SECRET = os.environ.get("SESSION_SECRET") or secrets.token_hex(32)

PORTAINER_TOKEN_FILE = "/opt/portainer/api_token.key"
SSH_DIR = "/root/.ssh"

# Phase 2 (Agent API): empty = token auth disabled until enforcement lands.
OPS_READ_TOKEN = os.environ.get("OPS_READ_TOKEN", "")
OPS_WRITE_TOKEN = os.environ.get("OPS_WRITE_TOKEN", "")
