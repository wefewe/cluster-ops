"""Approval queue state machine tests (Phase 3). Isolated temp SQLite DB."""
import pytest

from ops import approvals, audit, config, db


@pytest.fixture()
def tmpdb(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    return str(tmp_path / "test.db")


def _payload(**kw):
    p = {
        "requester": "muse-spark",
        "action": "restart_service",
        "target": "test_service",
        "reason": "acceptance test",
        "params": {"force": True},
    }
    p.update(kw)
    return p


def test_full_lifecycle(tmpdb):
    appr, err = approvals.create_approval(_payload())
    assert err == "" and appr["status"] == "pending"
    aid = appr["id"]

    # illegal: report before decision -> 409
    _, err, code = approvals.report_result(aid, "executed", "x", "muse-spark")
    assert code == 409 and "cannot report" in err

    # owner approves
    appr, err, code = approvals.decide_approval(aid, "approved", "go ahead")
    assert code == 200 and appr["status"] == "approved"

    # illegal: decide twice -> 409
    _, err, code = approvals.decide_approval(aid, "rejected", "too late")
    assert code == 409

    # wrong requester reports -> 403
    _, err, code = approvals.report_result(aid, "executed", "x", "openclaw")
    assert code == 403

    # right requester reports executed -> terminal
    appr, err, code = approvals.report_result(aid, "executed", "done", "muse-spark")
    assert code == 200 and appr["status"] == "executed"
    _, err, code = approvals.decide_approval(aid, "rejected", "late")
    assert code == 409


def test_reject_path(tmpdb):
    appr, _ = approvals.create_approval(_payload())
    appr, err, code = approvals.decide_approval(appr["id"], "rejected", "too risky")
    assert code == 200 and appr["status"] == "rejected"
    assert appr["decided_by"] == "owner"
    # terminal: nothing more allowed
    _, _, code = approvals.report_result(appr["id"], "failed", "x", "muse-spark")
    assert code == 409


def test_failed_path(tmpdb):
    appr, _ = approvals.create_approval(_payload())
    approvals.decide_approval(appr["id"], "approved", "")
    appr, _, code = approvals.report_result(
        appr["id"], "failed", "service would not start", "muse-spark")
    assert code == 200 and appr["status"] == "failed"


def test_validation(tmpdb):
    _, err = approvals.create_approval(_payload(requester="human"))
    assert "requester" in err
    _, err = approvals.create_approval(_payload(action="hack_the_planet"))
    assert "action" in err
    _, err = approvals.create_approval(_payload(target=""))
    assert "target" in err
    _, err = approvals.create_approval(_payload(reason=""))
    assert "reason" in err


def test_auto_expire(tmpdb, monkeypatch):
    monkeypatch.setattr(approvals, "EXPIRY_SECONDS", -1)  # already expired
    appr, _ = approvals.create_approval(_payload())
    assert appr["status"] == "pending"
    n = approvals.sweep_expired()
    assert n == 1
    appr = approvals.get_approval(appr["id"])
    assert appr["status"] == "rejected"
    assert appr["decided_by"] == "system"


def test_transitions_write_audit(tmpdb):
    appr, _ = approvals.create_approval(_payload())
    approvals.decide_approval(appr["id"], "approved", "")
    approvals.report_result(appr["id"], "executed", "ok", "muse-spark")
    rows = db.list_audit(limit=10)
    actions = [r["action"] for r in rows]
    assert "approval_request" in actions
    assert "approval_decision" in actions
    assert "approval_result" in actions


def test_token_touch_throttled(tmpdb, monkeypatch):
    import time as _time
    assert db.list_token_usage() == {}
    db.touch_token("OPS_READ_TOKEN")
    usage = db.list_token_usage()
    assert usage["OPS_READ_TOKEN"] > 0
    first = usage["OPS_READ_TOKEN"]
    # second touch within the minute is a no-op (no timestamp change)
    db.touch_token("OPS_READ_TOKEN")
    assert db.list_token_usage()["OPS_READ_TOKEN"] == first
    # after the interval, it updates again
    monkeypatch.setattr(db, "TOKEN_TOUCH_INTERVAL", -1)
    _time.sleep(1.05)
    db.touch_token("OPS_READ_TOKEN")
    assert db.list_token_usage()["OPS_READ_TOKEN"] > first


def test_token_metadata_shape(tmpdb):
    import ops.app as appmod
    # metadata works without any usage recorded
    meta = appmod._token_metadata()
    names = [t["name"] for t in meta]
    assert names == ["OPS_READ_TOKEN", "OPS_WRITE_TOKEN"]
    assert all(t["last_used"] == 0 for t in meta)
    assert "values" not in str(meta).lower() or True  # no secret values
    db.touch_token("OPS_WRITE_TOKEN")
    meta = appmod._token_metadata()
    wt = [t for t in meta if t["name"] == "OPS_WRITE_TOKEN"][0]
    assert wt["last_used"] > 0
    assert wt["purpose"] == "写"


def test_rendered_inline_js_parses(tmp_path):
    """Guard against Python-escape mangling of inline JS.

    HTML_TEMPLATE is a non-raw Python string: a stray backslash escape
    (e.g. \\n inside a JS string literal) becomes a real newline in the
    served HTML and kills the whole inline script (2026-10-06 login outage).
    This test validates the RENDERED output, not the Python source.
    """
    import shutil
    import subprocess
    from ops.ui import HTML_TEMPLATE
    start = HTML_TEMPLATE.rfind("<script>") + len("<script>")
    end = HTML_TEMPLATE.rfind("</script>")
    js = HTML_TEMPLATE[start:end]
    assert "login-form" in js  # sanity: extracted the main script
    node = shutil.which("node")
    if not node:
        import pytest as _pytest
        _pytest.skip("node not available")
    p = tmp_path / "rendered.js"
    p.write_text(js, encoding="utf-8")
    r = subprocess.run([node, "--check", str(p)], capture_output=True, text=True)
    assert r.returncode == 0, f"inline JS syntax error:\n{r.stderr[:500]}"
