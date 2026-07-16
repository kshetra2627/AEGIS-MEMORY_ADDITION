"""Hybrid retrieval support: BM25 lexical index + cross-encoder reranker.
These only influence WHICH chunks are selected/ordered for the final top-5 --
every chunk's reported similarity score always stays the real Chroma cosine
score (computed here with the same formula LangChain uses for cosine space),
never a fabricated or rescaled value, so governance/confidence stay honest.
"""
import re
import numpy as np
from rank_bm25 import BM25Okapi

_bm25_cache = None
_bm25_corpus = None  # list of {"chunk_id", "text", "metadata"}
_cross_encoder = None


def invalidate_bm25_cache():
    global _bm25_cache, _bm25_corpus
    _bm25_cache = None
    _bm25_corpus = None


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def _build_bm25(vs):
    global _bm25_cache, _bm25_corpus
    try:
        data = vs.get(include=["documents", "metadatas", "embeddings"])
        # NOTE: Chroma returns "embeddings" as a numpy array, not a list -- `arr or []`
        # raises "truth value of an array is ambiguous" and was silently swallowed by
        # the except below, meaning BM25 hybrid retrieval never actually ran. Use
        # explicit None checks instead of `or` for anything that may be a numpy array.
        docs = data.get("documents")
        docs = docs if docs is not None else []
        metas = data.get("metadatas")
        metas = metas if metas is not None else []
        embeds = data.get("embeddings")
        embeds = embeds if embeds is not None and len(embeds) > 0 else []
        _bm25_corpus = [{"text": d, "metadata": m, "embedding": e} for d, m, e in zip(docs, metas, embeds)]
        tokenized = [_tokenize(d) for d in docs]
        _bm25_cache = BM25Okapi(tokenized) if tokenized else None
    except Exception as e:
        print(f"[hybrid] BM25 index build failed: {e}")
        _bm25_cache, _bm25_corpus = None, None


def bm25_candidates(vs, query: str, top_n: int = 15) -> list[dict]:
    """Returns lexical-match candidates (chunk text + metadata) not yet scored by cosine similarity."""
    global _bm25_cache, _bm25_corpus
    if _bm25_cache is None:
        _build_bm25(vs)
    if _bm25_cache is None or not _bm25_corpus:
        return []
    try:
        scores = _bm25_cache.get_scores(_tokenize(query))
        top_idx = np.argsort(scores)[::-1][:top_n]
        return [_bm25_corpus[i] for i in top_idx if scores[i] > 0]
    except Exception as e:
        print(f"[hybrid] BM25 query failed: {e}")
        return []


def cosine_relevance_score(query_embedding, chunk_embedding) -> float:
    """Matches LangChain's _cosine_relevance_score_fn: 1 - cosine_distance/2, so
    manually-scored BM25-only candidates land on the exact same scale as
    Chroma's similarity_search_with_relevance_scores() output."""
    q = np.array(query_embedding)
    c = np.array(chunk_embedding)
    denom = (np.linalg.norm(q) * np.linalg.norm(c)) or 1e-9
    cosine_sim = float(np.dot(q, c) / denom)
    cosine_distance = 1.0 - cosine_sim
    return 1.0 - cosine_distance / 2.0


def get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        try:
            from sentence_transformers import CrossEncoder
            _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception as e:
            print(f"[hybrid] cross-encoder load failed, skipping rerank: {e}")
            _cross_encoder = False
    return _cross_encoder or None


def rerank(query: str, candidates: list[dict]) -> list[dict]:
    """Reorders candidates by cross-encoder relevance. Falls back to original
    order (by existing score) if the model is unavailable -- never raises."""
    encoder = get_cross_encoder()
    if not encoder or not candidates:
        return candidates
    try:
        pairs = [(query, c["text"]) for c in candidates]
        rerank_scores = encoder.predict(pairs)
        for c, rs in zip(candidates, rerank_scores):
            c["_rerank_score"] = float(rs)
        return sorted(candidates, key=lambda c: c["_rerank_score"], reverse=True)
    except Exception as e:
        print(f"[hybrid] rerank failed: {e}")
        return candidates
