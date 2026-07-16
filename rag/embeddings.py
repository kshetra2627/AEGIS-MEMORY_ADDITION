"""Embedding model wrapper, swappable via EMBEDDING_MODEL env var."""
import os
from langchain_community.embeddings import HuggingFaceEmbeddings

_embeddings = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        _embeddings = HuggingFaceEmbeddings(model_name=model_name)
    return _embeddings
