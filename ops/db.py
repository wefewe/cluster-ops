"""SQLite persistence layer (single-writer, WAL-friendly)."""
import os
import sqlite3
import threading
import time

_db_lock = threading.Lock()


def _db_path():
    from .config import DB_PATH
    return DB_PATH


def _connect():
    path = _db_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if missing. Idempotent; safe to call on every boot."""
    with _db_lock:
        conn = _connect()
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts INTEGER NOT NULL,
                    actor TEXT NOT NULL,
                    level TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL DEFAULT '',
                    result TEXT NOT NULL DEFAULT 'ok',
                    detail TEXT NOT NULL DEFAULT '',
                    rollback_hint TEXT NOT NULL DEFAULT ''
                )"""
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit(ts DESC)")
            conn.execute(
                """CREATE TABLE IF NOT EXISTS approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts INTEGER NOT NULL,
                    updated INTEGER NOT NULL,
                    requester TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL DEFAULT '',
                    params TEXT NOT NULL DEFAULT '{}',
                    reason TEXT NOT NULL DEFAULT '',
                    level TEXT NOT NULL DEFAULT 'L2',
                    status TEXT NOT NULL DEFAULT 'pending',
                    decided_by TEXT NOT NULL DEFAULT '',
                    decided_at INTEGER NOT NULL DEFAULT 0,
                    decision_note TEXT NOT NULL DEFAULT '',
                    executed_at INTEGER NOT NULL DEFAULT 0,
                    execute_detail TEXT NOT NULL DEFAULT '',
                    expires_at INTEGER NOT NULL DEFAULT 0
                )"""
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status)")
            conn.execute(
                """CREATE TABLE IF NOT EXISTS token_usage (
                    name TEXT PRIMARY KEY,
                    last_used INTEGER NOT NULL DEFAULT 0
                )"""
            )
            conn.commit()
        finally:
            conn.close()


def insert_audit(entry):
    """Insert one audit row. Returns the new row id."""
    with _db_lock:
        conn = _connect()
        try:
            cur = conn.execute(
                """INSERT INTO audit
                   (ts, actor, level, action, target, result, detail, rollback_hint)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry["ts"], entry["actor"], entry["level"], entry["action"],
                    entry.get("target", ""), entry.get("result", "ok"),
                    entry.get("detail", ""), entry.get("rollback_hint", ""),
                ),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


def list_audit(limit=50, actor=None, level=None):
    """Newest-first audit rows as plain dicts."""
    limit = max(1, min(int(limit or 50), 500))
    where, params = [], []
    if actor:
        where.append("actor = ?")
        params.append(actor)
    if level:
        where.append("level = ?")
        params.append(level)
    sql = "SELECT * FROM audit"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY ts DESC, id DESC LIMIT ?"
    params.append(limit)
    with _db_lock:
        conn = _connect()
        try:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


def insert_approval(entry):
    """Insert one approval row. Returns the new row id."""
    with _db_lock:
        conn = _connect()
        try:
            cur = conn.execute(
                """INSERT INTO approvals
                   (ts, updated, requester, action, target, params, reason,
                    level, status, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry["ts"], entry["updated"], entry["requester"],
                    entry["action"], entry["target"], entry["params"],
                    entry["reason"], entry["level"], entry["status"],
                    entry["expires_at"],
                ),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


def get_approval_row(approval_id):
    with _db_lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM approvals WHERE id = ?", (approval_id,)
            ).fetchone()
            return row
        finally:
            conn.close()


def list_approval_rows(status=None, limit=50):
    limit = max(1, min(int(limit or 50), 500))
    where, params = [], []
    if status:
        where.append("status = ?")
        params.append(status)
    sql = "SELECT * FROM approvals"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY ts DESC, id DESC LIMIT ?"
    params.append(limit)
    with _db_lock:
        conn = _connect()
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()


def update_approval(approval_id, fields):
    """Update allowed mutable fields of an approval row."""
    allowed = (
        "updated", "status", "decided_by", "decided_at", "decision_note",
        "executed_at", "execute_detail",
    )
    sets = [f"{k} = ?" for k in fields if k in allowed]
    values = [fields[k] for k in fields if k in allowed]
    if not sets:
        return
    values.append(approval_id)
    with _db_lock:
        conn = _connect()
        try:
            conn.execute(
                f"UPDATE approvals SET {', '.join(sets)} WHERE id = ?", values
            )
            conn.commit()
        finally:
            conn.close()


TOKEN_TOUCH_INTERVAL = 60  # seconds: at most one usage write per token per minute


def touch_token(name):
    """Record a token use, throttled to one write per minute. Best-effort."""
    now = int(time.time())
    with _db_lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT last_used FROM token_usage WHERE name = ?", (name,)
            ).fetchone()
            if row and now - row["last_used"] < TOKEN_TOUCH_INTERVAL:
                return
            conn.execute(
                """INSERT INTO token_usage (name, last_used) VALUES (?, ?)
                   ON CONFLICT(name) DO UPDATE SET last_used = excluded.last_used""",
                (name, now),
            )
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()


def list_token_usage():
    """{name: last_used} for all tracked tokens."""
    with _db_lock:
        conn = _connect()
        try:
            rows = conn.execute("SELECT name, last_used FROM token_usage").fetchall()
            return {r["name"]: r["last_used"] for r in rows}
        finally:
            conn.close()
