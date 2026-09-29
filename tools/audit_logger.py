"""Persists every query to SQLite (database/audit.db) and exports to logs/audit_log.json.

T7b: Added nullable memory_ids (JSON list) and memory_used (bool) columns.
     Migration is safe for existing databases -- columns are added only if missing.
     Values come from the real runtime state (state["memory_context"]) set in
     node_audit_logging, never hardcoded.
"""
import os
import json
import sqlite3
from datetime import datetime

DB_PATH = os.path.join("database", "audit.db")
JSON_PATH = os.path.join("logs", "audit_log.json")

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    question TEXT,
    retrieved_documents TEXT,
    retrieved_chunks TEXT,
    topic TEXT,
    owner TEXT,
    risk TEXT,
    confidence REAL,
    answer TEXT,
    citations TEXT,
    escalated INTEGER,
    approval_status TEXT,
    llm_provider TEXT,
    retrieval_latency REAL,
    total_latency REAL,
    execution_status TEXT,
    approval_timestamp TEXT,
    rejection_reason TEXT,
    user_id TEXT
)
"""

# Columns added by T7b — applied via ALTER TABLE if not present.
_MIGRATION_COLUMNS = [
    ("memory_used", "INTEGER DEFAULT 0"),
    ("memory_ids", "TEXT DEFAULT '[]'"),
    ("user_id", "TEXT"),
]


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    _apply_migrations(conn)
    return conn


def _apply_migrations(conn: sqlite3.Connection) -> None:
    """Add new columns to an existing audit.db if they are missing.

    Safe to call repeatedly — uses PRAGMA table_info to check before altering.
    """
    cur = conn.execute("PRAGMA table_info(audit_log)")
    existing = {row[1] for row in cur.fetchall()}
    for col_name, col_def in _MIGRATION_COLUMNS:
        if col_name not in existing:
            try:
                conn.execute(f"ALTER TABLE audit_log ADD COLUMN {col_name} {col_def}")
                conn.commit()
            except sqlite3.OperationalError as e:
                # Column may have been added by a concurrent process — ignore.
                print(f"[audit_logger] migration note: {e}")


def log_query(record: dict) -> int:
    """Writes one audit record. Never raises -- logging failures are printed, not fatal."""
    record = dict(record)
    record.setdefault("timestamp", datetime.utcnow().isoformat())

    # Normalise memory provenance fields from the runtime state.
    # These are populated by node_audit_logging in orchestrator.py from
    # state["memory_context"] — never hardcoded.
    memory_used = int(bool(record.get("memory_used", False)))
    memory_ids_raw = record.get("memory_ids", [])
    memory_ids = json.dumps(memory_ids_raw if isinstance(memory_ids_raw, list) else [])

    try:
        conn = _get_conn()
        cur = conn.execute(
            """INSERT INTO audit_log
            (timestamp, question, retrieved_documents, retrieved_chunks, topic, owner, risk,
             confidence, answer, citations, escalated, approval_status, llm_provider,
             retrieval_latency, total_latency, execution_status, approval_timestamp,
             rejection_reason, memory_used, memory_ids, user_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                record.get("timestamp"),
                record.get("question"),
                json.dumps(record.get("retrieved_documents", [])),
                json.dumps(record.get("retrieved_chunks", [])),
                record.get("topic"),
                record.get("owner"),
                record.get("risk"),
                record.get("confidence"),
                record.get("answer"),
                json.dumps(record.get("citations", [])),
                int(record.get("escalated", False)),
                record.get("approval_status", "N/A"),
                record.get("llm_provider"),
                record.get("retrieval_latency"),
                record.get("total_latency"),
                record.get("execution_status", "success"),
                record.get("approval_timestamp"),
                record.get("rejection_reason"),
                memory_used,
                memory_ids,
                str(record["user_id"]) if record.get("user_id") is not None else None,
            ),
        )
        conn.commit()
        row_id = cur.lastrowid
        conn.close()
        _export_json()
        return row_id
    except Exception as e:
        print(f"[audit_logger] failed to log query: {e}")
        return -1


def update_approval(row_id: int, approval_status: str, rejection_reason: str = None):
    try:
        conn = _get_conn()
        conn.execute(
            "UPDATE audit_log SET approval_status=?, approval_timestamp=?, rejection_reason=? WHERE id=?",
            (approval_status, datetime.utcnow().isoformat(), rejection_reason, row_id),
        )
        conn.commit()
        conn.close()
        _export_json()
    except Exception as e:
        print(f"[audit_logger] failed to update approval: {e}")


def fetch_all(user_id: str | None = None) -> list[dict]:
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        if user_id is None:
            rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM audit_log WHERE user_id = ? ORDER BY id DESC",
                (str(user_id),),
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[audit_logger] failed to fetch: {e}")
        return []


def _export_json():
    try:
        os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
        rows = fetch_all()
        with open(JSON_PATH, "w") as f:
            json.dump(rows, f, indent=2, default=str)
    except Exception as e:
        print(f"[audit_logger] failed to export json: {e}")
