"""Embedding model wrapper, swappable via EMBEDDING_MODEL env var."""
import os
from langchain_community.embeddings import HuggingFaceEmbeddings

_embeddings = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        # Suppress tqdm progress bars during model loading and encoding.
        # On Windows with Streamlit's headless mode, stdout is redirected to a
        # non-terminal pipe. tqdm tries to flush it and raises:
        #   OSError: [Errno 22] Invalid argument
        # TQDM_DISABLE=1 is read by tqdm, HuggingFace transformers, and
        # sentence-transformers before any file descriptor is opened, so the
        # flush never occurs.
        # NOTE: do NOT pass encode_kwargs={"show_progress_bar": False} here --
        # LangChain's similarity_search_with_relevance_scores() and the
        # sentence-transformers CrossEncoder also call encode() with their own
        # show_progress_bar argument, which would cause:
        #   TypeError: got multiple values for keyword argument 'show_progress_bar'
        os.environ.setdefault("TQDM_DISABLE", "1")
        _embeddings = HuggingFaceEmbeddings(model_name=model_name)
    return _embeddings
