"""Query normalization: typo correction (RapidFuzz) + abbreviation expansion.
Runs as a pre-processing step inside retrieve_policy_documents() -- does not
change the RAG Retrieval node's output shape, only what text is searched.
"""
import re
from rapidfuzz import process, fuzz

ABBREVIATIONS = {
    "gdpr": "gdpr general data protection regulation",
    "aml": "aml anti-money laundering",
    "kyc": "kyc know your customer",
    "dpo": "dpo data protection officer",
    "pii": "pii personally identifiable information",
    "ofac": "ofac office of foreign assets control sanctions",
    "eu": "eu european union",
    "us": "us united states",
    "infosec": "infosec information security",
    "nist": "nist national institute of standards and technology",
}

_vocab_cache: set[str] | None = None


def build_vocabulary(vs) -> set[str]:
    """Builds a word vocabulary from all indexed chunk text, used as the fuzzy-match dictionary."""
    global _vocab_cache
    try:
        data = vs.get(include=["documents"])
        words = set()
        for doc in data.get("documents", []) or []:
            for w in re.findall(r"[a-zA-Z]{4,}", doc.lower()):
                words.add(w)
        _vocab_cache = words
    except Exception as e:
        print(f"[query_rewrite] vocabulary build failed: {e}")
        _vocab_cache = set()
    return _vocab_cache


def invalidate_vocabulary():
    global _vocab_cache
    _vocab_cache = None


def _correct_typos(query: str, vocabulary: set[str]) -> str:
    if not vocabulary:
        return query
    tokens = query.split()
    corrected = []
    for tok in tokens:
        clean = re.sub(r"[^a-zA-Z]", "", tok).lower()
        if len(clean) < 4 or clean in vocabulary:
            corrected.append(tok)
            continue
        match = process.extractOne(clean, vocabulary, scorer=fuzz.ratio, score_cutoff=85)
        corrected.append(match[0] if match else tok)
    return " ".join(corrected)


def _expand_abbreviations(query: str) -> str:
    q = query.lower()
    extras = [expansion for abbr, expansion in ABBREVIATIONS.items() if re.search(rf"\b{abbr}\b", q)]
    if not extras:
        return query
    return query + " " + " ".join(extras)


CROSS_BORDER_EU_TERMS = re.compile(r"\b(eu|european|gdpr)\b", re.IGNORECASE)
CROSS_BORDER_OUTSIDE_TERMS = re.compile(
    r"\b(us region|united states|non[- ]eu|outside the eu|third country|another country|abroad)\b",
    re.IGNORECASE,
)


def _expand_cross_border_transfer(query: str) -> str:
    """Users ask about this in plain language ("EU data in our US region"); the
    indexed GDPR text discusses the identical scenario under Chapter V's actual
    vocabulary ("third country", "international transfer"). Appending that real
    terminology is a content-grounded query expansion, not a fabricated match --
    it only broadens what's searched for, same as the abbreviation expansion above.
    """
    if CROSS_BORDER_EU_TERMS.search(query) and CROSS_BORDER_OUTSIDE_TERMS.search(query):
        return query + " third country transfer international data transfer adequacy decision standard contractual clauses"
    return query


def normalize_query(query: str, vs=None) -> str:
    """Never raises -- on any failure, falls back to the original query unchanged."""
    try:
        vocabulary = _vocab_cache
        if vocabulary is None and vs is not None:
            vocabulary = build_vocabulary(vs)
        corrected = _correct_typos(query, vocabulary or set())
        expanded = _expand_abbreviations(corrected)
        return _expand_cross_border_transfer(expanded)
    except Exception as e:
        print(f"[query_rewrite] normalize failed: {e}")
        return query
