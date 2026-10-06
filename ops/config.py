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

# Phase 1+: Agent API tokens. Empty = refuse to start (fail-fast, see server.main).
# Tokens are injected via stack env; never baked into the image.
OPS_READ_TOKEN = os.environ.get("OPS_READ_TOKEN", "")
OPS_WRITE_TOKEN = os.environ.get("OPS_WRITE_TOKEN", "")

# Phase 3b: Telegram push on new approval requests.
# Empty = no push. Never fail-fast: the panel must work without Telegram.
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")

# SQLite persistence (bind-mounted from host, covered by cluster-backup).
DB_PATH = os.environ.get("OPS_DB_PATH", "/data/ops.db")
