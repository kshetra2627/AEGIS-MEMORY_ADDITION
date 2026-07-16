"""Deterministic rule-based risk classifier: Low / Medium / High.

Rules live in config/risk_rules.json, not in code. The file is reloaded whenever
its mtime changes, so edits take effect immediately without restarting the app.
"""
import json
import os
import re

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "risk_rules.json")

_cache = {"mtime": None, "rules": None}


def _compile_cross_border(cfg: dict):
    eu_re = re.compile(r"\b(" + "|".join(cfg["eu_markers"]) + r")\b", re.IGNORECASE)
    foreign_re = re.compile(r"\b(" + "|".join(cfg["foreign_region_markers"]) + r")\b", re.IGNORECASE)
    verb_re = re.compile(r"\b(" + "|".join(cfg["data_handling_verbs"]) + r")\b", re.IGNORECASE)
    return eu_re, foreign_re, verb_re


def _load_rules() -> dict:
    mtime = os.path.getmtime(_CONFIG_PATH)
    if _cache["mtime"] == mtime:
        return _cache["rules"]

    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    rules = {
        "high_risk_patterns": [re.compile(p, re.IGNORECASE) for p in raw["high_risk_patterns"]],
        "medium_risk_patterns": [re.compile(p, re.IGNORECASE) for p in raw["medium_risk_patterns"]],
        "high_risk_topics": set(raw["high_risk_topics"]),
        "cross_border": _compile_cross_border(raw["cross_border_data_risk"]),
    }
    _cache["mtime"] = mtime
    _cache["rules"] = rules
    return rules


def _is_cross_border_data_risk(q: str, cross_border) -> bool:
    eu_re, foreign_re, verb_re = cross_border
    return bool(eu_re.search(q) and foreign_re.search(q) and verb_re.search(q))


def classify_risk(query: str, topic: str = "") -> str:
    rules = _load_rules()
    q = query.lower()

    if _is_cross_border_data_risk(q, rules["cross_border"]):
        return "High"

    for pat in rules["high_risk_patterns"]:
        if pat.search(q):
            return "High"

    if topic in rules["high_risk_topics"]:
        return "High"

    for pat in rules["medium_risk_patterns"]:
        if pat.search(q):
            return "Medium"

    return "Low"
