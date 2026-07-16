"""RAGAS-style RAG evaluation: Context Precision, Context Recall, Faithfulness, Answer
Relevancy -- computed with Aegis's own embedding model + LLM provider instead of the
`ragas` package, so scoring works against any of the failover providers (Groq/Gemini/
OpenRouter) with no extra OpenAI-shaped dependency.

Definitions used here (deliberately explicit since there's no ground-truth answer set
to score against, unlike stock RAGAS context_recall):
- Context Precision: of the chunks the retriever marked as qualifying, what fraction
  is judged actually relevant to the question (LLM-judged, rank-weighted like RAGAS's
  average-precision formulation).
- Context Recall: of the qualifying chunks, what fraction were actually cited in the
  final answer -- did compliance reasoning make use of the relevant context it had.
- Faithfulness: decompose the answer into atomic claims, then check what fraction are
  directly supported by the retrieved context (LLM-judged).
- Answer Relevancy: reverse-engineer questions the answer would be responding to, then
  average their embedding cosine similarity to the original question.
"""
import json
import re

from llm_provider import get_llm_response
from rag.embeddings import get_embeddings

JUDGE_SYSTEM_PROMPT = """You are a strict RAG evaluation judge. You will be given a
question, a numbered list of retrieved context chunks, and an answer produced from
that context. Respond with ONLY a JSON object (no markdown fences, no commentary):

{
  "chunk_relevance": [true/false, ...],   // one entry per context chunk, in order given
  "claims": [{"claim": "<atomic factual claim from the answer>", "supported": true/false}, ...],
  "reverse_questions": ["<question 1 the answer addresses>", "<question 2>", "<question 3>"]
}

Rules:
- chunk_relevance must have exactly one boolean per numbered chunk, judging whether that
  chunk is actually relevant to answering the question.
- claims: break the answer into its individual factual statements (ignore citation tags
  and refusal boilerplate) and judge each as directly supported by the context or not.
- If the answer is empty or a refusal, return an empty claims list.
- reverse_questions: 3 short questions that this answer would be a good response to,
  independent of the original question wording.
"""


def _extract_json(text: str) -> dict:
    if not text:
        return {}
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def evaluate(query: str, chunks: list[dict], citations: list[str], answer: str) -> dict:
    """Returns the four RAGAS-style scores (0-1 floats) plus the raw judge output."""
    qualifying = [c for c in chunks if c.get("qualifies")]

    empty = {
        "context_precision": None, "context_recall": None,
        "faithfulness": None, "answer_relevancy": None, "judge_raw": None,
    }
    if not qualifying or not answer.strip():
        return empty

    context_blocks = "\n\n".join(
        f"[{i + 1}] {c['text']}" for i, c in enumerate(qualifying)
    )
    user_prompt = (
        f"QUESTION: {query}\n\nCONTEXT CHUNKS:\n{context_blocks}\n\nANSWER:\n{answer}"
    )
    result = get_llm_response(
        [{"role": "system", "content": JUDGE_SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
        temperature=0.0,
    )
    parsed = _extract_json(result.get("text", ""))
    if not parsed:
        return empty

    relevance = parsed.get("chunk_relevance") or []
    relevance = relevance[:len(qualifying)]
    if relevance:
        hits, precisions = 0, []
        for i, rel in enumerate(relevance):
            if rel:
                hits += 1
                precisions.append(hits / (i + 1))
        context_precision = round(sum(precisions) / hits, 3) if hits else 0.0
    else:
        context_precision = None

    cited_chunk_ids = set()
    for c in qualifying:
        cid = str(c.get("chunk_id", ""))
        if cid and any(cid in cit for cit in citations):
            cited_chunk_ids.add(cid)
    context_recall = round(len(cited_chunk_ids) / len(qualifying), 3) if qualifying else None

    claims = parsed.get("claims") or []
    if claims:
        supported = sum(1 for c in claims if c.get("supported"))
        faithfulness = round(supported / len(claims), 3)
    else:
        faithfulness = None

    reverse_questions = parsed.get("reverse_questions") or []
    answer_relevancy = None
    if reverse_questions:
        try:
            embedder = get_embeddings()
            q_emb = embedder.embed_query(query)
            sims = [_cosine(q_emb, embedder.embed_query(rq)) for rq in reverse_questions if rq.strip()]
            answer_relevancy = round(sum(sims) / len(sims), 3) if sims else None
        except Exception:
            answer_relevancy = None

    return {
        "context_precision": context_precision,
        "context_recall": context_recall,
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "judge_raw": parsed,
    }
