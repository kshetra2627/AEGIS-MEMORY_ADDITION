"""Deterministic confidence scoring — never LLM-estimated.
Confidence = 70% retrieval similarity + 20% normalized chunk count + 10% citation coverage.
"""


def calculate_confidence_score(chunks: list[dict], citations: list[str]) -> dict:
    qualifying = [c for c in chunks if c.get("qualifies")]

    if not qualifying:
        return {"score": 0, "level": "Low", "retrieval_component": 0, "chunk_component": 0, "citation_component": 0}

    avg_similarity = sum(c["score"] for c in qualifying) / len(qualifying)
    retrieval_component = max(0.0, min(1.0, avg_similarity)) * 70

    chunk_component = min(len(qualifying), 5) / 5 * 20

    citation_component = (len(citations) / len(qualifying) if qualifying else 0)
    citation_component = min(1.0, citation_component) * 10

    score = retrieval_component + chunk_component + citation_component
    score = max(0.0, min(100.0, score))

    if score >= 75:
        level = "High"
    elif score >= 50:
        level = "Medium"
    else:
        level = "Low"

    return {
        "score": round(score, 1),
        "level": level,
        "retrieval_component": round(retrieval_component, 1),
        "chunk_component": round(chunk_component, 1),
        "citation_component": round(citation_component, 1),
    }
