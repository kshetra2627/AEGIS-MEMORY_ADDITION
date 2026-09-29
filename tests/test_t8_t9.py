"""Offline tests for T8a, T8b, T9.

Tests all logic that can be verified without a running Streamlit server or
live Hindsight credentials.

Run:
    python tests/test_t8_t9.py
"""
import os
import sys
import re

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
# T8a: pending_reviews.py — importable, has _do_retain_review, uses OWNER_MAP
# =============================================================================
import importlib
import ui.pages.pending_reviews as pr_mod

check("pending_reviews imports without error", True)
check("pending_reviews has _do_retain_review", hasattr(pr_mod, "_do_retain_review"))
check("pending_reviews has _ALL_OWNERS", hasattr(pr_mod, "_ALL_OWNERS"))
check("pending_reviews has _RISK_LEVELS", hasattr(pr_mod, "_RISK_LEVELS"))

# _ALL_OWNERS must come from OWNER_MAP (not hardcoded list)
from agents.router import OWNER_MAP
expected_owners = set(OWNER_MAP.values())
actual_owners = set(pr_mod._ALL_OWNERS)
check(
    "pending_reviews._ALL_OWNERS derived from OWNER_MAP",
    expected_owners.issubset(actual_owners),
    f"expected {expected_owners} subset of {actual_owners}",
)
check("pending_reviews._RISK_LEVELS = Low/Medium/High", set(pr_mod._RISK_LEVELS) == {"Low", "Medium", "High"})

# _do_retain_review no-ops when memory disabled (no exception)
mock_row = {
    "question": "Test question",
    "topic": "Vendor Compliance",
    "owner": "Legal",
    "risk": "Medium",
}
try:
    pr_mod._do_retain_review(1, "approve", "Looks good", "Procurement Compliance", "High", mock_row)
    check("_do_retain_review no-ops when memory disabled", True)
except Exception as e:
    check("_do_retain_review no-ops when memory disabled", False, str(e))

try:
    pr_mod._do_retain_review(2, "reject", "Insufficient", None, None, mock_row)
    check("_do_retain_review no correction no-ops when memory disabled", True)
except Exception as e:
    check("_do_retain_review no correction no-ops when memory disabled", False, str(e))

# =============================================================================
# T8b: agent.py — importable, has _do_retain_correction, helper functions
# =============================================================================
import ui.pages.agent as agent_mod

check("agent imports without error", True)
check("agent has _do_retain_correction", hasattr(agent_mod, "_do_retain_correction"))
check("agent has _render_memory_card", hasattr(agent_mod, "_render_memory_card"))
check("agent has _render_memory_trace", hasattr(agent_mod, "_render_memory_trace"))
check("agent has _render_compare", hasattr(agent_mod, "_render_compare"))
check("agent has _extract_summary", hasattr(agent_mod, "_extract_summary"))

# _do_retain_correction no-ops when memory disabled
mock_state = {
    "query": "Can we onboard a vendor?",
    "effective_query": "Can we onboard a vendor?",
    "topic": "Vendor Compliance",
    "owner": "Legal",
    "risk": "Medium",
}
try:
    agent_mod._do_retain_correction(mock_state, "Procurement Compliance", "High", "Enhanced review required.")
    check("_do_retain_correction no-ops when memory disabled", True)
except Exception as e:
    check("_do_retain_correction no-ops when memory disabled", False, str(e))

# agent._ALL_OWNERS and _RISK_LEVELS consistent with pending_reviews
check(
    "agent._ALL_OWNERS matches pending_reviews._ALL_OWNERS",
    set(agent_mod._ALL_OWNERS) == set(pr_mod._ALL_OWNERS),
)
check(
    "agent._RISK_LEVELS matches pending_reviews._RISK_LEVELS",
    set(agent_mod._RISK_LEVELS) == set(pr_mod._RISK_LEVELS),
)

# =============================================================================
# T9: _extract_summary logic
# =============================================================================
# QUESTION takes priority
text_with_question = "TYPE: correction\nDATE: 2026-06-12\nQUESTION: Can we onboard a payment vendor?\nREASON: Enhanced review required."
summary = agent_mod._extract_summary(text_with_question)
check("_extract_summary returns QUESTION content", "payment vendor" in summary, summary)

