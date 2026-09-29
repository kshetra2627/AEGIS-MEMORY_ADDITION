"""Low-level Hindsight client wrapper for Aegis.

Reads config from environment (via existing load_dotenv()):
  HINDSIGHT_API_URL    - Hindsight API base URL (e.g. https://api.hindsight.vectorize.io)
  HINDSIGHT_API_KEY    - Bearer token for the Hindsight Cloud or self-hosted server
  HINDSIGHT_BANK_ID    - Memory bank identifier (default: aegis-northwind)
  MEMORY_ENABLED       - "true" / "false" (default: true)
  MEMORY_TOP_K         - Max memories to recall (default: 5)
  MEMORY_TIMEOUT_SECONDS - Per-request timeout (default: 5)

Decision (per spec §5): single org bank; user_id/user_role stored in tags/metadata
rather than separate banks.  The SDK supports tags filtering on recall, so this is
sufficient without requiring two separate banks.

Package verified: hindsight-client==0.10.1  (pip install hindsight-client)
Client class:     hindsight_client.Hindsight(base_url, api_key, timeout)
retain():         client.retain(bank_id, content, timestamp, context, metadata, tags)
recall():         client.recall(bank_id, query, max_tokens, budget, tags) -> RecallResponse
reflect():        client.reflect(bank_id, query, budget, context)         -> ReflectResponse
RecallResult:     .id, .text, .type, .mentioned_at, .scores
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config (read once at module load; can be overridden by tests via env vars)
# ---------------------------------------------------------------------------
_API_URL: str = os.getenv("HINDSIGHT_API_URL", "").strip()
_API_KEY: str = os.getenv("HINDSIGHT_API_KEY", "").strip()
_BANK_ID: str = os.getenv("HINDSIGHT_BANK_ID", "aegis-northwind").strip()
_MEMORY_ENABLED_RAW: str = os.getenv("MEMORY_ENABLED", "false").strip().lower()
_TIMEOUT: float = float(os.getenv("MEMORY_TIMEOUT_SECONDS", "5"))
_TOP_K: int = int(os.getenv("MEMORY_TOP_K", "5"))


# ---------------------------------------------------------------------------
# Public data classes
# ---------------------------------------------------------------------------

@dataclass
class MemoryItem:
    """A single recalled memory item."""
    id: str
    text: str
    type: str             # parsed from TYPE: prefix in text or SDK .type; "unknown" if absent
    date: str | None      # from .mentioned_at or DATE: prefix in text
    score: float | None   # composite recall score if available


@dataclass
class MemoryResult:
    """Container returned by recall() and indicates success/failure."""
    items: list[MemoryItem] = field(default_factory=list)
    ok: bool = True
    error: str | None = None
    latency_ms: int = 0


# ---------------------------------------------------------------------------
# Internal: lazy client creation
# ---------------------------------------------------------------------------

_client = None  # hindsight_client.Hindsight instance, created on first use


def _get_client():
    """Return a cached Hindsight client, creating it on first call.

    Returns None if configuration is incomplete.
    """
    global _client
    if _client is not None:
        return _client
    if not _API_URL or not _API_KEY:
        return None
    try:
        from hindsight_client import Hindsight  # type: ignore
        _client = Hindsight(base_url=_API_URL, api_key=_API_KEY, timeout=_TIMEOUT)
        return _client
    except Exception as exc:  # noqa: BLE001
        logger.warning("Hindsight client init failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def is_enabled() -> bool:
    """Returns True when MEMORY_ENABLED=true AND API URL+KEY are configured."""
    return _MEMORY_ENABLED_RAW == "true" and bool(_API_URL) and bool(_API_KEY)


def _parse_type_from_text(text: str) -> str:
    """Extract TYPE: value from the retained text template, or 'unknown'."""
    m = re.search(r"^TYPE:\s*(\S+)", text, re.MULTILINE | re.IGNORECASE)
    return m.group(1).lower() if m else "unknown"


def _parse_date_from_text(text: str) -> str | None:
    """Extract DATE: value from the retained text template."""
    m = re.search(r"^DATE:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip() if m else None


def _recall_result_to_item(r) -> MemoryItem:
    """Convert a hindsight_client RecallResult to our MemoryItem."""
    raw_type: str = r.type or _parse_type_from_text(r.text)
    raw_date: str | None = r.mentioned_at or _parse_date_from_text(r.text)
    # Normalise date to YYYY-MM-DD if it's an ISO timestamp
    if raw_date and "T" in raw_date:
        raw_date = raw_date[:10]
    # Extract composite score from scores object if present
    score: float | None = None
    if r.scores is not None:
        try:
            scores_dict = r.scores.model_dump() if hasattr(r.scores, "model_dump") else {}
            vals = [v for v in scores_dict.values() if isinstance(v, (int, float))]
            if vals:
                score = round(max(vals), 4)
        except Exception:  # noqa: BLE001
            pass
    return MemoryItem(id=r.id, text=r.text, type=raw_type, date=raw_date, score=score)


# ---------------------------------------------------------------------------
# Core operations — these never raise to callers
# ---------------------------------------------------------------------------

def retain(
    text: str,
    *,
    metadata: dict | None = None,
    timestamp: str | None = None,
    tags: list[str] | None = None,
) -> tuple[bool, str | None]:
    """Retain a text item in the org memory bank.

    Args:
        text:      The memory text (follows the TYPE:/DATE:/... template).
        metadata:  Optional key-value metadata dict (str -> str).
        timestamp: Optional ISO-8601 timestamp string (e.g. "2026-06-12T00:00:00Z").
        tags:      Optional list of string tags.

    Returns:
        (True, None) on success; (False, error_message) on failure.
    """
    if not is_enabled():
        return False, "Memory disabled or not configured"
    client = _get_client()
    if client is None:
        return False, "Hindsight client unavailable (check HINDSIGHT_API_URL / HINDSIGHT_API_KEY)"
    try:
        ts: datetime | None = None
        if timestamp:
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        client.retain(
            bank_id=_BANK_ID,
            content=text,
            timestamp=ts,
            metadata=metadata,
            tags=tags,
            retain_async=True,  # non-blocking; we don't need to wait for confirmation
        )
        return True, None
    except Exception as exc:  # noqa: BLE001
        msg = f"retain() failed: {exc}"
        logger.warning(msg)
        return False, msg


def recall(query: str, *, top_k: int | None = None) -> MemoryResult:
    """Recall relevant memories for a query.

    Args:
        query: Natural-language query string.
        top_k: How many results to return (defaults to MEMORY_TOP_K env var).

    Returns:
        MemoryResult — always; ok=False and error set if Hindsight failed.
    """
    if not is_enabled():
        return MemoryResult(ok=False, error="Memory disabled or not configured")
    client = _get_client()
    if client is None:
        return MemoryResult(ok=False, error="Hindsight client unavailable")
    effective_top_k = top_k if top_k is not None else _TOP_K
    # Translate top_k to a token budget: ~200 tokens/item
    max_tokens = max(512, effective_top_k * 250)
    t0 = time.monotonic()
    try:
        response = client.recall(
            bank_id=_BANK_ID,
            query=query,
            max_tokens=max_tokens,
            budget="mid",
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        items = [_recall_result_to_item(r) for r in response.results[:effective_top_k]]
        return MemoryResult(items=items, ok=True, error=None, latency_ms=latency_ms)
    except Exception as exc:  # noqa: BLE001
        latency_ms = int((time.monotonic() - t0) * 1000)
        msg = f"recall() failed: {exc}"
        logger.warning(msg)
        return MemoryResult(ok=False, error=msg, latency_ms=latency_ms)


def reflect(query: str) -> tuple[str | None, str | None]:
    """Run a reflect (deep reasoning) query over the memory bank.

    Returns:
        (insight_text, None) on success; (None, error_message) on failure.
    """
    if not is_enabled():
        return None, "Memory disabled or not configured"
    client = _get_client()
    if client is None:
        return None, "Hindsight client unavailable"
    try:
        response = client.reflect(
            bank_id=_BANK_ID,
            query=query,
            budget="low",
        )
        return response.text, None
    except Exception as exc:  # noqa: BLE001
        msg = f"reflect() failed: {exc}"
        logger.warning(msg)
        return None, msg
