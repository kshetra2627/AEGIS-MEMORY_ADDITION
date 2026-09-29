"""Hindsight memory integration package for Aegis."""
from memory.hindsight_client import (
    MemoryItem,
    MemoryResult,
    is_enabled,
    retain,
    recall,
    reflect,
)
from memory.service import (
    recall_for_query,
    format_prompt_block,
    retain_case,
    retain_review,
    retain_correction,
    mask_pii,
)

__all__ = [
    "MemoryItem",
    "MemoryResult",
    "is_enabled",
    "retain",
    "recall",
    "reflect",
    "recall_for_query",
    "format_prompt_block",
    "retain_case",
    "retain_review",
    "retain_correction",
    "mask_pii",
]
