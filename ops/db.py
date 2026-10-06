"""SQLite persistence layer (single-writer, WAL-friendly)."""
import os
import sqlite3
import threading

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
