"""Grounded answer generation. The LLM may only synthesize retrieved chunks -- never
introduce outside facts or rely on model memory. Uses low temperature for determinism.
"""
from llm_provider import get_llm_response

SYSTEM_PROMPT = """You are Aegis, a compliance advisory assistant.
You must answer STRICTLY and ONLY using the "RETRIEVED POLICY CHUNKS" provided below.
Rules:
- Do not use any outside knowledge, training data, or assumptions.
- Every factual sentence must be directly supported by at least one chunk.
- After every sentence that states a fact, append an inline citation tag in the form [Chunk <chunk_id>] referencing the exact chunk it came from.
- Every paragraph must contain at least one [Chunk <chunk_id>] tag.
- If the chunks do not contain enough information to answer, say so explicitly instead of guessing.
- Never provide legal advice beyond what the policy text states. Never endorse bypassing or ignoring a regulation.
- Be concise and precise, written for a corporate compliance audience.
"""


def generate_draft_answer(query: str, chunks: list[dict], chat_history_summary: str = "") -> dict:
    """Returns {text, provider, attempts}. Returns empty text if no qualifying chunks."""
    qualifying = [c for c in chunks if c.get("qualifies")]
    if not qualifying:
        return {"text": "", "provider": "none", "attempts": []}

    context_blocks = []
    for c in qualifying:
        context_blocks.append(
            f"[Chunk {c['chunk_id']}] (Document: {c['title']} | File: {c['filename']} | "
            f"Page: {c['page']} | Section: {c['section']} | Clause: {c['clause']})\n{c['text']}"
        )
    context = "\n\n".join(context_blocks)

    history_note = f"\nPrevious conversation context: {chat_history_summary}\n" if chat_history_summary else ""

    user_prompt = (
        f"RETRIEVED POLICY CHUNKS:\n{context}\n{history_note}\n"
        f"QUESTION: {query}\n\n"
        "Answer using only the chunks above, with inline [Chunk <id>] citations after each factual sentence."
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    result = get_llm_response(messages, temperature=0.1)
    return result
