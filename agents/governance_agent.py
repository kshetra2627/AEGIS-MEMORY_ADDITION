"""Governance node logic: verifies grounding, evidence sufficiency, and citation coverage.
Discards the draft answer entirely on any failure and returns the fixed refusal string.
"""
import re
from rag.retriever import SIMILARITY_THRESHOLD

REFUSAL_MESSAGE = (
    "I could not find this information in the uploaded compliance corpus. "
    "I cannot provide regulatory advice without supporting policy. "
    "This query has been routed to the Compliance Team."
)

MIN_CONFIDENCE = 40
STRONG_SINGLE_CHUNK_BUFFER = 0.10

HEDGE_PATTERNS = [
    r"no information (is )?available",
    r"do(?:es)?n?'?t? not (?:contain|specify|provide|include|address|cover)",
    r"not (?:specified|available|provided|covered|addressed|mentioned) (?:in|by) the",
    r"cannot (?:find|determine|confirm|locate)",
    r"unable to (?:determine|find|confirm|locate)",
    r"insufficient information",
    r"no (?:specific |explicit )?(?:mention|reference) (?:of|to)",
    r"chunks? (?:do|does) not (?:contain|provide|specify|address|cover)",
]
_HEDGE_RE = re.compile("|".join(HEDGE_PATTERNS), re.IGNORECASE)


def _is_hedged_non_answer(answer_text: str) -> bool:
    """Catches drafts where the LLM admits it has no answer but still attaches citation
    tags to that admission (satisfying the syntactic citation check while asserting
    nothing). Those must be refused, not shown as a confident, cited answer."""
    return bool(_HEDGE_RE.search(answer_text))


def _evidence_sufficient(qualifying_chunks: list[dict]) -> bool:
    if len(qualifying_chunks) >= 2:
        return True
    if len(qualifying_chunks) == 1:
        return qualifying_chunks[0]["score"] >= SIMILARITY_THRESHOLD + STRONG_SINGLE_CHUNK_BUFFER
    return False


def _every_paragraph_cited(answer_text: str) -> bool:
    if not answer_text.strip():
        return False
    paragraphs = [p for p in answer_text.split("\n") if p.strip()]
    if not paragraphs:
        return False
    return all(re.search(r"\[Chunk\s+[^\]]+\]", p) for p in paragraphs)


def validate(in_domain: bool, chunks: list[dict], draft_answer: str, confidence: dict) -> dict:
    """Returns {passed: bool, reason: str, final_text: str}."""
    if not in_domain:
        return {"passed": False, "reason": "out_of_domain", "final_text": REFUSAL_MESSAGE}

    qualifying = [c for c in chunks if c.get("qualifies")]

    if not _evidence_sufficient(qualifying):
        return {"passed": False, "reason": "insufficient_evidence", "final_text": REFUSAL_MESSAGE}

    if not draft_answer or not draft_answer.strip():
        return {"passed": False, "reason": "empty_answer", "final_text": REFUSAL_MESSAGE}

    if _is_hedged_non_answer(draft_answer):
        return {"passed": False, "reason": "hedged_non_answer", "final_text": REFUSAL_MESSAGE}

    if confidence.get("score", 0) < MIN_CONFIDENCE:
        return {"passed": False, "reason": "low_confidence", "final_text": REFUSAL_MESSAGE}

    if not _every_paragraph_cited(draft_answer):
        return {"passed": False, "reason": "uncited_paragraph", "final_text": REFUSAL_MESSAGE}

    return {"passed": True, "reason": "ok", "final_text": draft_answer}
