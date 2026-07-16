"""Lightweight MultiQueryRetriever-style query expansion using the existing
llm_provider abstraction (Groq/Gemini/OpenRouter) -- broadens recall by
generating paraphrased variants of the query. Degrades gracefully to
[original query] only if no LLM provider is available.
"""
from llm_provider import get_llm_response

SYSTEM_PROMPT = (
    "You generate alternate phrasings of a compliance question to broaden a search. "
    "Given a question, output exactly 2 alternate phrasings that preserve the same meaning, "
    "one per line, with no numbering or extra text."
)


def generate_query_variants(query: str, max_variants: int = 2) -> list[str]:
    try:
        result = get_llm_response(
            [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": query}],
            temperature=0.2,
        )
        if result["provider"] == "none" or not result["text"]:
            return []
        lines = [l.strip("-• \t") for l in result["text"].splitlines() if l.strip()]
        return lines[:max_variants]
    except Exception as e:
        print(f"[multiquery] variant generation failed: {e}")
        return []
