"""Top-k retrieval with relevance-score thresholding.

Retrieval-robustness layer (scoped exception to the LangGraph spec): query
rewrite (typo correction + abbreviation expansion), multi-query expansion, and
BM25 hybrid + cross-encoder reranking all happen INSIDE this function. The
output shape handed to the RAG Retrieval node -- and everything downstream
(Context Validation, Compliance Reasoning, Citation Generation, Confidence
Calculation, Governance Validation) -- is unchanged: a list of chunks with
their real Chroma-derived similarity score and a `qualifies` flag. No new
graph nodes, no rescaled/fabricated scores.
"""
import os
from rag.vectorstore import get_vectorstore
from rag.query_rewrite import normalize_query
from rag.multiquery import generate_query_variants
from rag.hybrid import bm25_candidates, cosine_relevance_score, rerank

SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.65"))
CANDIDATE_POOL_SIZE = 15


def _chunk_dict(metadata: dict, text: str, score: float) -> dict:
    return {
        "text": text,
        "score": float(score),
        "qualifies": float(score) >= SIMILARITY_THRESHOLD,
        "filename": metadata.get("filename", ""),
        "title": metadata.get("title", ""),
        "page": metadata.get("page", ""),
        "section": metadata.get("section", ""),
        "clause": metadata.get("clause", ""),
        "chunk_id": metadata.get("chunk_id", ""),
    }


def retrieve(query: str, k: int = 5) -> list[dict]:
    """Returns top-k chunks with metadata + relevance score, filtered by SIMILARITY_THRESHOLD.
    Never raises: any retrieval-robustness failure falls back to plain vector search,
    and a broken Chroma connection yields an empty list instead of crashing the app.
    """
    try:
        vs = get_vectorstore()
    except Exception as e:
        print(f"[retriever] vectorstore unavailable: {e}")
        return []

    rewritten = normalize_query(query, vs)
    variants = [rewritten] + generate_query_variants(rewritten)

    candidates: dict[str, dict] = {}

    for variant in variants:
        try:
            results = vs.similarity_search_with_relevance_scores(variant, k=CANDIDATE_POOL_SIZE)
        except Exception as e:
            print(f"[retriever] vector search failed for variant '{variant}': {e}")
            continue
        for doc, score in results:
            cid = doc.metadata.get("chunk_id", "")
            if cid and (cid not in candidates or score > candidates[cid]["score"]):
                candidates[cid] = _chunk_dict(doc.metadata, doc.page_content, score)

    try:
        query_embedding = vs.embeddings.embed_query(rewritten)
        for cand in bm25_candidates(vs, rewritten, top_n=CANDIDATE_POOL_SIZE):
            cid = cand["metadata"].get("chunk_id", "")
            if not cid or cid in candidates:
                continue
            emb = cand.get("embedding")
            if emb is None or len(emb) == 0:
                continue
            score = cosine_relevance_score(query_embedding, cand["embedding"])
            candidates[cid] = _chunk_dict(cand["metadata"], cand["text"], score)
    except Exception as e:
        print(f"[retriever] BM25 hybrid stage failed, continuing with vector-only results: {e}")

    pool = sorted(candidates.values(), key=lambda c: c["score"], reverse=True)[:CANDIDATE_POOL_SIZE]
    reranked = rerank(rewritten, pool)

    return reranked[:k]
