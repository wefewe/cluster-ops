"""Smoke tests for the ops/ package (Phase 0 + Phase 1 audit). Zero dependencies."""
import time

from ops.auth import sign_session, verify_session, verify_token


def test_session_roundtrip():
    ts = str(int(time.time()))
    assert verify_session(f"ops_token={ts}.{sign_session(ts)}")


def test_session_rejects_garbage():
    assert not verify_session("ops_token=bogus")
    assert not verify_session("")
    assert not verify_session("ops_token=12345.nothex")


def test_config_defaults():
    from ops import config
    assert config.PORT == 8080
    assert config.ADMIN_PASSWORD  # generated fallback keeps server bootable
    assert len(config.SESSION_SECRET) >= 32


def test_token_verify():
    assert verify_token("secret123", "secret123")
    assert not verify_token("wrong", "secret123")
    assert not verify_token("", "secret123")
    assert not verify_token("secret123", "")


def test_audit_validation():
    from ops.audit import validate_audit_payload
    ok, _ = validate_audit_payload({"actor": "muse-spark", "level": "L1",
                                    "action": "restart_service"})
    assert ok
    ok, err = validate_audit_payload({"actor": "hacker", "level": "L1",
                                      "action": "restart_service"})
    assert not ok and "actor" in err
    ok, err = validate_audit_payload({"actor": "muse-spark", "level": "L9",
                                      "action": "restart_service"})
    assert not ok and "level" in err
    ok, err = validate_audit_payload({"level": "L1", "action": "restart_service"})
    assert not ok and "actor" in err


def test_audit_db_roundtrip(tmp_path, monkeypatch):
    import ops.config as config
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    from ops import db
    from ops.audit import query_audit, record_audit
    db.init_db()
    row_id, err = record_audit({"actor": "muse-spark", "level": "L1",
                                "action": "restart_service",
                                "target": "cline2api_cline2api",
                                "detail": "container unhealthy"})
    assert err == "" and row_id == 1
    items = query_audit()
    assert len(items) == 1
    assert items[0]["actor"] == "muse-spark"
    assert items[0]["target"] == "cline2api_cline2api"
    assert query_audit(actor="openclaw") == []
    assert len(query_audit(level="L1")) == 1
