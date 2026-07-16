"""Persists every query to SQLite (database/audit.db) and exports to logs/audit_log.json."""
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
    rejection_reason TEXT
)
"""


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    return conn


def log_query(record: dict) -> int:
    """Writes one audit record. Never raises -- logging failures are printed, not fatal."""
    record = dict(record)
    record.setdefault("timestamp", datetime.utcnow().isoformat())
    try:
        conn = _get_conn()
        cur = conn.execute(
            """INSERT INTO audit_log
            (timestamp, question, retrieved_documents, retrieved_chunks, topic, owner, risk,
             confidence, answer, citations, escalated, approval_status, llm_provider,
             retrieval_latency, total_latency, execution_status, approval_timestamp, rejection_reason)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
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


def fetch_all() -> list[dict]:
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC").fetchall()
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
