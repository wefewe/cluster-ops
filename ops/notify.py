"""Best-effort Telegram notifications.

Used for: new L2 approval requests (the owner needs to know promptly,
otherwise a request can sit 24h unseen). Fire-and-forget: never blocks
an API response, never raises, never fail-fasts the container when the
token is not configured.
"""
import json
import threading
import urllib.request

from . import config

PANEL_URL = "https://ops.cwsub.indevs.in/"


def _post(text):
    try:
        body = json.dumps({"chat_id": config.TG_CHAT_ID, "text": text}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{config.TG_BOT_TOKEN}/sendMessage",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10).read()
    except Exception:
        pass


def notify_async(text):
    """Send a Telegram message in a daemon thread. Safe from handlers."""
    if not config.TG_BOT_TOKEN or not config.TG_CHAT_ID:
        return
    threading.Thread(target=_post, args=(text,), daemon=True).start()


def approval_created_msg(appr):
    return (
        f"\U0001f7e1 [审批] #{appr['id']} 待处理\n"
        f"发起: {appr['requester']}\n"
        f"动作: {appr['action']} → {appr['target']}\n"
        f"理由: {appr['reason']}\n"
        f"\U0001f446 {PANEL_URL}\n"
        f"24h 未处理自动驳回"
    )
