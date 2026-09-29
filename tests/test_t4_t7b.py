"""Offline unit tests for T4-T7b.

All tests run with MEMORY_ENABLED=false and make zero network calls.
They exercise the logic paths, not the Hindsight API itself.

Run:
    python tests/test_t4_t7b.py
"""

import os
import sys
import json
import sqlite3
import tempfile

os.environ["MEMORY_ENABLED"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

failures = []


def check(name, condition, detail=""):
    if condition:
        print("[PASS]  {}{}".format(name, "  -- " + str(detail) if detail else ""))
    else:
        print("[FAIL]  {}{}".format(name, "  -- " + str(detail) if detail else ""))
        failures.append(name)


# =============================================================================
# T6: governance_agent — citation rules
# =============================================================================
from agents.governance_agent import (
    _every_paragraph_cited,
    _has_memory_only_citation,
    validate,
    REFUSAL_MESSAGE,
)

# Chunk-only paragraph: PASS
check("chunk-only paragraph accepted",
      _every_paragraph_cited("This is grounded. [Chunk c1]"))

# Mixed chunk+memory paragraph: PASS (chunk present)
check("mixed chunk+memory paragraph accepted",
      _every_paragraph_cited("Grounded fact [Chunk c1] with precedent [Memory m1]."))

# Memory-only paragraph: FAIL (no chunk)
check("memory-only paragraph refused",
      not _every_paragraph_cited("Precedent says this. [Memory m1]"))

# No citation at all: FAIL
check("no citation refused",
      not _every_paragraph_cited("This has no citations."))

# Empty: FAIL
check("empty string refused",
      not _every_paragraph_cited(""))

# _has_memory_only_citation
check("has_memory_only: memory with no chunk = True",
      _has_memory_only_citation("See [Memory m1] for precedent."))
check("has_memory_only: chunk present = False",
      not _has_memory_only_citation("See [Chunk c1] and [Memory m1]."))
check("has_memory_only: no citations = False",
      not _has_memory_only_citation("No citations here."))

# validate() — memory-only answer is refused because uncited_paragraph
mock_chunks = [{"qualifies": True, "score": 0.85, "chunk_id": "c1", "text": "policy text",
                "title": "Policy", "filename": "p.pdf", "page": 1, "section": "S1", "clause": "C1"}]
memory_only_answer = "This answer uses only memory. [Memory m1]"
result = validate(True, mock_chunks, memory_only_answer, {"score": 80})
check("validate: memory-only answer is refused",
      not result["passed"] and result["reason"] == "uncited_paragraph")

# validate() — chunk+memory answer passes
mixed_answer = "Policy says X [Chunk c1]. Prior case confirms Y [Memory m1]. [Chunk c1]"
result2 = validate(True, mock_chunks, mixed_answer, {"score": 80})
check("validate: chunk+memory answer passes",
      result2["passed"])

# =============================================================================
# T5: compliance_agent — memory_block parameter
# =============================================================================
from agents.compliance_agent import generate_draft_answer, SYSTEM_PROMPT

# SYSTEM_PROMPT must contain the memory rules section
check("SYSTEM_PROMPT contains memory context rules",
      "ORGANISATIONAL MEMORY RULES" in SYSTEM_PROMPT or "organizational_memory" in SYSTEM_PROMPT.lower()
      or "memory" in SYSTEM_PROMPT.lower())

# generate_draft_answer accepts memory_block param (no qualifying chunks → returns empty)
result_no_chunks = generate_draft_answer("test query", [], memory_block="<organizational_memory>test</organizational_memory>")
check("generate_draft_answer accepts memory_block with no qualifying chunks",
      result_no_chunks["text"] == "" and result_no_chunks["provider"] == "none")

# =============================================================================
# T7: mask_pii
# =============================================================================
from memory.service import mask_pii

check("mask_pii masks email",
      "[EMAIL]" in mask_pii("Contact user@example.com for details."))
check("mask_pii masks phone (US format)",
      "[PHONE]" in mask_pii("Call 555-123-4567 now."))
check("mask_pii masks 8+ digit account number",
      "[ACCOUNT_NUM]" in mask_pii("Account 12345678 is affected."))
check("mask_pii preserves non-PII text",
      "Vendor Compliance" in mask_pii("Topic: Vendor Compliance"))
check("mask_pii preserves department names",
      "Procurement Compliance" in mask_pii("Owner: Procurement Compliance"))

# =============================================================================
# T7: retain_case — memory disabled path (no exception, no network call)
# =============================================================================
from memory.service import retain_case, retain_review, retain_correction

mock_state_passed = {
    "query": "What is the retention period?",
    "effective_query": "What is the retention period?",
    "topic": "Records Retention",
    "owner": "Legal",
    "risk": "Low",
    "governance_passed": True,
    "governance_reason": "ok",
    "final_answer": "7 years per FCA rules. [Chunk c1]",
    "user_id": "anonymous",
    "user_role": "compliance_officer",
}

try:
    retain_case(mock_state_passed)   # memory disabled — should be a no-op
    check("retain_case no-ops when memory disabled", True)
except Exception as e:
    check("retain_case no-ops when memory disabled", False, str(e))

mock_state_gap = {
    "query": "What is the MFA policy?",
    "topic": "Cybersecurity",
    "owner": "CISO",
    "risk": "High",
    "governance_passed": False,
    "governance_reason": "insufficient_evidence",
    "final_answer": "",
    "user_id": "anonymous",
    "user_role": "compliance_officer",
}
try:
    retain_case(mock_state_gap)   # memory disabled — should be a no-op
    check("retain_case (corpus_gap) no-ops when memory disabled", True)
except Exception as e:
    check("retain_case (corpus_gap) no-ops when memory disabled", False, str(e))

# retain_review no-ops when disabled
try:
    retain_review(1, "approve", "Looks good", state=mock_state_passed)
    check("retain_review no-ops when memory disabled", True)
except Exception as e:
    check("retain_review no-ops when memory disabled", False, str(e))

# retain_correction no-ops when disabled
try:
    retain_correction(mock_state_passed, "Procurement Compliance", "High", "Enhanced review required.")
    check("retain_correction no-ops when memory disabled", True)
except Exception as e:
    check("retain_correction no-ops when memory disabled", False, str(e))

# =============================================================================
# T7b: audit_logger — memory_ids + memory_used columns, migration safety
# =============================================================================
import tools.audit_logger as al

# Use a temp database for isolation.
_orig_db = al.DB_PATH
_orig_json = al.JSON_PATH
with tempfile.TemporaryDirectory() as tmpdir:
    al.DB_PATH = os.path.join(tmpdir, "audit.db")
    al.JSON_PATH = os.path.join(tmpdir, "audit_log.json")

    # Write a record WITH memory.
    record_with_mem = {
        "question": "Test question",
        "retrieved_documents": [],
        "retrieved_chunks": [],
        "topic": "Vendor Compliance",
        "owner": "Procurement Compliance",
        "risk": "High",
        "confidence": 75.0,
        "answer": "Answer text [Chunk c1]",
        "citations": [],
        "escalated": False,
        "approval_status": "N/A",
        "llm_provider": "groq",
        "retrieval_latency": 0.1,
        "total_latency": 0.5,
        "execution_status": "success",
        "memory_used": True,
        "memory_ids": ["m-abc123", "m-def456"],
    }
    row_id = al.log_query(record_with_mem)
    check("log_query with memory returns valid row_id", row_id > 0, row_id)

    # Verify memory columns are stored correctly.
    conn = sqlite3.connect(al.DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM audit_log WHERE id=?", (row_id,)).fetchone()
    check("memory_used=1 stored correctly", row["memory_used"] == 1, row["memory_used"])
    stored_ids = json.loads(row["memory_ids"])
    check("memory_ids stored correctly", stored_ids == ["m-abc123", "m-def456"], stored_ids)
    conn.close()

    # Write a record WITHOUT memory.
    record_no_mem = dict(record_with_mem)
    record_no_mem["memory_used"] = False
    record_no_mem["memory_ids"] = []
    row_id2 = al.log_query(record_no_mem)
    conn = sqlite3.connect(al.DB_PATH)
    conn.row_factory = sqlite3.Row
    row2 = conn.execute("SELECT * FROM audit_log WHERE id=?", (row_id2,)).fetchone()
    check("memory_used=0 when no memory", row2["memory_used"] == 0, row2["memory_used"])
    check("memory_ids=[] when no memory", json.loads(row2["memory_ids"]) == [], json.loads(row2["memory_ids"]))
    conn.close()

    # Migration safety: simulate an OLD database without the new columns.
    old_db_path = os.path.join(tmpdir, "old_audit.db")
    old_conn = sqlite3.connect(old_db_path)
    old_conn.execute("""
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, question TEXT, retrieved_documents TEXT,
            retrieved_chunks TEXT, topic TEXT, owner TEXT, risk TEXT,
            confidence REAL, answer TEXT, citations TEXT, escalated INTEGER,
            approval_status TEXT, llm_provider TEXT, retrieval_latency REAL,
            total_latency REAL, execution_status TEXT,
            approval_timestamp TEXT, rejection_reason TEXT
        )
    """)
    old_conn.commit()
    old_conn.close()

    al.DB_PATH = old_db_path
    # Opening an old db should apply migrations without error.
    try:
        conn2 = al._get_conn()
        cur = conn2.execute("PRAGMA table_info(audit_log)")
        cols = {r[1] for r in cur.fetchall()}
        conn2.close()
        check("migration adds memory_used to old db", "memory_used" in cols, cols)
        check("migration adds memory_ids to old db", "memory_ids" in cols, cols)
    except Exception as e:
        check("migration on old db does not crash", False, str(e))

# Restore paths
al.DB_PATH = _orig_db
al.JSON_PATH = _orig_json

# =============================================================================
# T4: orchestrator — graph compiles, new GraphState fields present
# =============================================================================
import agents.orchestrator as orch

# Force graph recompilation after env changes.
orch._reset_graph()
graph = orch.get_graph()
check("orchestrator graph compiles with memory nodes", graph is not None)

# GraphState type should include memory fields.
state_fields = orch.GraphState.__annotations__
check("GraphState has memory_enabled", "memory_enabled" in state_fields)
check("GraphState has memory_context", "memory_context" in state_fields)
check("GraphState has memory_ok", "memory_ok" in state_fields)
check("GraphState has memory_block", "memory_block" in state_fields)
check("GraphState has retain", "retain" in state_fields)
check("GraphState has user_id", "user_id" in state_fields)
check("GraphState has user_role", "user_role" in state_fields)

# run_query accepts new parameters (type-check only, no LLM call).
import inspect
sig = inspect.signature(orch.run_query)
params = list(sig.parameters.keys())
check("run_query has memory_enabled param", "memory_enabled" in params)
check("run_query has retain param", "retain" in params)
check("run_query has user_id param", "user_id" in params)

sig2 = inspect.signature(orch.run_query_streaming)
params2 = list(sig2.parameters.keys())
check("run_query_streaming has memory_enabled param", "memory_enabled" in params2)
check("run_query_streaming has retain param", "retain" in params2)

# =============================================================================
# Summary
# =============================================================================
print()
if failures:
    print("RESULT: {} test(s) FAILED: {}".format(len(failures), failures))
    sys.exit(1)
else:
    print("RESULT: All tests passed ({} checks)".format(
        sum(1 for line in open(__file__) if line.strip().startswith("check("))
    ))
    sys.exit(0)
