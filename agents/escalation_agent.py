"""Deterministic rule-based risk classifier: Low / Medium / High."""
import re

HIGH_RISK_PATTERNS = [
    r"\bignore\b.*\b(gdpr|policy|rule|regulation|compliance)\b",
    r"\bbypass\b",
    r"\bcross[- ]?border\b",
    r"\btransfer\b.*\b(outside|abroad|overseas|another (country|region))\b",
    r"\bwithout (review|approval)\b",
    r"\bjust (do it|this once|ignore)\b",
    r"\bsanction(ed|s)?\b",
    r"\bconfirm we can\b",
    r"\bskip (the|any) (review|approval|check)\b",
    r"\bus region\b.*\beu\b|\beu\b.*\bus region\b",
]

MEDIUM_RISK_PATTERNS = [
    r"\bvendor onboarding\b",
    r"\bcontractor(s)?\b.*\baccess\b",
    r"\bdocuments? (are )?needed\b",
    r"\bthird[- ]party\b",
    r"\bshare (data|information)\b",
]

HIGH_RISK_TOPICS = {"Sanctions", "AML"}


def classify_risk(query: str, topic: str = "") -> str:
    q = query.lower()

    for pat in HIGH_RISK_PATTERNS:
        if re.search(pat, q):
            return "High"

    if topic in HIGH_RISK_TOPICS:
        return "High"

    for pat in MEDIUM_RISK_PATTERNS:
        if re.search(pat, q):
            return "Medium"

    return "Low"
