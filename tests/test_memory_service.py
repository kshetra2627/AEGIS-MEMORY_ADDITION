"""Unit tests for memory/service.py — T3 acceptance tests.

Tests:
  1. format_prompt_block([]) returns ""
  2. format_prompt_block with items returns a delimited block containing the
     <organizational_memory> opening and closing tags.
  3. Each item appears as [Memory <id>] in the block.
  4. Block contains the untrusted-context warning header lines.
  5. Block is capped at _CHAR_BUDGET characters.
  6. recall_for_query returns MemoryResult (ok=False, items=[]) when memory is disabled.

Run with:
    python tests/test_memory_service.py
"""

import os
import sys

# Ensure project root is on the path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force memory disabled for all unit tests — these tests must not make
# network calls.
os.environ["MEMORY_ENABLED"] = "false"

from memory.hindsight_client import MemoryItem, MemoryResult
from memory.service import (
    format_prompt_block,
    recall_for_query,
    _CHAR_BUDGET,
    _first_summary_line,
)

failures = []


def check(name, condition, detail=""):
    if condition:
        print("[PASS]  {}{}".format(name, " -- " + detail if detail else ""))
    else:
        print("[FAIL]  {}{}".format(name, " -- " + detail if detail else ""))
        failures.append(name)


# ---------------------------------------------------------------------------
# Test 1: empty input returns empty string (no delimiters)
# ---------------------------------------------------------------------------
result = format_prompt_block([])
check(
    "empty list returns empty string",
    result == "",
    repr(result),
)

# ---------------------------------------------------------------------------
# Test 2: non-empty input returns a delimited block
# ---------------------------------------------------------------------------
items = [
    MemoryItem(
        id="m-abc123",
        text=(
            "TYPE: correction\n"
            "DATE: 2026-06-12\n"
            "QUESTION: Can we onboard a payment vendor without a security questionnaire?\n"
            "TOPIC: Vendor Compliance\n"
            "AEGIS_OWNER: Legal | AEGIS_RISK: Medium\n"
            "CORRECTED_OWNER: Procurement Compliance | CORRECTED_RISK: High\n"
            "REASON: Enhanced vendor review required."
        ),
        type="correction",
        date="2026-06-12",
        score=0.85,
    )
]
block = format_prompt_block(items)

check(
    "block opens with <organizational_memory>",
    block.startswith("<organizational_memory>"),
    block[:50],
)
check(
    "block closes with </organizational_memory>",
    block.strip().endswith("</organizational_memory>"),
    block[-30:],
)
check(
    "block contains [Memory m-abc123]",
    "[Memory m-abc123]" in block,
    "",
)
check(
    "block contains untrusted-context warning",
    "context ONLY" in block,
    "",
)
check(
    "block contains chunk citation reminder",
    "[Chunk <id>]" in block or "[Chunk" in block,
    "",
)
check(
    "block contains date from item",
    "2026-06-12" in block,
    "",
)
check(
    "block contains type from item",
    "correction" in block,
    "",
)

# ---------------------------------------------------------------------------
# Test 3: item summary line is extracted from QUESTION: field
# ---------------------------------------------------------------------------
summary = _first_summary_line(items[0].text)
check(
    "_first_summary_line extracts QUESTION content",
    "payment vendor" in summary,
    repr(summary),
)

# ---------------------------------------------------------------------------
# Test 4: multiple items all appear in block
# ---------------------------------------------------------------------------
items_multi = [
    MemoryItem(id="m-001", text="TYPE: case\nQUESTION: First question about sanctions.\nREASON: reason1", type="case", date="2026-05-01", score=0.9),
    MemoryItem(id="m-002", text="TYPE: correction\nQUESTION: Second question about GDPR.\nREASON: reason2", type="correction", date="2026-05-02", score=0.8),
    MemoryItem(id="m-003", text="TYPE: review_decision\nQUESTION: Third question about AML.\nREASON: reason3", type="review_decision", date="2026-05-03", score=0.7),
]
block_multi = format_prompt_block(items_multi)
check("multi-item block contains [Memory m-001]", "[Memory m-001]" in block_multi)
check("multi-item block contains [Memory m-002]", "[Memory m-002]" in block_multi)
check("multi-item block contains [Memory m-003]", "[Memory m-003]" in block_multi)
check(
    "multi-item block has correct line count (3 items + header lines)",
    block_multi.count("[Memory m-") == 3,
    "found {} [Memory m-] refs".format(block_multi.count("[Memory m-")),
)

# ---------------------------------------------------------------------------
# Test 5: character budget is enforced
# ---------------------------------------------------------------------------
# Build an item whose single line is very long.
long_text = "TYPE: case\nQUESTION: " + ("X" * 5000) + "\nREASON: reason"
big_items = [
    MemoryItem(id="m-big-{}".format(i), text=long_text, type="case", date="2026-01-01", score=0.5)
    for i in range(5)
]
big_block = format_prompt_block(big_items)
check(
    "block with large items is capped at CHAR_BUDGET",
    len(big_block) <= _CHAR_BUDGET,
    "len={}, budget={}".format(len(big_block), _CHAR_BUDGET),
)
check(
    "capped block still has opening delimiter",
    "<organizational_memory>" in big_block,
    "",
)
check(
    "capped block still has closing delimiter",
    "</organizational_memory>" in big_block,
    "",
)

# ---------------------------------------------------------------------------
# Test 6: recall_for_query returns MemoryResult(ok=False) when memory disabled
# ---------------------------------------------------------------------------
result = recall_for_query("vendor onboarding security questionnaire", topic="Vendor Compliance")
check(
    "recall_for_query returns MemoryResult when memory disabled",
    isinstance(result, MemoryResult),
    type(result).__name__,
)
check(
    "recall_for_query ok=False when memory disabled",
    result.ok is False,
    "ok={}".format(result.ok),
)
check(
    "recall_for_query items=[] when memory disabled",
    result.items == [],
    "items={}".format(result.items),
)
check(
    "recall_for_query error is non-empty string when memory disabled",
    isinstance(result.error, str) and len(result.error) > 0,
    repr(result.error),
)

# ---------------------------------------------------------------------------
# Test 7: item with no QUESTION/REASON falls back to first non-blank line
# ---------------------------------------------------------------------------
fallback_text = "TYPE: audit_finding\nDATE: 2026-04-01\nSome other content here."
summary2 = _first_summary_line(fallback_text)
check(
    "_first_summary_line falls back to first non-blank line when no QUESTION/REASON",
    len(summary2) > 0,
    repr(summary2),
)

# ---------------------------------------------------------------------------
# Test 8: item with None date/type renders gracefully
# ---------------------------------------------------------------------------
item_none = MemoryItem(id="m-none", text="QUESTION: test question", type=None, date=None, score=None)
block_none = format_prompt_block([item_none])
check(
    "item with None date/type renders without error",
    "[Memory m-none]" in block_none,
    block_none[:100],
)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
if failures:
    print("RESULT: {} test(s) FAILED: {}".format(len(failures), failures))
    sys.exit(1)
else:
    print("RESULT: All {} tests passed".format(
        sum(1 for line in open(__file__) if line.strip().startswith("check("))
    ))
    sys.exit(0)
