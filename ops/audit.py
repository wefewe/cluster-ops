"""AI operations audit timeline (Phase 1).

Three AI operators (openclaw / opencode / muse-spark) plus the human owner
report every L1/L2 write action here within 5 minutes of execution
(RUNBOOK 7.2 rule 9). The table is append-only.
"""
import time

from . import db

ACTORS = ("openclaw", "opencode", "muse-spark", "owner")
LEVELS = ("L1", "L2")
RESULTS = ("ok", "failed", "rejected")

# Action verbs we recognize; unknown verbs are rejected so the timeline
# stays greppable instead of filling with free text.
ACTIONS = (
    "restart_service",
    "scale_service",
    "rollback_service",
    "update_image",
    "backup_trigger",
    "guard_trigger",
    "drill_trigger",
    "prune_images",
    "config_change",
    "secret_change",
    "dns_change",
    "node_change",
    "firewall_change",
    "data_restore",
    "data_delete",
    "approval_decision",
    "other",
)


def validate_audit_payload(payload):
    """Returns (ok, error_message)."""
    if not isinstance(payload, dict):
        return False, "body must be a JSON object"
    for field in ("actor", "level", "action"):
        if not payload.get(field):
            return False, f"missing required field: {field}"
    if payload["actor"] not in ACTORS:
        return False, f"unknown actor: {payload['actor']}"
    if payload["level"] not in LEVELS:
        return False, f"unknown level: {payload['level']}"
    if payload["action"] not in ACTIONS:
        return False, f"unknown action: {payload['action']}"
    if payload.get("result") and payload["result"] not in RESULTS:
        return False, f"unknown result: {payload['result']}"
    return True, ""


def record_audit(payload):
    """Validate + persist. Returns (row_id, error_message)."""
    ok, err = validate_audit_payload(payload)
    if not ok:
        return None, err
    entry = {
        "ts": int(payload.get("ts") or time.time()),
        "actor": payload["actor"],
        "level": payload["level"],
        "action": payload["action"],
        "target": str(payload.get("target", ""))[:256],
        "result": payload.get("result", "ok"),
        "detail": str(payload.get("detail", ""))[:2000],
        "rollback_hint": str(payload.get("rollback_hint", ""))[:500],
    }
    return db.insert_audit(entry), ""


def query_audit(limit=50, actor=None, level=None):
    if actor and actor not in ACTORS:
        actor = None
    if level and level not in LEVELS:
        level = None
    return db.list_audit(limit=limit, actor=actor, level=level)
