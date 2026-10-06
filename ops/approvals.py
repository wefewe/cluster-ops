"""L2 approval queue (Phase 3).

An AI that needs a high-risk (L2) action posts an approval request.
The human owner approves/rejects from the panel (admin cookie).
The requesting AI then executes and reports back the outcome.

State machine (illegal transitions -> 409):
    pending -> approved   (owner decides, cookie only)
    pending -> rejected   (owner decides, or 24h auto-expire)
    approved -> executed  (requesting AI reports, write token)
    approved -> failed    (requesting AI reports, write token)

Every transition also appends an audit entry so the timeline tells
the full story.
"""
import json
import time

from . import audit, db, notify

STATUSES = ("pending", "approved", "rejected", "executed", "failed")
EXPIRY_SECONDS = 24 * 3600


def _now():
    return int(time.time())


def _row_to_dict(row):
    d = dict(row)
    try:
        d["params"] = json.loads(d.get("params") or "{}")
    except ValueError:
        d["params"] = {}
    return d


def _audit_transition(appr, event, actor, result="ok", detail=""):
    """Append a timeline entry for an approval state change. Best-effort."""
    try:
        audit.record_audit({
            "ts": _now(),
            "actor": actor,
            "level": "L2",
            "action": event,
            "target": appr.get("target", ""),
            "result": result,
            "detail": f"approval #{appr['id']}: {detail}".strip(),
        })
    except Exception:
        pass


def create_approval(payload):
    """Validate + insert a pending approval. Returns (row_dict, error)."""
    if not isinstance(payload, dict):
        return None, "body must be a JSON object"
    requester = payload.get("requester", "")
    action = payload.get("action", "")
    target = payload.get("target", "")
    reason = payload.get("reason", "")
    params = payload.get("params", {})
    if requester not in ("openclaw", "opencode", "muse-spark"):
        return None, f"unknown requester: {requester}"
    if action not in audit.ACTIONS:
        return None, f"unknown action: {action}"
    if not target:
        return None, "missing required field: target"
    if not reason:
        return None, "missing required field: reason"
    if not isinstance(params, dict):
        return None, "params must be a JSON object"
    ts = _now()
    row_id = db.insert_approval({
        "ts": ts,
        "updated": ts,
        "requester": requester,
        "action": action,
        "target": target,
        "params": json.dumps(params, ensure_ascii=False),
        "reason": reason,
        "level": "L2",
        "status": "pending",
        "expires_at": ts + EXPIRY_SECONDS,
    })
    appr = get_approval(row_id)
    _audit_transition(appr, "approval_request", requester, "ok", reason)
    notify.notify_async(notify.approval_created_msg(appr))
    return appr, ""


def get_approval(approval_id):
    row = db.get_approval_row(approval_id)
    return _row_to_dict(row) if row else None


def list_approvals(status=None, limit=50):
    sweep_expired()
    return [_row_to_dict(r) for r in db.list_approval_rows(status, limit)]


def decide_approval(approval_id, decision, note="", by="owner"):
    """Owner approves/rejects a pending request. Returns (row, error, http_code)."""
    appr = get_approval(approval_id)
    if not appr:
        return None, "approval not found", 404
    if decision not in ("approved", "rejected"):
        return None, "decision must be approved or rejected", 400
    if appr["status"] != "pending":
        return None, f"cannot decide from status {appr['status']}", 409
    ts = _now()
    db.update_approval(approval_id, {
        "status": decision,
        "updated": ts,
        "decided_by": by,
        "decided_at": ts,
        "decision_note": note or "",
    })
    appr = get_approval(approval_id)
    _audit_transition(
        appr, "approval_decision", by,
        "ok" if decision == "approved" else "rejected",
        f"{decision}: {note}".strip(),
    )
    return appr, "", 200


def report_result(approval_id, outcome, detail="", requester=""):
    """Requesting AI reports execution outcome. Returns (row, error, http_code)."""
    appr = get_approval(approval_id)
    if not appr:
        return None, "approval not found", 404
    if outcome not in ("executed", "failed"):
        return None, "outcome must be executed or failed", 400
    if appr["status"] != "approved":
        return None, f"cannot report from status {appr['status']}", 409
    if requester and requester != appr["requester"]:
        return None, "only the requesting AI may report this approval", 403
    ts = _now()
    db.update_approval(approval_id, {
        "status": outcome,
        "updated": ts,
        "executed_at": ts,
        "execute_detail": detail or "",
    })
    appr = get_approval(approval_id)
    _audit_transition(
        appr, "approval_result", appr["requester"],
        "ok" if outcome == "executed" else "failed", detail,
    )
    return appr, "", 200


def sweep_expired():
    """Auto-reject pending approvals older than 24h. Returns count."""
    rows = db.list_approval_rows("pending", 1000)
    now = _now()
    count = 0
    for row in rows:
        if row["expires_at"] and row["expires_at"] <= now:
            db.update_approval(row["id"], {
                "status": "rejected",
                "updated": now,
                "decided_by": "system",
                "decided_at": now,
                "decision_note": "auto-rejected: 24h without owner decision",
            })
            _audit_transition(
                _row_to_dict(db.get_approval_row(row["id"])),
                "approval_decision", "owner", "rejected",
                "auto-rejected after 24h",
            )
            count += 1
    return count
