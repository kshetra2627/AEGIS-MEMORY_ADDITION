"""Smoke test for the Hindsight memory client wrapper.

Usage:
    python scripts/smoke_hindsight.py

What it tests:
  1. is_enabled() returns True (requires HINDSIGHT_API_URL + HINDSIGHT_API_KEY in .env)
  2. retain() stores one item without raising
  3. recall() retrieves relevant items without raising
  4. With a wrong API key: recall() returns ok=False and does NOT raise
  5. With a wrong URL:     recall() returns ok=False and does NOT raise

Exit code 0 = all checks passed.
Exit code 1 = one or more checks failed.
"""

import os
import sys
import time

# Make sure we can import the project root packages
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import memory.hindsight_client as hc

failures = []


def check(name, condition, detail=""):
    if condition:
        status = "PASS"
    else:
        status = "FAIL"
        failures.append(name)
    msg = "[{}]  {}".format(status, name)
    if detail:
        msg += " -- {}".format(detail)
    print(msg)


# -----------------------------------------------------------------------
# 1. is_enabled()
# -----------------------------------------------------------------------
enabled = hc.is_enabled()
mem_flag = os.getenv("MEMORY_ENABLED")
url_status = "set" if os.getenv("HINDSIGHT_API_URL") else "MISSING"
key_status = "set" if os.getenv("HINDSIGHT_API_KEY") else "MISSING"
check(
    "is_enabled()",
    enabled,
    "MEMORY_ENABLED={}, URL={}, KEY={}".format(mem_flag, url_status, key_status),
)

if not enabled:
    print()
    print("Memory is disabled or not configured. Set HINDSIGHT_API_URL, HINDSIGHT_API_KEY,")
    print("and MEMORY_ENABLED=true in .env to run the full smoke test.")
    sys.exit(0)

# -----------------------------------------------------------------------
# 2. retain() -- store a smoke-test item
# -----------------------------------------------------------------------
smoke_text = (
    "TYPE: smoke_test\n"
    "DATE: {}\n".format(time.strftime("%Y-%m-%d")) +
    "QUESTION: Aegis smoke test -- can we onboard a new payment vendor without a security questionnaire?\n"
    "TOPIC: Vendor Compliance\n"
    "AEGIS_OWNER: Legal | AEGIS_RISK: Medium\n"
    "CORRECTED_OWNER: Procurement Compliance | CORRECTED_RISK: High\n"
    "REASON: Smoke-test item -- delete after verification.\n"
)
ok, err = hc.retain(smoke_text, metadata={"source": "smoke_test"})
check("retain() smoke item", ok, err or "stored OK")

# -----------------------------------------------------------------------
# 3. recall() -- retrieve relevant items (allow up to 3s for async indexing)
# -----------------------------------------------------------------------
print("  (sleeping 3s to allow async indexing...)")
time.sleep(3)
result = hc.recall("vendor onboarding security questionnaire", top_k=5)
check("recall() ok=True", result.ok, result.error or "latency={}ms".format(result.latency_ms))
check("recall() returns items", len(result.items) > 0, "got {} items".format(len(result.items)))
if result.items:
    first = result.items[0]
    print("   -> Top result: id={!r}, type={!r}, date={!r}".format(first.id, first.type, first.date))
    print("     text[:80]: {!r}...".format(first.text[:80]))

# -----------------------------------------------------------------------
# 4. Invalid API key must NOT raise -- returns ok=False
# -----------------------------------------------------------------------
_orig_key = hc._API_KEY
_orig_client = hc._client
hc._API_KEY = "INVALID-KEY-smoke-test"
hc._client = None  # force re-creation with bad key
bad_key_result = hc.recall("vendor onboarding")
check("bad API key: ok=False", not bad_key_result.ok, bad_key_result.error or "")
check("bad API key: no exception raised", True)
# Restore
hc._API_KEY = _orig_key
hc._client = _orig_client

# -----------------------------------------------------------------------
# 5. Invalid URL must NOT raise -- returns ok=False
# -----------------------------------------------------------------------
_orig_url = hc._API_URL
hc._API_URL = "http://127.0.0.1:19999"  # nothing listening here
hc._client = None
bad_url_result = hc.recall("vendor onboarding")
check("bad URL: ok=False", not bad_url_result.ok, bad_url_result.error or "")
check("bad URL: no exception raised", True)
# Restore
hc._API_URL = _orig_url
hc._client = _orig_client

# -----------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------
print()
if failures:
    print("RESULT: {} check(s) FAILED: {}".format(len(failures), failures))
    sys.exit(1)
else:
    print("RESULT: All checks passed")
    sys.exit(0)
