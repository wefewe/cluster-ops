"""Smoke tests for the ops/ package split (Phase 0). Zero dependencies."""
import time

from ops.auth import sign_session, verify_session


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