# REASON used when no QUESTION
text_with_reason = "TYPE: review_decision\nDATE: 2026-06-12\nREASON: Routing to Procurement Compliance."
summary2 = agent_mod._extract_summary(text_with_reason)
check("_extract_summary falls back to REASON", "Procurement" in summary2, summary2)

# Fallback to first non-blank line
text_fallback = "Some unstructured text here."
summary3 = agent_mod._extract_summary(text_fallback)
check("_extract_summary falls back to first line", "unstructured" in summary3, summary3)

# Long text is truncated
long_text = "QUESTION: " + "X" * 300
summary4 = agent_mod._extract_summary(long_text)
check("_extract_summary truncates long text", len(summary4) <= 203, len(summary4))  # 200 + "..."

# =============================================================================
# T9: Memory card reads from state["memory_context"] — no hardcoded data
# =============================================================================
# Verify _render_memory_card exists and its source doesn't contain hardcoded items
import inspect
src = inspect.getsource(agent_mod._render_memory_card)

# Must read from state["memory_context"], not a hardcoded list
check("_render_memory_card reads memory_context from state", 'memory_context' in src)
check("_render_memory_card reads memory_enabled from state", 'memory_enabled' in src)
check("_render_memory_card reads latency_ms from state", 'latency_ms' in src)

# Must NOT contain hardcoded memory IDs or demo text
hardcoded_patterns = ["vendor-onboarding-2026", "nwfs-seed", "FinSecure", "correction_example"]
for pat in hardcoded_patterns:
    check(
        f"_render_memory_card has no hardcoded demo data: {pat!r}",
        pat not in src,
    )

# =============================================================================
# T9: Compare mode uses run_query_streaming with retain=False
# =============================================================================
src_compare = inspect.getsource(agent_mod._render_compare)
check("_render_compare uses retain=False", "retain=False" in src_compare)
check("_render_compare calls run_query_streaming", "run_query_streaming" in src_compare)
check("_render_compare runs memory_enabled=False for OFF column", "memory_enabled=False" in src_compare)
check("_render_compare runs memory_enabled=True for ON column", "memory_enabled=True" in src_compare)

# =============================================================================
# T9: Memory toggle passes actual value to orchestrator
# =============================================================================
src_render = inspect.getsource(agent_mod.render)
check("render passes memory_toggle to run_query_streaming", "memory_enabled=memory_on" in src_render)
check("render reads memory_toggle from session_state", "memory_toggle" in src_render)

# =============================================================================
# T9: components.py NODE_TO_STAGE includes memory nodes
# =============================================================================
from ui.components import NODE_TO_STAGE, LIVE_STAGES
check("NODE_TO_STAGE has memory_recall", "memory_recall" in NODE_TO_STAGE)
check("NODE_TO_STAGE has memory_retain", "memory_retain" in NODE_TO_STAGE)
check("LIVE_STAGES has Recalling Memory step", any("Recalling" in s for s in LIVE_STAGES))

# =============================================================================
# T8b: pending_reviews render function still present (not removed)
# =============================================================================
check("pending_reviews has render function", hasattr(pr_mod, "render") and callable(pr_mod.render))
check("agent has render function", hasattr(agent_mod, "render") and callable(agent_mod.render))

# =============================================================================
# No hardcoded memory data in agent.py source
# =============================================================================
full_agent_src = inspect.getsource(agent_mod)
for pat in ["vendor-onboarding-2026", "nwfs-seed", "FinSecure Payment", "Procurement Compliance/High"]:
    check(
        f"agent.py has no hardcoded demo memory data: {pat!r}",
        pat not in full_agent_src,
    )

# =============================================================================
# Summary
# =============================================================================
print()
if failures:
    print("RESULT: {} test(s) FAILED: {}".format(len(failures), failures))
    sys.exit(1)
else:
    print("RESULT: All {} tests passed".format(
        sum(1 for line in open(__file__) if line.strip().startswith("check("))
    ))
    sys.exit(0)
